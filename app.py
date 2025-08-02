import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime
import base64
import requests
from io import BytesIO

# config.py에서 설정 가져오기
from config import AppConfig
# data_handler.py에서 데이터 처리 클래스 가져오기
from data_handler import DataProcessor
# analysis_engine.py에서 분석 엔진 가져오기
from analysis_engine import BusinessAnalyzer


# Streamlit 설정
st.set_page_config(**AppConfig.PAGE_CONFIG)

class SujeonggwaMarketAnalyzer:
    def __init__(self):
        self.required_columns = AppConfig.REQUIRED_COLUMNS
        self.our_brand = AppConfig.OUR_BRAND
        self.data_processor = DataProcessor()  # 데이터 처리기
        self.business_analyzer = BusinessAnalyzer()  # 분석 엔진 추가
    

    def load_latest_analysis_from_github(self):
        """GitHub에서 최신 분석 결과 불러오기"""
        github_config = AppConfig.get_github_config()
        github_token = github_config['token']
        github_api_url = AppConfig.get_github_api_url()
        
        if not github_token:
            return None
        
        try:
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.get(github_api_url, headers=headers)
            
            if response.status_code == 200:
                files = response.json()
                
                analysis_files = [f for f in files if f['name'].startswith('analysis_results') and f['name'].endswith('.json')]
                
                if analysis_files:
                    latest_file = max(analysis_files, key=lambda x: x['name'])
                    file_response = requests.get(latest_file['download_url'])
                    
                    if file_response.status_code == 200:
                        return json.loads(file_response.text)
                
            return None
            
        except Exception as e:
            st.error(f"GitHub에서 분석 결과 로드 중 오류: {str(e)}")
            return None

    def clear_github_results(self):
        """GitHub에서 기존 분석 결과 파일들 삭제"""
        github_config = AppConfig.get_github_config()
        github_token = github_config['token']
        github_api_url = AppConfig.get_github_api_url()
        
        if not github_token:
            return False
        
        try:
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.get(github_api_url, headers=headers)
            
            if response.status_code == 200:
                files = response.json()
                analysis_files = [f for f in files if f['name'].startswith('analysis_results') and f['name'].endswith('.json')]
                
                for file_info in analysis_files:
                    delete_url = f"{github_api_url}/{file_info['name']}"
                    delete_data = {
                        "message": f"Delete old analysis result: {file_info['name']}",
                        "sha": file_info['sha']
                    }
                    
                    delete_response = requests.delete(delete_url, headers=headers, json=delete_data)
                    if delete_response.status_code != 200:
                        st.warning(f"파일 삭제 실패: {file_info['name']}")
                
                return True
            
        except Exception as e:
            st.error(f"GitHub 파일 삭제 중 오류: {str(e)}")
            return False

    def save_to_github(self, content, filename):
        """GitHub에 분석 결과 저장"""
        github_config = AppConfig.get_github_config()
        github_token = github_config['token']
        github_api_url = AppConfig.get_github_api_url()
        
        if not github_token:
            return False
        
        try:
            content_encoded = base64.b64encode(content.encode('utf-8')).decode()
            
            url = f"{github_api_url}/{filename}"
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            data = {
                "message": f"📊 수정과 시장 분석 결과 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "content": content_encoded,
            }
            
            response = requests.put(url, headers=headers, json=data)
            
            if response.status_code in [200, 201]:
                return True
            else:
                st.error(f"GitHub 업로드 실패: {response.status_code}")
                return False
                
        except Exception as e:
            st.error(f"GitHub 저장 중 오류: {str(e)}")
            return False

def show_analysis_results(analysis_results, json_content, timestamp, github_success):
    """분석 결과를 표시하는 함수"""
    
    if not analysis_results:
        st.error("분석 결과가 없습니다.")
        return
    
    if github_success:
        st.success("✅ 분석 완료 및 GitHub 저장 성공!")
    else:
        st.warning("⚠️ 분석 완료, GitHub 저장 실패")
    
    tab_handmade, tab_all = st.tabs(["🥛 수제 제품 분석", "🏭 전체 제품 분석 (수제+공장형)"])
    
    with tab_handmade:
        show_category_analysis(analysis_results.get('handmade_category', {}), "수제")
    
    with tab_all:
        show_category_analysis(analysis_results.get('all_category', {}), "전체")

