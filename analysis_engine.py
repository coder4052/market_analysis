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
            return None, None, None
        
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
        """수제 제품과 전체 제품으로 분리"""
        if '공장형 여부' in combined_df.columns:
            handmade_df = combined_df[combined_df['공장형 여부'] == 0].copy()
            all_products_df = combined_df.copy()
        else:
            handmade_df = combined_df.copy()
            all_products_df = combined_df.copy()
            st.warning("'공장형 여부' 컬럼을 찾을 수 없습니다.")
        
        return handmade_df, all_products_df
    
    def _analyze_category(self, df, category_name):
        """카테고리별 분석 (수제 또는 전체)"""
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
        """빈 분석 결과 생성"""
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
        """기본 통계 계산"""
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
        """고유 제품 수 계산"""
        # 필수 컬럼 체크
        required_for_analysis = ['브랜드', '제품명', '용량(ml)', '개수']
        available_cols = [col for col in required_for_analysis if col in df.columns]
        
        if len(available_cols) < 2:
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
        """비즈니스 인사이트 분석"""
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
        """우리 제품 상세 분석"""
        our_products = df[df['브랜드'] == self.our_brand].copy()
        
        if our_products.empty:
            return []
        
        unique_our_products = self._calculate_unique_products(our_products)
        
        if unique_our_products.empty:
            return []
        
        our_product_details = []
        
        for _, product in unique_our_products.iterrows():
            product_info = {
                '브랜드': product.get('브랜드', ''),
                '제품명': product.get('제품명', ''),
                '용량': f"{product.get('용량(ml)', 0)}ml" if pd.notna(product.get('용량(ml)')) else 'N/A',
                '개수': f"{product.get('개수', 0)}개" if pd.notna(product.get('개수')) else 'N/A'
            }
            
            # 가격 정보 추가
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
            
            # 기본적인 정보만 포함 (리뷰/평점 분석은 단순화)
            product_info['시장반응도'] = "분석 중"
            product_info['고객만족도'] = "분석 중"
            product_info['브랜드내순위'] = "분석 중"
            
            our_product_details.append(product_info)
        
        return our_product_details
    
    def _analyze_price_competitiveness(self, df):
        """플랫폼별 가격 경쟁력 분석 (단순화 버전)"""
        if not all(col in df.columns for col in ['최저가 단위가격(100ml당)', '플랫폼']):
            return {}
        
        our_products = df[df['브랜드'] == self.our_brand]
        competitor_products = df[df['브랜드'] != self.our_brand]
        
        competitiveness = {}
        
        for platform in df['플랫폼'].unique():
            if pd.isna(platform):
                continue
            
            our_platform_data = our_products[our_products['플랫폼'] == platform]
            competitor_platform_data = competitor_products[competitor_products['플랫폼'] == platform]
            
            if our_platform_data.empty or competitor_platform_data.empty:
                continue
            
            platform_analysis = []
            
            for _, our_product in our_platform_data.iterrows():
                if pd.isna(our_product.get('최저가 단위가격(100ml당)')):
                    continue
                
                our_price = our_product['최저가 단위가격(100ml당)']
                competitor_prices = competitor_platform_data['최저가 단위가격(100ml당)'].dropna()
                
                if len(competitor_prices) == 0:
                    continue
                
                competitor_avg = competitor_prices.mean()
                competitor_min = competitor_prices.min()
                competitor_max = competitor_prices.max()
                
                price_gap = our_price - competitor_avg
                price_gap_percent = (price_gap / competitor_avg) * 100 if competitor_avg > 0 else 0
                
                # 시장 위치 판단
                if our_price <= competitor_min:
                    position = "🎯 최저가"
                elif our_price <= competitor_avg:
                    position = "📊 평균 이하"
                elif our_price <= competitor_max:
                    position = "📈 평균 이상"
                else:
                    position = "💰 최고가"
                
                platform_analysis.append({
                    '제품': f"{our_product.get('제품명', '')} {our_product.get('용량(ml)', 0)}ml {our_product.get('개수', 0)}개",
                    '우리_단위가격': f"{our_price:,.0f}원",
                    '경쟁사_평균': f"{competitor_avg:,.0f}원",
                    '경쟁사_최저': f"{competitor_min:,.0f}원",
                    '경쟁사_최고': f"{competitor_max:,.0f}원",
                    '가격차이': f"{price_gap:+,.0f}원",
                    '가격차이_퍼센트': f"{price_gap_percent:+.1f}%",
                    '시장_포지션': position,
                    '경쟁사_수': len(competitor_prices),
                    '비교_기준': "전체 시장",
                    '주요_경쟁사': ["분석 중"]
                })
            
            if platform_analysis:
                competitiveness[platform] = platform_analysis
        
        return competitiveness
    
    def _analyze_volume_market(self, df):
        """용량별/개수별 시장 현황 분석"""
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
            
            for _, combo in volume_count_combinations.head(10).iterrows():
                volume = combo['용량(ml)']
                count = combo['개수']
                total_products = combo['제품수']
                
                # 해당 조합에서 우리 제품 수
                our_products_in_combo = len(our_products[
                    (our_products['용량(ml)'] == volume) & 
                    (our_products['개수'] == count)
                ])
                
                combo_info = {
                    '용량_개수': f"{volume}ml {count}개",
                    '총_제품수': int(total_products),
                    '우리_제품수': int(our_products_in_combo),
                    '평균_단위가격': 'N/A',
                    '최저_단위가격': 'N/A',
                    '최고_단위가격': 'N/A'
                }
                
                volume_count_market.append(combo_info)
            
            return volume_count_market
            
        except Exception as e:
            return []
    
    def _analyze_market_share(self, df):
        """브랜드별 시장 점유율 분석"""
        try:
            unique_products = self._calculate_unique_products(df)
            brand_share = unique_products['브랜드'].value_counts()
            total_unique_products = len(unique_products)
            
            brand_share_percent = {}
            
            for brand, count in brand_share.head(10).items():
                if pd.notna(brand) and total_unique_products > 0:
                    percentage = (count / total_unique_products) * 100
                    brand_share_percent[brand] = {
                        '제품_수': int(count),
                        '점유율_퍼센트': round(percentage, 1)
                    }
            
            return brand_share_percent
            
        except Exception as e:
            return {}
