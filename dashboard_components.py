import streamlit as st
import pandas as pd
from config import AppConfig

class DashboardRenderer:
    """대시보드 UI 렌더링을 담당하는 클래스"""
    
    def __init__(self):
        """대시보드 렌더러 초기화"""
        self.ui_messages = AppConfig.UI_MESSAGES
        self.our_brand = AppConfig.OUR_BRAND
    
    @staticmethod
    def render_analysis_results(analysis_results, json_content, timestamp, github_success):
        """분석 결과를 표시하는 메인 함수
        
        Args:
            analysis_results (dict): 분석 결과 데이터
            json_content (str): JSON 형태의 분석 결과
            timestamp (str): 분석 시간
            github_success (bool): GitHub 저장 성공 여부
        """
        if not analysis_results:
            st.error("분석 결과가 없습니다.")
            return
        
        # 성공 메시지 표시
        if github_success:
            st.success("✅ 분석 완료 및 GitHub 저장 성공!")
        else:
            st.warning("⚠️ 분석 완료, GitHub 저장 실패")
        
        # 탭 생성
        tab_handmade, tab_all = st.tabs(["🥛 수제 제품 분석", "🏭 전체 제품 분석 (수제+공장형)"])
        
        with tab_handmade:
            DashboardRenderer.render_category_analysis(
                analysis_results.get('handmade_category', {}), "수제"
            )
        
        with tab_all:
            DashboardRenderer.render_category_analysis(
                analysis_results.get('all_category', {}), "전체"
            )
    
    @staticmethod
    def render_category_analysis(category_data, category_type):
        """카테고리별 분석 결과 표시
        
        Args:
            category_data (dict): 카테고리 분석 데이터
            category_type (str): 카테고리 타입 (수제/전체)
        """
        if not category_data:
            st.warning(f"{category_type} 카테고리 데이터가 없습니다.")
            return
        
        # 핵심 지표 카드 표시
        DashboardRenderer._render_key_metrics(category_data)
        
        st.markdown("---")
        
        # 종합 현황 표시
        st.subheader(f"🥤 서로 브랜드 종합 현황 ({category_type})")
        
        business_insights = category_data.get('business_insights', {})
        
        # 1. 제품별 상세 현황
        DashboardRenderer._render_product_details(business_insights)
        
        st.markdown("---")
        
        # 2. 제품별 가격 경쟁력
        DashboardRenderer._render_price_competitiveness(business_insights)
        
        st.markdown("---")
        
        # 3. 용량별/개수별 시장 현황
        DashboardRenderer._render_volume_market_analysis(business_insights)
        
        st.markdown("---")
        
        # 4. 브랜드별 시장 분석
        DashboardRenderer._render_brand_market_share(business_insights)
    
    @staticmethod
    def _render_key_metrics(category_data):
        """핵심 지표 카드 렌더링
        
        Args:
            category_data (dict): 카테고리 데이터
        """
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
    
    @staticmethod
    def _render_product_details(business_insights):
        """제품별 상세 현황 렌더링
        
        Args:
            business_insights (dict): 비즈니스 인사이트 데이터
        """
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
    
    @staticmethod
    def _render_price_competitiveness(business_insights):
        """가격 경쟁력 렌더링
        
        Args:
            business_insights (dict): 비즈니스 인사이트 데이터
        """
        st.markdown("### 💰 제품별 가격 경쟁력")
        
        if 'detailed_competitiveness' in business_insights:
            comp_data = business_insights['detailed_competitiveness']
            
            if comp_data:
                for platform, products in comp_data.items():
                    with st.expander(f"🏪 {platform} - {len(products)}개 제품"):
                        DashboardRenderer._render_platform_competitiveness(products)
            else:
                st.info("제품별 경쟁력 데이터가 없습니다.")
        else:
            st.info("제품별 경쟁력 데이터가 없습니다.")
    
    @staticmethod
    def _render_platform_competitiveness(products):
        """플랫폼별 경쟁력 렌더링
        
        Args:
            products (list): 플랫폼별 제품 리스트
        """
        for product in products:
            st.markdown(f"**{product.get('제품', 'N/A')}**")
            
            # 비교 기준 표시
            comparison_basis = product.get('비교_기준', 'N/A')
            DashboardRenderer._render_comparison_basis(comparison_basis)
            
            # 가격 정보 표시
            DashboardRenderer._render_price_metrics(product)
            
            # 주요 경쟁사 표시
            DashboardRenderer._render_main_competitors(product)
            
            st.markdown("---")
    
    @staticmethod
    def _render_comparison_basis(comparison_basis):
        """비교 기준 표시
        
        Args:
            comparison_basis (str): 비교 기준
        """
        if comparison_basis == "동일 용량+개수":
            st.success(f"🎯 **비교 기준**: {comparison_basis}")
        elif "유사 용량" in comparison_basis:
            st.info(f"📊 **비교 기준**: {comparison_basis}")
        elif comparison_basis == "동일 개수":
            st.warning(f"📈 **비교 기준**: {comparison_basis}")
        else:
            st.error(f"💰 **비교 기준**: {comparison_basis}")
    
    @staticmethod
    def _render_price_metrics(product):
        """가격 지표 표시
        
        Args:
            product (dict): 제품 정보
        """
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
            
            DashboardRenderer._render_market_position(position, competitor_count)
    
    @staticmethod
    def _render_market_position(position, competitor_count):
        """시장 포지션 표시
        
        Args:
            position (str): 시장 포지션
            competitor_count (int): 경쟁사 수
        """
        if "🎯" in position:
            st.success(f"**{position}** (경쟁사 {competitor_count}개)")
        elif "📊" in position:
            st.info(f"**{position}** (경쟁사 {competitor_count}개)")
        elif "📈" in position:
            st.warning(f"**{position}** (경쟁사 {competitor_count}개)")
        else:
            st.error(f"**{position}** (경쟁사 {competitor_count}개)")
    
    @staticmethod
    def _render_main_competitors(product):
        """주요 경쟁사 표시
        
        Args:
            product (dict): 제품 정보
        """
        main_competitors = product.get('주요_경쟁사', [])
        if main_competitors and main_competitors != ["분석 중"]:
            st.markdown("**📋 주요 경쟁사:**")
            for i, competitor in enumerate(main_competitors, 1):
                st.write(f"  {i}. {competitor}")
    
    @staticmethod
    def _render_volume_market_analysis(business_insights):
        """용량별 시장 분석 렌더링
        
        Args:
            business_insights (dict): 비즈니스 인사이트 데이터
        """
        st.markdown("### 📊 용량별/개수별 시장 현황")
        
        if 'volume_count_market' in business_insights:
            market_data = business_insights['volume_count_market']
            
            if market_data:
                st.markdown("#### 🔥 인기 용량/개수 조합 (상위 10개)")
                
                market_df = pd.DataFrame(market_data)
                st.dataframe(market_df, use_container_width=True)
                
                # 진출 기회 시장 찾기
                DashboardRenderer._render_market_opportunities(market_data)
            else:
                st.warning("용량별 시장 데이터가 없습니다.")
        else:
            st.info("용량별 시장 분석 데이터가 없습니다.")
    
    @staticmethod
    def _render_market_opportunities(market_data):
        """시장 진출 기회 렌더링
        
        Args:
            market_data (list): 시장 데이터
        """
        untapped_markets = [item for item in market_data if item.get('우리_제품수', 0) == 0]
        
        if untapped_markets:
            st.markdown("#### 💡 진출 기회 있는 시장")
            for market in untapped_markets[:5]:
                volume_count = market.get('용량_개수', 'N/A')
                total_products = market.get('총_제품수', 0)
                avg_price = market.get('평균_단위가격', 'N/A')
                st.info(f"**{volume_count}**: {total_products}개 제품, 평균 단위가격 {avg_price}")
    
    @staticmethod
    def _render_brand_market_share(business_insights):
        """브랜드별 시장 점유율 렌더링
        
        Args:
            business_insights (dict): 비즈니스 인사이트 데이터
        """
        st.markdown("### 🏆 브랜드별 시장 점유율")
        
        if 'market_share' in business_insights:
            share_data = business_insights['market_share']
            
            if share_data:
                share_df = pd.DataFrame([
                    {'브랜드': brand, '제품 수': data.get('제품_수', 0), '점유율': f"{data.get('점유율_퍼센트', 0)}%"}
                    for brand, data in share_data.items()
                ])
                
                st.dataframe(share_df, use_container_width=True)
                
                # 서로 브랜드 순위 분석
                DashboardRenderer._render_brand_ranking(share_data)
            else:
                st.warning("브랜드별 점유율 데이터가 없습니다.")
        else:
            st.info("브랜드별 점유율 데이터가 없습니다.")
    
    @staticmethod
    def _render_brand_ranking(share_data):
        """브랜드 순위 분석 렌더링
        
        Args:
            share_data (dict): 점유율 데이터
        """
        seoro_rank = None
        for idx, (brand, _) in enumerate(share_data.items(), 1):
            if brand == AppConfig.OUR_BRAND:
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
    
    @staticmethod
    def render_sidebar_file_info(uploaded_files, data_processor=None):
        """사이드바 파일 정보 렌더링
        
        Args:
            uploaded_files (list): 업로드된 파일 리스트
            data_processor: 데이터 처리기 (선택사항)
        """
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)}개 파일 업로드됨")
            
            for file in uploaded_files:
                if data_processor:
                    platform = data_processor.extract_platform_from_filename(file.name)
                else:
                    platform = "알 수 없음"
                st.write(f"📄 {platform}: {file.name}")
    
    @staticmethod
    def render_sidebar_analysis_items():
        """사이드바 분석 항목 렌더링"""
        st.markdown("### 📋 분석 항목")
        for item in AppConfig.UI_MESSAGES['analysis_items']:
            st.markdown(f"- {item}")
    
    @staticmethod
    def render_usage_guide():
        """사용 방법 가이드 렌더링"""
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
    
    @staticmethod
    def render_welcome_message():
        """초기 환영 메시지 렌더링"""
        st.info("👈 사이드바에서 엑셀 파일들을 업로드하고 분석을 시작하세요.")
        DashboardRenderer.render_usage_guide()
    
    @staticmethod
    def render_data_quality_info(df_list, data_processor):
        """데이터 품질 정보 렌더링
        
        Args:
            df_list (list): DataFrame 리스트
            data_processor: 데이터 처리기
        """
        if not df_list or not data_processor:
            return
        
        with st.expander("📊 데이터 품질 확인", expanded=False):
            quality_info = data_processor.validate_data_quality(df_list)
            
            st.write(f"📁 총 {quality_info['total_files']}개 파일")
            st.write(f"📊 총 {quality_info['total_products']}개 제품")
            st.write(f"🏪 플랫폼: {', '.join(quality_info['platforms'])}")
            
            if quality_info['quality_issues']:
                st.write("⚠️ 품질 이슈:")
                for issue in quality_info['quality_issues']:
                    st.write(f"  • {issue}")
    
    @staticmethod
    def render_progress_indicator(current_step, total_steps, status_text):
        """진행 상태 표시기 렌더링
        
        Args:
            current_step (int): 현재 단계
            total_steps (int): 전체 단계
            status_text (str): 상태 텍스트
        """
        progress_value = current_step / total_steps
        st.progress(progress_value)
        st.text(status_text)