def show_category_analysis(category_data, category_type):
    """카테고리별 분석 결과 표시"""
    
    if not category_data:
        st.warning(f"{category_type} 카테고리 데이터가 없습니다.")
        return
    
    # 핵심 지표 카드
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 분석된 제품 수", f"{category_data.get('total_products_analyzed', 0)}개")
    
    with col2:
        st.metric("🎯 고유 제품 수", f"{category_data.get('total_unique_products', 0)}개")
    
    with col3:
        our_count = category_data.get('our_unique_products_count', 0)
        st.metric("🥤 서로 브랜드", f"{our_count}개")
    
    with col4:
        competitor_count = category_data.get('competitor_unique_products_count', 0)
        st.metric("🏭 경쟁사 제품", f"{competitor_count}개")
    
    st.markdown("---")
    
    # 통합된 우리 제품 현황
    st.subheader(f"🥤 서로 브랜드 종합 현황 ({category_type})")
    
    business_insights = category_data.get('business_insights', {})
    
    # 1. 제품별 상세 현황
    st.markdown("### 📊 제품별 상세 현황")
    if 'our_product_details' in business_insights:
        product_details = business_insights['our_product_details']
        
        if product_details:
            details_df = pd.DataFrame(product_details)
            st.dataframe(details_df, use_container_width=True)
            st.info(f"💡 총 {len(product_details)}개의 서로 브랜드 제품이 분석되었습니다.")
        else:
            st.warning("서로 브랜드 제품이 없습니다.")
    else:
        st.warning("제품 상세 정보가 없습니다.")
    
    st.markdown("---")
    
    # 2. 제품별 가격 경쟁력
    st.markdown("### 💰 제품별 가격 경쟁력")
    if 'detailed_competitiveness' in business_insights:
        comp_data = business_insights['detailed_competitiveness']
        
        if comp_data:
            for platform, products in comp_data.items():
                with st.expander(f"🏪 {platform} - {len(products)}개 제품"):
                    
                    for product in products:
                        st.markdown(f"**{product.get('제품', 'N/A')}**")
                        
                        # 비교 기준 표시
                        comparison_basis = product.get('비교_기준', 'N/A')
                        if comparison_basis == "동일 용량+개수":
                            st.success(f"🎯 **비교 기준**: {comparison_basis}")
                        elif "유사 용량" in comparison_basis:
                            st.info(f"📊 **비교 기준**: {comparison_basis}")
                        elif comparison_basis == "동일 개수":
                            st.warning(f"📈 **비교 기준**: {comparison_basis}")
                        else:
                            st.error(f"💰 **비교 기준**: {comparison_basis}")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("우리 단위가격", product.get('우리_단위가격', 'N/A'))
                            st.metric("경쟁사 평균", product.get('경쟁사_평균', 'N/A'))
                        
                        with col2:
                            st.metric("경쟁사 최저", product.get('경쟁사_최저', 'N/A'))
                            st.metric("경쟁사 최고", product.get('경쟁사_최고', 'N/A'))
                        
                        with col3:
                            st.metric("가격 차이", product.get('가격차이', 'N/A'), product.get('가격차이_퍼센트', 'N/A'))
                            
                            position = product.get('시장_포지션', 'N/A')
                            competitor_count = product.get('경쟁사_수', 0)
                            
                            if "🎯" in position:
                                st.success(f"**{position}** (경쟁사 {competitor_count}개)")
                            elif "📊" in position:
                                st.info(f"**{position}** (경쟁사 {competitor_count}개)")
                            elif "📈" in position:
                                st.warning(f"**{position}** (경쟁사 {competitor_count}개)")
                            else:
                                st.error(f"**{position}** (경쟁사 {competitor_count}개)")
                        
                        # 주요 경쟁사 표시
                        main_competitors = product.get('주요_경쟁사', [])
                        if main_competitors:
                            st.markdown("**📋 주요 경쟁사:**")
                            for i, competitor in enumerate(main_competitors, 1):
                                st.write(f"  {i}. {competitor}")
                        
                        st.markdown("---")
        else:
            st.info("제품별 경쟁력 데이터가 없습니다.")
    else:
        st.info("제품별 경쟁력 데이터가 없습니다.")
    
    st.markdown("---")
    
    # 3. 용량별/개수별 시장 현황
    st.markdown("### 📊 용량별/개수별 시장 현황")
    if 'volume_count_market' in business_insights:
        market_data = business_insights['volume_count_market']
        
        if market_data:
            st.markdown("#### 🔥 인기 용량/개수 조합 (상위 10개)")
            
            market_df = pd.DataFrame(market_data)
            st.dataframe(market_df, use_container_width=True)
            
            # 우리가 진출하지 않은 시장 찾기
            untapped_markets = [item for item in market_data if item.get('우리_제품수', 0) == 0]
            
            if untapped_markets:
                st.markdown("#### 💡 진출 기회 있는 시장")
                for market in untapped_markets[:5]:
                    volume_count = market.get('용량_개수', 'N/A')
                    total_products = market.get('총_제품수', 0)
                    avg_price = market.get('평균_단위가격', 'N/A')
                    st.info(f"**{volume_count}**: {total_products}개 제품, 평균 단위가격 {avg_price}")
        else:
            st.warning("용량별 시장 데이터가 없습니다.")
    else:
        st.info("용량별 시장 분석 데이터가 없습니다.")
    
    st.markdown("---")
    
    # 4. 브랜드별 시장 분석
    st.markdown("### 🏆 브랜드별 시장 점유율")
    
    if 'market_share' in business_insights:
        share_data = business_insights['market_share']
        
        if share_data:
            share_df = pd.DataFrame([
                {'브랜드': brand, '제품 수': data.get('제품_수', 0), '점유율': f"{data.get('점유율_퍼센트', 0)}%"}
                for brand, data in share_data.items()
            ])
            
            st.dataframe(share_df, use_container_width=True)
            
            # 서로 브랜드 순위 찾기
            seoro_rank = None
            for idx, (brand, _) in enumerate(share_data.items(), 1):
                if brand == "서로":
                    seoro_rank = idx
                    break
            
            if seoro_rank:
                if seoro_rank == 1:
                    st.success(f"🏆 서로 브랜드가 **1위**입니다!")
                elif seoro_rank <= 3:
                    st.info(f"🥉 서로 브랜드가 **{seoro_rank}위**입니다.")
                else:
                    st.warning(f"📈 서로 브랜드가 **{seoro_rank}위**입니다. 더 많은 제품 라인업이 필요해 보입니다.")
            else:
                st.info("서로 브랜드는 현재 상위 10위 안에 없습니다.")
        else:
            st.warning("브랜드별 점유율 데이터가 없습니다.")
    else:
        st.info("브랜드별 점유율 데이터가 없습니다.")

