import pandas as pd
import streamlit as st
from datetime import datetime
from config import AppConfig

class BusinessAnalyzer:
    """수정과 시장 분석의 핵심 비즈니스 로직을 담당하는 클래스"""
    
    def __init__(self, our_brand=None):
        """비즈니스 분석기 초기화
        
        Args:
            our_brand (str, optional): 우리 브랜드명. 기본값은 config에서 가져옴
        """
        self.our_brand = our_brand or AppConfig.OUR_BRAND
        self.analysis_settings = AppConfig.ANALYSIS_SETTINGS
        self.business_insights_config = AppConfig.BUSINESS_INSIGHTS
    
    def analyze_business_critical_data(self, df_list):
        """소상공인 관점의 핵심 비즈니스 분석
        
        Args:
            df_list (list): 정제된 DataFrame들의 리스트
            
        Returns:
            tuple: (분석 결과, 수제 제품 DataFrame, 전체 제품 DataFrame)
        """
        if not df_list:
            return {
            '제품': f"{our_product.get('제품명', '')} {our_product.get('용량(ml)', 0)}ml {our_product.get('개수', 0)}개",
            '우리_단위가격': f"{our_unit_price:,.0f}원",
            '경쟁사_평균': f"{competitor_avg:,.0f}원",
            '경쟁사_최저': f"{competitor_min:,.0f}원",
            '경쟁사_최고': f"{competitor_max:,.0f}원",
            '가격차이': f"{price_gap:+,.0f}원",
            '가격차이_퍼센트': f"{price_gap_percent:+.1f}%",
            '시장_포지션': f"{position_color} {market_position}",
            '경쟁사_수': len(competitors),
            '비교_기준': comparison_type,
            '주요_경쟁사': competitor_details[:self.analysis_settings['main_competitors_count']]
        }
    
    def _determine_market_position(self, our_price, competitor_min, competitor_avg, competitor_max):
        """시장 포지션 결정
        
        Args:
            our_price (float): 우리 가격
            competitor_min (float): 경쟁사 최저가
            competitor_avg (float): 경쟁사 평균가
            competitor_max (float): 경쟁사 최고가
            
        Returns:
            tuple: (포지션명, 이모지)
        """
        if our_price <= competitor_min:
            return "최저가", "🎯"
        elif our_price <= competitor_avg:
            return "평균 이하", "📊"
        elif our_price <= competitor_max:
            return "평균 이상", "📈"
        else:
            return "최고가", "💰"
    
    def _get_competitor_details(self, competitors):
        """경쟁사 세부 정보 생성
        
        Args:
            competitors (DataFrame): 경쟁사 데이터
            
        Returns:
            list: 경쟁사 세부 정보 리스트
        """
        competitor_details = []
        
        for _, comp in competitors.head(5).iterrows():  # 상위 5개만
            comp_volume = comp.get('용량(ml)', 'N/A')
            comp_count = comp.get('개수', 'N/A')
            comp_price = comp.get('최저가 단위가격(100ml당)', 'N/A')
            comp_brand = comp.get('브랜드', 'N/A')
            
            if comp_price != 'N/A' and not pd.isna(comp_price):
                detail = f"{comp_brand} {comp_volume}ml×{comp_count}개 ({comp_price:,.0f}원/100ml)"
            else:
                detail = f"{comp_brand} {comp_volume}ml×{comp_count}개 (가격정보없음)"
            
            competitor_details.append(detail)
        
        return competitor_details
    
    def _analyze_volume_market(self, df):
        """용량별/개수별 시장 현황 분석
        
        Args:
            df (DataFrame): 분석할 데이터프레임
            
        Returns:
            list: 용량별 시장 현황
        """
        if '용량(ml)' not in df.columns or '개수' not in df.columns:
            return []
        
        try:
            df_for_volume = df.dropna(subset=['용량(ml)', '개수'])
            
            if df_for_volume.empty:
                return []
            
            # 용량+개수 조합별 제품 수 계산
            volume_count_combinations = df_for_volume.groupby(['용량(ml)', '개수']).size().reset_index(name='제품수')
            volume_count_combinations = volume_count_combinations.sort_values('제품수', ascending=False)
            
            our_products = df[df['브랜드'] == self.our_brand]
            volume_count_market = []
            
            top_combinations = self.analysis_settings['top_volume_combinations']
            
            for _, combo in volume_count_combinations.head(top_combinations).iterrows():
                volume = combo['용량(ml)']
                count = combo['개수']
                total_products = combo['제품수']
                
                # 해당 조합에서 우리 제품 수
                our_products_in_combo = len(our_products[
                    (our_products['용량(ml)'] == volume) & 
                    (our_products['개수'] == count)
                ])
                
                # 해당 조합의 가격 정보
                combo_products = df_for_volume[
                    (df_for_volume['용량(ml)'] == volume) & 
                    (df_for_volume['개수'] == count)
                ]
                
                combo_info = {
                    '용량_개수': f"{volume}ml {count}개",
                    '총_제품수': int(total_products),
                    '우리_제품수': int(our_products_in_combo)
                }
                
                # 가격 정보 추가
                self._add_combo_price_info(combo_info, combo_products)
                
                volume_count_market.append(combo_info)
            
            return volume_count_market
            
        except Exception as e:
            st.warning(f"용량별 시장 분석 중 오류: {str(e)}")
            return []
    
    def _add_combo_price_info(self, combo_info, combo_products):
        """조합별 가격 정보 추가
        
        Args:
            combo_info (dict): 조합 정보
            combo_products (DataFrame): 조합 제품 데이터
        """
        if ('최저가 단위가격(100ml당)' in combo_products.columns and 
            not combo_products['최저가 단위가격(100ml당)'].isna().all()):
            
            unit_prices = combo_products['최저가 단위가격(100ml당)'].dropna()
            if len(unit_prices) > 0:
                combo_info.update({
                    '평균_단위가격': f"{unit_prices.mean():,.0f}원",
                    '최저_단위가격': f"{unit_prices.min():,.0f}원",
                    '최고_단위가격': f"{unit_prices.max():,.0f}원"
                })
            else:
                combo_info.update({
                    '평균_단위가격': 'N/A',
                    '최저_단위가격': 'N/A',
                    '최고_단위가격': 'N/A'
                })
        else:
            combo_info.update({
                '평균_단위가격': 'N/A',
                '최저_단위가격': 'N/A',
                '최고_단위가격': 'N/A'
            })
    
    def _analyze_market_share(self, df):
        """브랜드별 시장 점유율 분석
        
        Args:
            df (DataFrame): 분석할 데이터프레임
            
        Returns:
            dict: 브랜드별 점유율 정보
        """
        try:
            unique_products = self._calculate_unique_products(df)
            brand_share = unique_products['브랜드'].value_counts()
            total_unique_products = len(unique_products)
            
            brand_share_percent = {}
            top_brands_count = self.analysis_settings['top_brands_count']
            
            for brand, count in brand_share.head(top_brands_count).items():
                if pd.notna(brand) and total_unique_products > 0:
                    percentage = (count / total_unique_products) * 100
                    brand_share_percent[brand] = {
                        '제품_수': int(count),
                        '점유율_퍼센트': round(percentage, 1)
                    }
            
            return brand_share_percent
            
        except Exception as e:
            st.warning(f"브랜드별 점유율 분석 중 오류: {str(e)}")
            return {}
    
    def get_market_opportunities(self, df):
        """시장 기회 분석 (추가 기능)
        
        Args:
            df (DataFrame): 분석할 데이터프레임
            
        Returns:
            dict: 시장 기회 정보
        """
        opportunities = {}
        
        # 진출하지 않은 용량/개수 조합 찾기
        volume_market = self._analyze_volume_market(df)
        untapped_markets = [
            market for market in volume_market 
            if market.get('우리_제품수', 0) == 0
        ]
        
        opportunities['untapped_volume_combinations'] = untapped_markets[:5]  # 상위 5개
        
        # 가격 경쟁력이 좋은 영역 찾기
        competitiveness = self._analyze_price_competitiveness(df)
        competitive_platforms = {}
        
        for platform, products in competitiveness.items():
            competitive_products = [
                p for p in products 
                if "🎯" in p.get('시장_포지션', '') or "📊" in p.get('시장_포지션', '')
            ]
            if competitive_products:
                competitive_platforms[platform] = len(competitive_products)
        
        opportunities['competitive_platforms'] = competitive_platforms
        
        return opportunities
    
    def generate_business_recommendations(self, analysis_results):
        """비즈니스 추천사항 생성 (추가 기능)
        
        Args:
            analysis_results (dict): 분석 결과
            
        Returns:
            list: 추천사항 리스트
        """
        recommendations = []
        
        # 수제 카테고리 분석
        handmade_category = analysis_results.get('handmade_category', {})
        our_products_count = handmade_category.get('our_unique_products_count', 0)
        competitor_count = handmade_category.get('competitor_unique_products_count', 0)
        
        # 제품 라인업 추천
        if our_products_count < competitor_count * 0.1:  # 경쟁사의 10% 미만
            recommendations.append({
                'priority': 'high',
                'category': '제품 라인업',
                'message': f"현재 {our_products_count}개 제품으로 경쟁사 대비 매우 적습니다. 제품 다양화가 시급합니다."
            })
        
        # 가격 경쟁력 추천
        insights = handmade_category.get('business_insights', {})
        competitiveness = insights.get('detailed_competitiveness', {})
        
        premium_products = 0
        total_products = 0
        
        for platform_products in competitiveness.values():
            for product in platform_products:
                total_products += 1
                if "💰" in product.get('시장_포지션', ''):
                    premium_products += 1
        
        if total_products > 0 and premium_products / total_products > 0.5:
            recommendations.append({
                'priority': 'medium',
                'category': '가격 전략',
                'message': f"제품의 {premium_products/total_products*100:.0f}%가 고가격대입니다. 가격 재검토를 권장합니다."
            })
        
        # 시장 기회 추천
        volume_market = insights.get('volume_count_market', [])
        untapped_count = sum(1 for market in volume_market if market.get('우리_제품수', 0) == 0)
        
        if untapped_count > 0:
            recommendations.append({
                'priority': 'medium', 
                'category': '시장 진출',
                'message': f"인기 용량 조합 중 {untapped_count}개 영역에 진출 기회가 있습니다."
            })
        
        return recommendations None, None, None
        
        # 모든 데이터 통합
        combined_df = pd.concat(df_list, ignore_index=True)
        
        # 1차: 수제 제품만 필터링 (공장형 여부 = 0)
        handmade_df, all_products_df = self._separate_product_types(combined_df)
        
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
            'platforms_analyzed': combined_df['플랫폼'].unique().tolist() if '플랫폼' in combined_df.columns else []
        }
        
        return analysis_results, handmade_df, all_products_df
    
    def _separate_product_types(self, combined_df):
        """수제 제품과 전체 제품으로 분리
        
        Args:
            combined_df (DataFrame): 통합된 데이터프레임
            
        Returns:
            tuple: (수제 제품 DataFrame, 전체 제품 DataFrame)
        """
        if '공장형 여부' in combined_df.columns:
            handmade_df = combined_df[combined_df['공장형 여부'] == 0].copy()
            all_products_df = combined_df.copy()
        else:
            handmade_df = combined_df.copy()
            all_products_df = combined_df.copy()
            st.warning("'공장형 여부' 컬럼을 찾을 수 없습니다.")
        
        return handmade_df, all_products_df
    
    def _analyze_category(self, df, category_name):
        """카테고리별 분석 (수제 또는 전체)
        
        Args:
            df (DataFrame): 분석할 데이터프레임
            category_name (str): 카테고리명
            
        Returns:
            dict: 분석 결과
        """
        if df.empty:
            return self._create_empty_analysis_result(category_name)
        
        # 기본 통계
        basic_stats = self._calculate_basic_statistics(df)
        
        # 비즈니스 인사이트 분석
        business_insights = self._analyze_business_insights(df)
        
        # 결과 통합
        category_results = {
            'category_name': category_name,
            **basic_stats,
            'business_insights': business_insights
        }
        
        return category_results
    
    def _create_empty_analysis_result(self, category_name):
        """빈 분석 결과 생성
        
        Args:
            category_name (str): 카테고리명
            
        Returns:
            dict: 빈 분석 결과
        """
        return {
            'category_name': category_name,
            'total_products_analyzed': 0,
            'total_unique_products': 0,
            'our_products_count': 0,
            'our_unique_products_count': 0,
            'competitor_products_count': 0,
            'competitor_unique_products_count': 0,
            'business_insights': {}
        }
    
    def _calculate_basic_statistics(self, df):
        """기본 통계 계산
        
        Args:
            df (DataFrame): 분석할 데이터프레임
            
        Returns:
            dict: 기본 통계 정보
        """
        # 서로 브랜드와 경쟁사 분리
        our_products = df[df['브랜드'] == self.our_brand].copy()
        competitor_products = df[df['브랜드'] != self.our_brand].copy()
        
        # 고유 제품 계산을 위한 그룹핑
        unique_products = self._calculate_unique_products(df)
        our_unique_products = unique_products[unique_products['브랜드'] == self.our_brand]
        competitor_unique_products = unique_products[unique_products['브랜드'] != self.our_brand]
        
        return {
            'total_products_analyzed': len(df),
            'total_unique_products': len(unique_products),
            'our_products_count': len(our_products),
            'our_unique_products_count': len(our_unique_products),
            'competitor_products_count': len(competitor_products),
            'competitor_unique_products_count': len(competitor_unique_products)
        }
    
    def _calculate_unique_products(self, df):
        """고유 제품 수 계산
        
        Args:
            df (DataFrame): 분석할 데이터프레임
            
        Returns:
            DataFrame: 고유 제품 데이터프레임
        """
        # 필수 컬럼 체크
        required_for_analysis = ['브랜드', '제품명', '용량(ml)', '개수']
        available_cols = [col for col in required_for_analysis if col in df.columns]
        
        if len(available_cols) < 2:
            st.warning(f"분석에 필요한 기본 컬럼이 부족합니다: {required_for_analysis}")
            return df.groupby(['브랜드']).size().reset_index(name='count')
        
        # 제품 그룹핑
        group_cols = available_cols
        agg_dict = {}
        
        if '최저가(배송비 포함)' in df.columns:
            agg_dict['최저가(배송비 포함)'] = 'min'
        if '최저가 단위가격(100ml당)' in df.columns:
            agg_dict['최저가 단위가격(100ml당)'] = 'min'
        if '플랫폼' in df.columns:
            agg_dict['플랫폼'] = lambda x: list(x.unique())
        
        if not agg_dict:
            unique_products = df.groupby(group_cols).size().reset_index(name='count')
        else:
            unique_products = df.groupby(group_cols).agg(agg_dict).reset_index()
        
        return unique_products
    
    def _analyze_business_insights(self, df):
        """비즈니스 인사이트 분석
        
        Args:
            df (DataFrame): 분석할 데이터프레임
            
        Returns:
            dict: 비즈니스 인사이트
        """
        insights = {}
        
        # 1. 우리 제품 상세 현황
        insights['our_product_details'] = self._analyze_our_products(df)
        
        # 2. 플랫폼별 가격 경쟁력
        insights['detailed_competitiveness'] = self._analyze_price_competitiveness(df)
        
        # 3. 용량별/개수별 시장 현황
        insights['volume_count_market'] = self._analyze_volume_market(df)
        
        # 4. 브랜드별 시장 점유율
        insights['market_share'] = self._analyze_market_share(df)
        
        return insights
    
    def _analyze_our_products(self, df):
        """우리 제품 상세 분석
        
        Args:
            df (DataFrame): 분석할 데이터프레임
            
        Returns:
            list: 우리 제품 상세 정보
        """
        our_products = df[df['브랜드'] == self.our_brand].copy()
        competitor_products = df[df['브랜드'] != self.our_brand].copy()
        
        if our_products.empty:
            return []
        
        unique_our_products = self._calculate_unique_products(our_products)
        
        if unique_our_products.empty:
            return []
        
        our_product_details = []
        
        # 시장 평균 계산
        market_averages = self._calculate_market_averages(competitor_products)
        
        # 우리 제품 성과 순위 계산
        performance_rankings = self._calculate_performance_rankings(our_products, unique_our_products)
        
        for _, product in unique_our_products.iterrows():
            product_info = self._create_product_info(
                product, our_products, market_averages, performance_rankings
            )
            our_product_details.append(product_info)
        
        return our_product_details
    
    def _calculate_market_averages(self, competitor_products):
        """시장 평균 계산
        
        Args:
            competitor_products (DataFrame): 경쟁사 제품 데이터
            
        Returns:
            dict: 시장 평균 정보
        """
        averages = {'reviews': 0, 'rating': 0}
        
        # 리뷰/평점 컬럼 찾기
        review_col, rating_col = self._find_review_rating_columns(competitor_products)
        
        if review_col and rating_col:
            market_reviews = competitor_products[
                competitor_products[review_col].notna() & 
                (competitor_products[review_col] > 0)
            ]
            market_ratings = competitor_products[
                competitor_products[rating_col].notna() & 
                (competitor_products[rating_col] > 0)
            ]
            
            if not market_reviews.empty:
                averages['reviews'] = market_reviews[review_col].mean()
            if not market_ratings.empty:
                averages['rating'] = market_ratings[rating_col].mean()
        
        return averages
    
    def _find_review_rating_columns(self, df):
        """리뷰/평점 컬럼 찾기
        
        Args:
            df (DataFrame): 데이터프레임
            
        Returns:
            tuple: (리뷰 컬럼명, 평점 컬럼명)
        """
        review_col = None
        rating_col = None
        
        available_columns = list(df.columns)
        
        # 리뷰 컬럼 찾기
        for col in ['리뷰 개수', '리뷰개수', 'review_count', '리뷰수']:
            if col in available_columns:
                review_col = col
                break
        
        # 평점 컬럼 찾기
        for col in ['평점', '평균평점', 'rating', '별점']:
            if col in available_columns:
                rating_col = col
                break
        
        return review_col, rating_col
    
    def _calculate_performance_rankings(self, our_products, unique_our_products):
        """우리 제품 성과 순위 계산
        
        Args:
            our_products (DataFrame): 우리 제품 데이터
            unique_our_products (DataFrame): 고유 우리 제품 데이터
            
        Returns:
            list: 성과 순위 정보
        """
        review_col, rating_col = self._find_review_rating_columns(our_products)
        
        if not review_col or not rating_col:
            return []
        
        performance_list = []
        
        for _, product in unique_our_products.iterrows():
            # 해당 제품의 리뷰/평점 데이터 찾기
            matching_products = our_products[
                (our_products['브랜드'] == product['브랜드']) & 
                (our_products['제품명'] == product['제품명']) &
                (our_products['용량(ml)'] == product['용량(ml)']) &
                (our_products['개수'] == product['개수'])
            ]
            
            if not matching_products.empty:
                product_reviews = matching_products[review_col].max() if review_col in matching_products.columns else 0
                product_rating = matching_products[rating_col].max() if rating_col in matching_products.columns else 0
                
                if pd.isna(product_reviews):
                    product_reviews = 0
                if pd.isna(product_rating):
                    product_rating = 0
                
                # 성과 점수 계산 (리뷰수 × 평점)
                performance_score = product_reviews * product_rating if product_rating > 0 else 0
                
                performance_list.append({
                    'product_key': f"{product['제품명']}_{product['용량(ml)']}_{product['개수']}",
                    'reviews': product_reviews,
                    'rating': product_rating,
                    'performance_score': performance_score
                })
        
        # 성과 순위 정렬
        performance_list.sort(key=lambda x: x['performance_score'], reverse=True)
        return performance_list
    
    def _create_product_info(self, product, our_products, market_averages, performance_rankings):
        """제품 정보 생성
        
        Args:
            product: 제품 정보
            our_products (DataFrame): 우리 제품 데이터
            market_averages (dict): 시장 평균
            performance_rankings (list): 성과 순위
            
        Returns:
            dict: 제품 상세 정보
        """
        product_key = f"{product['제품명']}_{product['용량(ml)']}_{product['개수']}"
        
        # 기본 정보
        product_info = {
            '브랜드': product.get('브랜드', ''),
            '제품명': product.get('제품명', ''),
            '용량': f"{product.get('용량(ml)', 0)}ml" if pd.notna(product.get('용량(ml)')) else 'N/A',
            '개수': f"{product.get('개수', 0)}개" if pd.notna(product.get('개수')) else 'N/A'
        }
        
        # 가격 정보 추가
        self._add_price_info(product_info, product)
        
        # 리뷰/평점 기반 확장 정보 추가
        self._add_performance_info(product_info, product_key, performance_rankings, market_averages)
        
        return product_info
    
    def _add_price_info(self, product_info, product):
        """제품 정보에 가격 정보 추가
        
        Args:
            product_info (dict): 제품 정보 딕셔너리
            product: 제품 데이터
        """
        if '최저가(배송비 포함)' in product.index and pd.notna(product['최저가(배송비 포함)']):
            product_info['최저가'] = f"{product['최저가(배송비 포함)']:,.0f}원"
        else:
            product_info['최저가'] = 'N/A'
        
        if '최저가 단위가격(100ml당)' in product.index and pd.notna(product['최저가 단위가격(100ml당)']):
            product_info['단위가격'] = f"{product['최저가 단위가격(100ml당)']:,.0f}원/100ml"
        else:
            product_info['단위가격'] = 'N/A'
        
        if '플랫폼' in product.index and isinstance(product['플랫폼'], list):
            product_info['판매플랫폼'] = ', '.join(product['플랫폼'])
        else:
            product_info['판매플랫폼'] = 'N/A'
    
    def _add_performance_info(self, product_info, product_key, performance_rankings, market_averages):
        """제품 정보에 성과 정보 추가
        
        Args:
            product_info (dict): 제품 정보 딕셔너리
            product_key (str): 제품 키
            performance_rankings (list): 성과 순위
            market_averages (dict): 시장 평균
        """
        product_performance = next(
            (p for p in performance_rankings if p['product_key'] == product_key), None
        )
        
        if product_performance:
            reviews = product_performance['reviews']
            rating = product_performance['rating']
            
            # 시장 반응도 계산
            product_info['시장반응도'] = self._calculate_market_reaction(reviews, market_averages['reviews'])
            
            # 고객 만족도 계산
            product_info['고객만족도'] = self._calculate_customer_satisfaction(rating)
            
            # 브랜드 내 순위 계산
            product_info['브랜드내순위'] = self._calculate_brand_ranking(product_key, performance_rankings)
        else:
            product_info['시장반응도'] = "데이터 없음"
            product_info['고객만족도'] = "데이터 없음"
            product_info['브랜드내순위'] = "데이터 없음"
    
    def _calculate_market_reaction(self, reviews, market_avg_reviews):
        """시장 반응도 계산
        
        Args:
            reviews (float): 제품 리뷰 수
            market_avg_reviews (float): 시장 평균 리뷰 수
            
        Returns:
            str: 시장 반응도 문자열
        """
        if market_avg_reviews > 0 and reviews > 0:
            market_ratio = reviews / market_avg_reviews
            if market_ratio >= 2.0:
                return f"🔥 {reviews:,.0f}개 (시장평균의 {market_ratio:.1f}배)"
            elif market_ratio >= 1.0:
                return f"📈 {reviews:,.0f}개 (시장평균의 {market_ratio:.1f}배)"
            else:
                return f"📊 {reviews:,.0f}개 (시장평균의 {market_ratio:.1f}배)"
        else:
            return f"{reviews:,.0f}개" if reviews > 0 else "리뷰 없음"
    
    def _calculate_customer_satisfaction(self, rating):
        """고객 만족도 계산
        
        Args:
            rating (float): 평점
            
        Returns:
            str: 고객 만족도 문자열
        """
        if rating > 0:
            excellent_threshold = self.business_insights_config['performance_metrics']['excellent_rating']
            good_threshold = self.business_insights_config['performance_metrics']['good_rating']
            
            if rating >= excellent_threshold:
                return f"⭐ {rating:.1f}점 (우수)"
            elif rating >= good_threshold:
                return f"⭐ {rating:.1f}점 (양호)"
            else:
                return f"⚠️ {rating:.1f}점 (개선필요)"
        else:
            return "평점 없음"
    
    def _calculate_brand_ranking(self, product_key, performance_rankings):
        """브랜드 내 순위 계산
        
        Args:
            product_key (str): 제품 키
            performance_rankings (list): 성과 순위
            
        Returns:
            str: 브랜드 내 순위 문자열
        """
        rank = next((i+1 for i, p in enumerate(performance_rankings) if p['product_key'] == product_key), None)
        
        if rank and len(performance_rankings) > 1:
            if rank == 1:
                return f"🏆 1위/{len(performance_rankings)}개"
            elif rank <= 3:
                return f"🥉 {rank}위/{len(performance_rankings)}개"
            else:
                return f"📊 {rank}위/{len(performance_rankings)}개"
        else:
            return "단일 제품"
    
    def _analyze_price_competitiveness(self, df):
        """플랫폼별 가격 경쟁력 분석
        
        Args:
            df (DataFrame): 분석할 데이터프레임
            
        Returns:
            dict: 플랫폼별 경쟁력 분석 결과
        """
        # 이 메서드는 길어서 별도 메서드들로 분리
        return self._detailed_competitiveness_analysis(df)
    
    def _detailed_competitiveness_analysis(self, df):
        """상세 경쟁력 분석
        
        Args:
            df (DataFrame): 분석할 데이터프레임
            
        Returns:
            dict: 상세 경쟁력 분석 결과
        """
        if not all(col in df.columns for col in ['최저가 단위가격(100ml당)', '플랫폼', '용량(ml)', '개수']):
            return {}
        
        our_products = df[df['브랜드'] == self.our_brand]
        competitor_products = df[df['브랜드'] != self.our_brand]
        
        competitiveness = {}
        
        for platform in df['플랫폼'].unique():
            if pd.isna(platform):
                continue
            
            platform_analysis = self._analyze_platform_competitiveness(
                platform, our_products, competitor_products
            )
            
            if platform_analysis:
                competitiveness[platform] = platform_analysis
        
        return competitiveness
    
    def _analyze_platform_competitiveness(self, platform, our_products, competitor_products):
        """플랫폼별 경쟁력 분석
        
        Args:
            platform (str): 플랫폼명
            our_products (DataFrame): 우리 제품 데이터
            competitor_products (DataFrame): 경쟁사 제품 데이터
            
        Returns:
            list: 플랫폼 경쟁력 분석 결과
        """
        our_platform_data = our_products[our_products['플랫폼'] == platform]
        competitor_platform_data = competitor_products[competitor_products['플랫폼'] == platform]
        
        if our_platform_data.empty or competitor_platform_data.empty:
            return None
        
        our_product_competitiveness = []
        
        for _, our_product in our_platform_data.iterrows():
            comp_analysis = self._analyze_single_product_competitiveness(
                our_product, competitor_platform_data
            )
            if comp_analysis:
                our_product_competitiveness.append(comp_analysis)
        
        return our_product_competitiveness if our_product_competitiveness else None
    
    def _analyze_single_product_competitiveness(self, our_product, competitor_platform_data):
        """단일 제품 경쟁력 분석
        
        Args:
            our_product: 우리 제품 정보
            competitor_platform_data (DataFrame): 경쟁사 플랫폼 데이터
            
        Returns:
            dict: 단일 제품 경쟁력 분석 결과
        """
        try:
            our_volume = our_product.get('용량(ml)')
            our_count = our_product.get('개수')
            our_unit_price = our_product.get('최저가 단위가격(100ml당)')
            
            if pd.isna(our_volume) or pd.isna(our_count) or pd.isna(our_unit_price):
                return None
            
            # 경쟁사 찾기 (단계별)
            selected_competitors, comparison_type = self._find_best_competitors(
                our_volume, our_count, competitor_platform_data
            )
            
            if selected_competitors is None or selected_competitors.empty:
                return None
            
            # 경쟁력 분석 수행
            return self._perform_competitiveness_analysis(
                our_product, our_unit_price, selected_competitors, comparison_type
            )
            
        except Exception as e:
            return None
    
    def _find_best_competitors(self, our_volume, our_count, competitor_platform_data):
        """최적의 경쟁사 찾기
        
        Args:
            our_volume (float): 우리 제품 용량
            our_count (int): 우리 제품 개수
            competitor_platform_data (DataFrame): 경쟁사 플랫폼 데이터
            
        Returns:
            tuple: (선택된 경쟁사 데이터, 비교 기준)
        """
        # 1단계: 정확히 같은 용량+개수
        exact_competitors = competitor_platform_data[
            (competitor_platform_data['용량(ml)'] == our_volume) & 
            (competitor_platform_data['개수'] == our_count)
        ]
        
        if not exact_competitors.empty:
            return exact_competitors, "동일 용량+개수"
        
        # 2단계: 유사 용량대 (±20% 범위)
        volume_range = our_volume * self.analysis_settings['volume_similarity_range']
        volume_range_min = our_volume - volume_range
        volume_range_max = our_volume + volume_range
        
        similar_volume_competitors = competitor_platform_data[
            (competitor_platform_data['용량(ml)'] >= volume_range_min) & 
            (competitor_platform_data['용량(ml)'] <= volume_range_max) &
            (competitor_platform_data['개수'] == our_count)
        ]
        
        if not similar_volume_competitors.empty:
            return similar_volume_competitors, f"유사 용량({volume_range_min:.0f}~{volume_range_max:.0f}ml)+동일개수"
        
        # 3단계: 같은 개수
        same_count_competitors = competitor_platform_data[
            competitor_platform_data['개수'] == our_count
        ]
        
        if not same_count_competitors.empty:
            return same_count_competitors, "동일 개수"
        
        # 4단계: 전체 경쟁사
        if not competitor_platform_data.empty:
            return competitor_platform_data, "전체 시장"
        
        return None, ""
    
    def _perform_competitiveness_analysis(self, our_product, our_unit_price, competitors, comparison_type):
        """경쟁력 분석 수행
        
        Args:
            our_product: 우리 제품 정보
            our_unit_price (float): 우리 제품 단위가격
            competitors (DataFrame): 경쟁사 데이터
            comparison_type (str): 비교 기준
            
        Returns:
            dict: 경쟁력 분석 결과
        """
        competitor_unit_prices = competitors['최저가 단위가격(100ml당)'].dropna()
        
        if len(competitor_unit_prices) == 0:
            return None
        
        competitor_avg = competitor_unit_prices.mean()
        competitor_min = competitor_unit_prices.min()
        competitor_max = competitor_unit_prices.max()
        
        price_gap = our_unit_price - competitor_avg
        price_gap_percent = (price_gap / competitor_avg) * 100 if competitor_avg > 0 else 0
        
        # 시장 위치 판단
        market_position, position_color = self._determine_market_position(
            our_unit_price, competitor_min, competitor_avg, competitor_max
        )
        
        # 경쟁사 세부 정보
        competitor_details = self._get_competitor_details(competitors)
        
        return
