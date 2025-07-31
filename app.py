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

# GitHub 설정
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "coder4052/market_analysis")
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents"

class SujeonggwaMarketAnalyzer:
    def __init__(self):
        self.required_columns = [
            "브랜드", "제품명", "용량(ml)", "개수", 
            "일반 판매가", "일반 판매가 단위가격(100ml당)", 
            "상시 할인가", "상시 할인가 단위가격(100ml당)",
            "배송비", "최저가(배송비 포함)", "최저가 단위가격(100ml당)", 
            "공장형 여부"
        ]
        self.our_brand = "서로"
    
    def extract_platform_from_filename(self, filename):
        """파일명에서 플랫폼 추출"""
        filename_lower = filename.lower()
        if '네이버' in filename:
            return '네이버'
        elif '쿠팡' in filename:
            return '쿠팡'
        elif '올웨이즈' in filename:
            return '올웨이즈'
        else:
            return '기타'
    
    def load_and_standardize_excel(self, uploaded_file):
        """엑셀 파일 로드 및 표준화"""
        try:
            df = pd.read_excel(uploaded_file, sheet_name=0)
            platform = self.extract_platform_from_filename(uploaded_file.name)
            
            # 필요한 컬럼만 추출
            available_columns = [col for col in self.required_columns if col in df.columns]
            missing_columns = [col for col in self.required_columns if col not in df.columns]
            
            if missing_columns:
                st.warning(f"[{platform}] 누락된 컬럼: {missing_columns}")
            
            # 데이터 정제
            df_clean = df[available_columns].copy()
            df_clean['플랫폼'] = platform
            df_clean['분석_시간'] = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            # 숫자형 컬럼 변환
            numeric_columns = ['용량(ml)', '개수', '최저가(배송비 포함)', '최저가 단위가격(100ml당)', '공장형 여부']
            for col in numeric_columns:
                if col in df_clean.columns:
                    df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
            
            return df_clean, platform, missing_columns
            
        except Exception as e:
            st.error(f"파일 처리 중 오류: {str(e)}")
            return None, None, None
    
    def analyze_business_critical_data(self, df_list):
        """소상공인 관점의 핵심 비즈니스 분석"""
        if not df_list:
            return None
        
        combined_df = pd.concat(df_list, ignore_index=True)
        
        # 1차: 수제 제품만 필터링 (공장형 여부 = 0)
        if '공장형 여부' in combined_df.columns:
            handmade_df = combined_df[combined_df['공장형 여부'] == 0].copy()
            all_products_df = combined_df.copy()  # 전체 제품 (수제 + 공장형)
        else:
            handmade_df = combined_df.copy()
            all_products_df = combined_df.copy()
            st.warning("'공장형 여부' 컬럼을 찾을 수 없습니다.")
        
        # 수제 제품 분석
        handmade_analysis = self._analyze_category(handmade_df, "수제 제품")
        
        # 전체 제품 분석 (수제 + 공장형)
        all_analysis = self._analyze_category(all_products_df, "전체 제품")
        
        # 통합 분석 결과
        analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'analysis_type': '수정과 시장 분석',
            'our_brand': self.our_brand,
            'handmade_category': handmade_analysis,
            'all_category': all_analysis,
            'platforms_analyzed': combined_df['플랫폼'].unique().tolist()
        }
        
        return analysis_results, handmade_df, all_products_df
    
    def _analyze_category(self, df, category_name):
        """카테고리별 분석 (수제 또는 전체)"""
        
        # 서로 브랜드 데이터 추출
        our_products = df[df['브랜드'] == self.our_brand].copy()
        competitor_products = df[df['브랜드'] != self.our_brand].copy()
        
        # 제품 그룹핑 (브랜드 + 제품명이 같으면 같은 제품으로 처리)
        unique_products = df.groupby(['브랜드', '제품명']).agg({
            '용량(ml)': lambda x: list(x.unique()),  # 용량 리스트
            '개수': 'first',  # 첫 번째 값 사용
            '최저가(배송비 포함)': 'min',  # 최저가 선택
            '최저가 단위가격(100ml당)': 'min',  # 최저 단위가격 선택
            '플랫폼': lambda x: list(x.unique())  # 판매 플랫폼 리스트
        }).reset_index()
        
        # 우리 브랜드 고유 제품 수 계산
        our_unique_products = unique_products[unique_products['브랜드'] == self.our_brand]
        competitor_unique_products = unique_products[unique_products['브랜드'] != self.our_brand]
        
        category_results = {
            'category_name': category_name,
            'total_products_analyzed': len(df),
            'total_unique_products': len(unique_products),
            'our_products_count': len(our_products),
            'our_unique_products_count': len(our_unique_products),
            'competitor_products_count': len(competitor_products),
            'competitor_unique_products_count': len(competitor_unique_products),
            'business_insights': {}
        }
        
        # 1. 우리 브랜드 플랫폼별 현황 (고유 제품 기준)
        if not our_unique_products.empty:
            our_platform_status = {}
            for platform in df['플랫폼'].unique():
                # 해당 플랫폼에서 판매되는 우리 브랜드 고유 제품
                platform_products = our_unique_products[
                    our_unique_products['플랫폼'].apply(lambda x: platform in x)
                ]
                
                if not platform_products.empty:
                    our_platform_status[platform] = {
                        '고유제품_수': len(platform_products),
                        '평균_최저가': round(platform_products['최저가(배송비 포함)'].mean(), 0),
                        '평균_단위가격': round(platform_products['최저가 단위가격(100ml당)'].mean(), 0),
                        '용량_종류': len(set([vol for volumes in platform_products['용량(ml)'] for vol in volumes]))
                    }
            
            category_results['business_insights']['our_platform_status'] = our_platform_status
        
        # 2. 플랫폼별 가격 경쟁력 분석 (고유 제품 기준)
        if '최저가 단위가격(100ml당)' in df.columns:
            competitiveness = {}
            for platform in df['플랫폼'].unique():
                platform_data = df[df['플랫폼'] == platform]
                our_platform_data = our_products[our_products['플랫폼'] == platform]
                competitor_platform_data = competitor_products[competitor_products['플랫폼'] == platform]
                
                if not our_platform_data.empty and not competitor_platform_data.empty:
                    our_avg_unit_price = our_platform_data['최저가 단위가격(100ml당)'].mean()
                    competitor_avg_unit_price = competitor_platform_data['최저가 단위가격(100ml당)'].mean()
                    competitor_min_unit_price = competitor_platform_data['최저가 단위가격(100ml당)'].min()
                    competitor_max_unit_price = competitor_platform_data['최저가 단위가격(100ml당)'].max()
                    
                    price_gap = our_avg_unit_price - competitor_avg_unit_price
                    price_gap_percent = (price_gap / competitor_avg_unit_price) * 100
                    
                    # 시장 위치 판단
                    if our_avg_unit_price <= competitor_min_unit_price:
                        market_position = "최저가 그룹"
                    elif our_avg_unit_price <= competitor_avg_unit_price:
                        market_position = "평균 이하"
                    elif our_avg_unit_price <= competitor_max_unit_price:
                        market_position = "평균 이상"
                    else:
                        market_position = "최고가 그룹"
                    
                    competitiveness[platform] = {
                        '우리_평균단위가격': round(our_avg_unit_price, 0),
                        '경쟁사_평균단위가격': round(competitor_avg_unit_price, 0),
                        '경쟁사_최저단위가격': round(competitor_min_unit_price, 0),
                        '경쟁사_최고단위가격': round(competitor_max_unit_price, 0),
                        '가격차이': round(price_gap, 0),
                        '가격차이_퍼센트': round(price_gap_percent, 1),
                        '시장_포지션': market_position
                    }
            
            category_results['business_insights']['price_competitiveness'] = competitiveness
        
        # 3. 브랜드별 시장 점유율 (고유 제품 수 기준)
        brand_share = unique_products['브랜드'].value_counts()
        total_unique_products = len(unique_products)
        brand_share_percent = {}
        
        for brand, count in brand_share.head(10).items():
            percentage = (count / total_unique_products) * 100
            brand_share_percent[brand] = {
                '고유제품_수': int(count),
                '점유율_퍼센트': round(percentage, 1)
            }
        
        category_results['business_insights']['market_share'] = brand_share_percent
        
        # 4. 가격대별 제품 분포 (우리 브랜드 위치 파악용)
        if '최저가 단위가격(100ml당)' in df.columns:
            unit_prices = df['최저가 단위가격(100ml당)'].dropna()
            
            # 가격대 구간 생성
            price_ranges = {
                '1000원 미만': len(unit_prices[unit_prices < 1000]),
                '1000-2000원': len(unit_prices[(unit_prices >= 1000) & (unit_prices < 2000)]),
                '2000-3000원': len(unit_prices[(unit_prices >= 2000) & (unit_prices < 3000)]),
                '3000-4000원': len(unit_prices[(unit_prices >= 3000) & (unit_prices < 4000)]),
                '4000원 이상': len(unit_prices[unit_prices >= 4000])
            }
            
            # 우리 제품이 속한 가격대 표시
            our_price_distribution = {}
            if not our_products.empty and '최저가 단위가격(100ml당)' in our_products.columns:
                our_unit_prices = our_products['최저가 단위가격(100ml당)'].dropna()
                for price_range, count in price_ranges.items():
                    if price_range == '1000원 미만':
                        our_count = len(our_unit_prices[our_unit_prices < 1000])
                    elif price_range == '1000-2000원':
                        our_count = len(our_unit_prices[(our_unit_prices >= 1000) & (our_unit_prices < 2000)])
                    elif price_range == '2000-3000원':
                        our_count = len(our_unit_prices[(our_unit_prices >= 2000) & (our_unit_prices < 3000)])
                    elif price_range == '3000-4000원':
                        our_count = len(our_unit_prices[(our_unit_prices >= 3000) & (our_unit_prices < 4000)])
                    else:  # 4000원 이상
                        our_count = len(our_unit_prices[our_unit_prices >= 4000])
                    
                    our_price_distribution[price_range] = {
                        '전체_제품수': count,
                        '우리_제품수': our_count
                    }
            
            category_results['business_insights']['price_distribution'] = our_price_distribution
        
        return category_results

    def load_latest_analysis_from_github(self):
        """GitHub에서 최신 분석 결과 불러오기"""
        if not GITHUB_TOKEN:
            return None
        
        try:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # 저장소 내용 조회
            response = requests.get(GITHUB_API_URL, headers=headers)
            
            if response.status_code == 200:
                files = response.json()
                
                # 분석 결과 파일들 찾기
                analysis_files = [f for f in files if f['name'].startswith('analysis_results') and f['name'].endswith('.json')]
                
                if analysis_files:
                    # 최신 파일 선택 (파일명의 타임스탬프 기준)
                    latest_file = max(analysis_files, key=lambda x: x['name'])
                    
                    # 파일 내용 가져오기
                    file_response = requests.get(latest_file['download_url'])
                    
                    if file_response.status_code == 200:
                        return json.loads(file_response.text)
                
            return None
            
        except Exception as e:
            st.error(f"GitHub에서 분석 결과 로드 중 오류: {str(e)}")
            return None

    def clear_github_results(self):
        """GitHub에서 기존 분석 결과 파일들 삭제"""
        if not GITHUB_TOKEN:
            return False
        
        try:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # 저장소 내용 조회
            response = requests.get(GITHUB_API_URL, headers=headers)
            
            if response.status_code == 200:
                files = response.json()
                
                # 분석 결과 파일들 찾기 (analysis_results로 시작하는 JSON 파일)
                analysis_files = [f for f in files if f['name'].startswith('analysis_results') and f['name'].endswith('.json')]
                
                # 각 파일 삭제
                for file_info in analysis_files:
                    delete_url = f"{GITHUB_API_URL}/{file_info['name']}"
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
        if not GITHUB_TOKEN:
            st.error("""
            🔧 **GitHub 연동 설정이 필요합니다**
            
            **Streamlit Cloud에서 설정하는 방법:**
            1. 앱 대시보드 → Settings → Secrets
            2. 다음 내용 추가:
            ```
            GITHUB_TOKEN = "your_github_token"
            GITHUB_REPO = "username/repo-name"
            ```
            """)
            return False
        
        try:
            content_encoded = base64.b64encode(content.encode('utf-8')).decode()
            
            url = f"{GITHUB_API_URL}/{filename}"
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
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
                st.error(f"GitHub 업로드 실패: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            st.error(f"GitHub 저장 중 오류: {str(e)}")
            return False

def show_analysis_results(analysis_results, json_content, timestamp, github_success):
    """분석 결과를 표시하는 함수"""
    
    # 결과 대시보드
    if github_success:
        st.success("✅ 분석 완료 및 GitHub 저장 성공!")
    else:
        st.warning("⚠️ 분석 완료, GitHub 저장 실패")
    
    # 카테고리 선택 탭
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
        st.metric("🥤 서로 브랜드 (고유)", f"{our_count}개")
    
    with col4:
        competitor_count = category_data.get('competitor_unique_products_count', 0)
        st.metric("🏭 경쟁사 제품 (고유)", f"{competitor_count}개")
    
    st.markdown("---")
    
    # 세부 분석 탭
    tab1, tab2, tab3 = st.tabs(["💰 가격 경쟁력", "📊 시장 분석", "📈 상세 정보"])
    
    with tab1:
        st.subheader(f"💰 {category_type} 카테고리 가격 경쟁력 분석")
        
        # 경쟁력 요약 테이블
        if 'price_competitiveness' in category_data.get('business_insights', {}):
            comp_data = category_data['business_insights']['price_competitiveness']
            
            st.markdown("#### 📋 플랫폼별 경쟁력 요약")
            
            for platform, data in comp_data.items():
                with st.expander(f"🏪 {platform} 상세 분석"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("서로 평균 단위가격", f"{data['우리_평균단위가격']:,}원")
                        st.metric("경쟁사 평균 단위가격", f"{data['경쟁사_평균단위가격']:,}원")
                    
                    with col2:
                        price_diff = data['가격차이']
                        price_diff_percent = data['가격차이_퍼센트']
                        
                        if price_diff > 0:
                            st.metric("가격 차이", f"+{price_diff:,}원", f"+{price_diff_percent}%")
                        else:
                            st.metric("가격 차이", f"{price_diff:,}원", f"{price_diff_percent}%")
                        
                        # 시장 포지션
                        position = data['시장_포지션']
                        if position == "최저가 그룹":
                            st.success(f"🎯 시장 포지션: **{position}**")
                        elif position == "평균 이하":
                            st.info(f"📊 시장 포지션: **{position}**")
                        else:
                            st.warning(f"📈 시장 포지션: **{position}**")
        else:
            st.info("가격 경쟁력 데이터가 없습니다.")
    
    with tab2:
        st.subheader(f"📊 {category_type} 카테고리 시장 점유율")
        
        # 시장 점유율 상세
        if 'market_share' in category_data.get('business_insights', {}):
            st.markdown("#### 🏆 브랜드별 시장 점유율 (고유제품 기준)")
            share_data = category_data['business_insights']['market_share']
            
            share_df = pd.DataFrame([
                {'브랜드': brand, '고유제품 수': data['고유제품_수'], '점유율': f"{data['점유율_퍼센트']}%"}
                for brand, data in share_data.items()
            ])
            
            st.dataframe(share_df, use_container_width=True)
        else:
            st.info("시장 점유율 데이터가 없습니다.")
    
    with tab3:
        # 카테고리 정보 요약
        st.markdown(f"#### 📈 {category_type} 카테고리 분석 요약")
        st.json({
            "카테고리명": category_data.get('category_name', 'Unknown'),
            "총_분석제품수": category_data.get('total_products_analyzed', 0),
            "고유제품수": category_data.get('total_unique_products', 0),
            "서로브랜드_제품수": category_data.get('our_products_count', 0),
            "서로브랜드_고유제품수": category_data.get('our_unique_products_count', 0),
            "경쟁사_제품수": category_data.get('competitor_products_count', 0),
            "경쟁사_고유제품수": category_data.get('competitor_unique_products_count', 0)
        })

def main():
    st.set_page_config(
        page_title="서로 수정과 - 시장 가격 분석",
        page_icon="🥤",
        layout="wide"
    )
    
    # 헤더
    st.title("🥤 서로 수정과 - 시장 가격 분석 대시보드")
    st.markdown("##### *플랫폼별 가격 경쟁력 및 시장 포지셔닝 분석*")
    
    st.markdown("---")
    
    analyzer = SujeonggwaMarketAnalyzer()
    
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
        
        if st.button("🚀 분석 시작", type="primary", disabled=not uploaded_files):
            st.session_state.run_analysis = True
        
        st.markdown("---")
        st.markdown("### 📋 분석 항목")
        st.markdown("""
        - ✅ 플랫폼별 가격 경쟁력
        - ✅ 시장 포지셔닝 분석  
        - ✅ 브랜드별 점유율
        - ✅ 가격대별 제품 분포
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
            
            df, platform, missing_cols = analyzer.load_and_standardize_excel(uploaded_file)
            
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
            analysis_results, handmade_df, all_products_df = analyzer.analyze_business_critical_data(df_list)
            
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
            
            # 세션 상태 리셋
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
                - 서로 브랜드의 플랫폼별 가격 경쟁력 분석
                - 단위가격(100ml당) 기준 시장 포지셔닝  
                - 경쟁사 대비 가격 차이 및 경쟁력 평가
                
                **📊 시장 현황 파악**
                - 브랜드별 시장 점유율 분석
                - 가격대별 제품 분포 및 우리 브랜드 위치
                - 플랫폼별 제품 현황 비교
                
                ### 📁 파일 업로드 가이드
                - **지원 형식**: Excel 파일 (.xlsx, .xls)
                - **파일명 예시**: "네이버 수정과 가격", "쿠팡 수정과 가격" 등
                - **필수 컬럼**: 브랜드, 제품명, 용량(ml), 최저가(배송비 포함), 최저가 단위가격(100ml당) 등
                """)

# Streamlit 앱 실행
if __name__ == "__main__":
    # 세션 상태 초기화
    if 'run_analysis' not in st.session_state:
        st.session_state.run_analysis = False
    
    main()