def main():
    # 헤더
    st.title("🥤 서로 수정과 - 시장 가격 분석 대시보드")
    st.markdown("##### *플랫폼별 가격 경쟁력 및 시장 포지셔닝 분석*")
    
    st.markdown("---")
    
    analyzer = SujeonggwaMarketAnalyzer()
    
    # 세션 상태 초기화
    if 'run_analysis' not in st.session_state:
        st.session_state.run_analysis = False
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    if 'json_content' not in st.session_state:
        st.session_state.json_content = None
    if 'timestamp' not in st.session_state:
        st.session_state.timestamp = None
    
    # 사이드바
    with st.sidebar:
        st.header("📊 분석 설정")
        
        uploaded_files = st.file_uploader(
            "엑셀 파일 업로드",
            type=['xlsx', 'xls'],
            accept_multiple_files=True,
            help="네이버, 쿠팡, 올웨이즈 수정과 가격 데이터"
        )
        
        st.markdown("---")
        
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)}개 파일 업로드됨")
            for file in uploaded_files:
                platform = analyzer.extract_platform_from_filename(file.name)
                st.write(f"📄 {platform}: {file.name}")

            # 데이터 품질 정보 표시 (새로 추가)
            with st.expander("📊 데이터 품질 확인", expanded=False):
                temp_df_list = []
                for file in uploaded_files:
                    df, platform, missing_cols = analyzer.data_processor.load_and_standardize_excel(file)
                    if df is not None:
                        temp_df_list.append(df)
                
                if temp_df_list:
                    quality_info = analyzer.data_processor.validate_data_quality(temp_df_list)
                    st.write(f"📁 총 {quality_info['total_files']}개 파일")
                    st.write(f"📊 총 {quality_info['total_products']}개 제품")
                    st.write(f"🏪 플랫폼: {', '.join(quality_info['platforms'])}")
                    
                    if quality_info['quality_issues']:
                        st.write("⚠️ 품질 이슈:")
                        for issue in quality_info['quality_issues']:
                            st.write(f"  • {issue}")

        
        
        if st.button("🚀 분석 시작", type="primary", disabled=not uploaded_files):
            st.session_state.run_analysis = True
        
        st.markdown("---")
        st.markdown("### 📋 분석 항목")
        st.markdown("""
        - ✅ 제품별 가격 경쟁력
        - ✅ 용량/개수별 시장 분석  
        - ✅ 브랜드별 점유율
        - ✅ 진출 기회 발견
        """)
    

    # 메인 분석
    if uploaded_files and st.session_state.get('run_analysis', False):
        
        # 프로그레스 표시
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        df_list = []
        platform_info = []
        
        # 파일 처리
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"📂 파일 처리 중: {uploaded_file.name}")
            progress_bar.progress((i + 1) / len(uploaded_files) * 0.4)
            
            df, platform, missing_cols = analyzer.data_processor.load_and_standardize_excel(uploaded_file)
            
            if df is not None:
                df_list.append(df)
                platform_info.append({
                    'filename': uploaded_file.name,
                    'platform': platform,
                    'rows': len(df),
                    'missing_columns': missing_cols
                })
        
        if df_list:
            status_text.text("🔍 시장 데이터 분석 중...")
            progress_bar.progress(0.7)
            
            # 핵심 비즈니스 분석
            analysis_results, handmade_df, all_products_df = analyzer.business_analyzer.analyze_business_critical_data(df_list)
            
            if analysis_results:
                status_text.text("📈 시각화 생성 중...")
                progress_bar.progress(0.9)
                
                # GitHub에 자동 저장
                status_text.text("💾 GitHub에 저장 중...")
                
                # 기존 결과 파일들 삭제
                analyzer.clear_github_results()
                
                # 새 결과 저장
                json_content = json.dumps(analysis_results, ensure_ascii=False, indent=2)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                json_filename = f"analysis_results_{timestamp}.json"
                
                github_success = analyzer.save_to_github(json_content, json_filename)
                
                progress_bar.progress(1.0)
                status_text.empty()
                progress_container.empty()
                
                # 결과를 세션 상태에 저장
                st.session_state.analysis_results = analysis_results
                st.session_state.json_content = json_content
                st.session_state.timestamp = timestamp
                
                # 결과 대시보드 표시
                show_analysis_results(analysis_results, json_content, timestamp, github_success)
            else:
                st.error("분석 중 오류가 발생했습니다.")
            
            # 세션 상태 리셋
            st.session_state.run_analysis = False
        else:
            st.error("처리할 수 있는 파일이 없습니다.")
            st.session_state.run_analysis = False
    
    # 기존 분석 결과가 세션에 있거나 GitHub에서 불러올 수 있는 경우
    elif st.session_state.get('analysis_results') or not uploaded_files:
        
        # 세션에 결과가 없으면 GitHub에서 불러오기
        if not st.session_state.get('analysis_results'):
            with st.spinner("GitHub에서 최신 분석 결과를 불러오는 중..."):
                latest_analysis = analyzer.load_latest_analysis_from_github()
                
                if latest_analysis:
                    st.session_state.analysis_results = latest_analysis
                    st.session_state.json_content = json.dumps(latest_analysis, ensure_ascii=False, indent=2)
                    st.session_state.timestamp = latest_analysis.get('timestamp', 'unknown')
                    st.success("✅ GitHub에서 최신 분석 결과를 불러왔습니다!")
        
        # 분석 결과 표시
        if st.session_state.get('analysis_results'):
            show_analysis_results(
                st.session_state.analysis_results, 
                st.session_state.get('json_content', ''), 
                st.session_state.get('timestamp', 'unknown'),
                True
            )
        else:
            # 초기 화면  
            st.info("👈 사이드바에서 엑셀 파일들을 업로드하고 분석을 시작하세요.")
            
            # 간단한 안내 메시지
            with st.expander("📋 사용 방법", expanded=False):
                st.markdown("""
                ### 🚀 주요 기능
                
                **🎯 핵심 비즈니스 분석**
                - 서로 브랜드의 제품별 가격 경쟁력 분석
                - 용량/개수별 세분화된 시장 포지셔닝  
                - 경쟁사 대비 정확한 가격 차이 분석
                
                **📊 시장 현황 파악**
                - 용량별/개수별 인기 시장 발견
                - 진출 기회 있는 시장 자동 추천
                - 브랜드별 시장 점유율 분석
                
                ### 📁 파일 업로드 가이드
                - **지원 형식**: Excel 파일 (.xlsx, .xls)
                - **파일명 예시**: "네이버 수정과 가격", "쿠팡 수정과 가격" 등
                - **필수 컬럼**: 브랜드, 제품명, 용량(ml), 개수, 최저가(배송비 포함), 최저가 단위가격(100ml당) 등
                """)

# Streamlit 앱 실행
if __name__ == "__main__":
    main()
