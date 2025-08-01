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

# Streamlit 설정
st.set_page_config(
    page_title="서로 수정과 - 시장 가격 분석",
    page_icon="🥤",
    layout="wide"
)

# GitHub 설정 (안전한 기본값 제공)
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "") if hasattr(st, 'secrets') else ""
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "coder4052/market_analysis") if hasattr(st, 'secrets') else "coder4052/market_analysis"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents"

class SujeonggwaMarketAnalyzer:
    def __init__(self):
        self.required_columns = [
            "브랜드", "제품명", "용량(ml)", "개수", 
            "일반 판매가", "일반 판매가 단위가격(100ml당)", 
            "상시 할인가", "상시 할인가 단위가격(100ml당)",
            "배송비", "최저가(배송비 포함)", "최저가 단위가격(100ml당)", 
            "공장형 여부", "리뷰 개수", "평점"  # 리뷰/평점 컬럼 추가
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
            
            if not available_columns:
                st.error(f"[{platform}] 필수 컬럼이 없습니다.")
                return None, None, None
            
            # 데이터 정제
            df_clean = df[available_columns].copy()
            df_clean['플랫폼'] = platform
            df_clean['분석_시간'] = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            # 숫자형 컬럼 변환 (안전하게 처리)
            numeric_columns = ['용량(ml)', '개수', '최저가(배송비 포함)', '최저가 단위가격(100ml당)', '공장형 여부']
            for col in numeric_columns:
                if col in df_clean.columns:
                    df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
            
            # NaN 값 제거
            df_clean = df_clean.dropna(subset=['브랜드', '제품명'])
            
            return df_clean, platform, missing_columns
            
        except Exception as e:
            st.error(f"파일 처리 중 오류: {str(e)}")
            return None, None, None
    
    def analyze_business_critical_data(self, df_list):
        """소상공인 관점의 핵심 비즈니스 분석"""
        if not df_list:
            return None, None, None
        
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
            'platforms_analyzed': combined_df['플랫폼'].unique().tolist() if '플랫폼' in combined_df.columns else []
        }
        
        return analysis_results, handmade_df, all_products_df
    
    def _analyze_category(self, df, category_name):
        """카테고리별 분석 (수제 또는 전체)"""
        
        # 리뷰/평점 컬럼 변수 미리 초기화
        review_col = None
        rating_col = None
        
        if df.empty:
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
        
        # 리뷰/평점 컬럼 찾기
        available_columns = list(df.columns)
        
        for col in ['리뷰 개수', '리뷰개수', 'review_count', '리뷰수']:
            if col in available_columns:
                review_col = col
                break
        
        for col in ['평점', '평균평점', 'rating', '별점']:
            if col in available_columns:
                rating_col = col
                break
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
        
        # 서로 브랜드 데이터 추출
        our_products = df[df['브랜드'] == self.our_brand].copy()
        competitor_products = df[df['브랜드'] != self.our_brand].copy()
        
        # 필수 컬럼 체크
        required_for_analysis = ['브랜드', '제품명', '용량(ml)', '개수']
        available_cols = [col for col in required_for_analysis if col in df.columns]
        
        if len(available_cols) < 2:
            st.warning(f"분석에 필요한 기본 컬럼이 부족합니다: {required_for_analysis}")
            return {
                'category_name': category_name,
                'total_products_analyzed': len(df),
                'total_unique_products': 0,
                'our_products_count': len(our_products),
                'our_unique_products_count': 0,
                'competitor_products_count': len(competitor_products),
                'competitor_unique_products_count': 0,
                'business_insights': {}
            }
        
        # 제품 그룹핑 (사용 가능한 컬럼만으로)
        group_cols = available_cols
        agg_dict = {}
        
        if '최저가(배송비 포함)' in df.columns:
            agg_dict['최저가(배송비 포함)'] = 'min'
        if '최저가 단위가격(100ml당)' in df.columns:
            agg_dict['최저가 단위가격(100ml당)'] = 'min'
        if '플랫폼' in df.columns:
            agg_dict['플랫폼'] = lambda x: list(x.unique())
        
        if not agg_dict:
            # 최소한의 그룹핑만 수행
            unique_products = df.groupby(group_cols).size().reset_index(name='count')
        else:
            unique_products = df.groupby(group_cols).agg(agg_dict).reset_index()
        
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
        
        # 1. 우리 브랜드 제품별 상세 현황 (고도화)
        if not our_unique_products.empty:
            our_product_details = []
            
            # 시장 평균 계산 (리뷰/평점)
            market_avg_reviews = 0
            market_avg_rating = 0
            
            if review_col and rating_col:
                market_reviews = competitor_products[competitor_products[review_col].notna() & (competitor_products[review_col] > 0)]
                market_ratings = competitor_products[competitor_products[rating_col].notna() & (competitor_products[rating_col] > 0)]
                
                if not market_reviews.empty:
                    market_avg_reviews = market_reviews[review_col].mean()
                if not market_ratings.empty:
                    market_avg_rating = market_ratings[rating_col].mean()
            
            # 우리 제품들의 성과 순위 계산 (리뷰수 × 평점 기준)
            our_products_performance = []
            
            for _, product in our_unique_products.iterrows():
                product_reviews = 0
                product_rating = 0
                
                # 해당 제품의 리뷰/평점 데이터 찾기
                matching_products = our_products[
                    (our_products['브랜드'] == product['브랜드']) & 
                    (our_products['제품명'] == product['제품명']) &
                    (our_products['용량(ml)'] == product['용량(ml)']) &
                    (our_products['개수'] == product['개수'])
                ]
                
                if not matching_products.empty and review_col and rating_col:
                    # 여러 플랫폼에서 판매되는 경우 최대값 사용
                    product_reviews = matching_products[review_col].max() if review_col in matching_products.columns else 0
                    product_rating = matching_products[rating_col].max() if rating_col in matching_products.columns else 0
                    
                    if pd.isna(product_reviews):
                        product_reviews = 0
                    if pd.isna(product_rating):
                        product_rating = 0
                
                # 성과 점수 계산 (리뷰수 × 평점)
                performance_score = product_reviews * product_rating if product_rating > 0 else 0
                
                our_products_performance.append({
                    'product_key': f"{product['제품명']}_{product['용량(ml)']}_{product['개수']}",
                    'reviews': product_reviews,
                    'rating': product_rating,
                    'performance_score': performance_score
                })
            
            # 성과 순위 정렬
            our_products_performance.sort(key=lambda x: x['performance_score'], reverse=True)
            
            for _, product in our_unique_products.iterrows():
                product_key = f"{product['제품명']}_{product['용량(ml)']}_{product['개수']}"
                
                # 기본 정보
                product_info = {
                    '브랜드': product.get('브랜드', ''),
                    '제품명': product.get('제품명', ''),
                    '용량': f"{product.get('용량(ml)', 0)}ml" if pd.notna(product.get('용량(ml)')) else 'N/A',
                    '개수': f"{product.get('개수', 0)}개" if pd.notna(product.get('개수')) else 'N/A'
                }
                
                # 가격 정보
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
                
                # 리뷰/평점 기반 확장 정보
                product_performance = next((p for p in our_products_performance if p['product_key'] == product_key), None)
                
                if product_performance and review_col and rating_col:
                    reviews = product_performance['reviews']
                    rating = product_performance['rating']
                    
                    # 시장 반응도
                    if market_avg_reviews > 0 and reviews > 0:
                        market_ratio = reviews / market_avg_reviews
                        if market_ratio >= 2.0:
                            reaction_status = f"🔥 {reviews:,.0f}개 (시장평균의 {market_ratio:.1f}배)"
                        elif market_ratio >= 1.0:
                            reaction_status = f"📈 {reviews:,.0f}개 (시장평균의 {market_ratio:.1f}배)"
                        else:
                            reaction_status = f"📊 {reviews:,.0f}개 (시장평균의 {market_ratio:.1f}배)"
                    else:
                        reaction_status = f"{reviews:,.0f}개" if reviews > 0 else "리뷰 없음"
                    
                    product_info['시장반응도'] = reaction_status
                    
                    # 고객 만족도
                    if rating > 0:
                        if rating >= 4.5:
                            satisfaction_status = f"⭐ {rating:.1f}점 (우수)"
                        elif rating >= 4.0:
                            satisfaction_status = f"⭐ {rating:.1f}점 (양호)"
                        else:
                            satisfaction_status = f"⚠️ {rating:.1f}점 (개선필요)"
                    else:
                        satisfaction_status = "평점 없음"
                    
                    product_info['고객만족도'] = satisfaction_status
                    
                    # 브랜드 내 순위
                    rank = next((i+1 for i, p in enumerate(our_products_performance) if p['product_key'] == product_key), None)
                    if rank and len(our_products_performance) > 1:
                        if rank == 1:
                            rank_status = f"🏆 1위/{len(our_products_performance)}개"
                        elif rank <= 3:
                            rank_status = f"🥉 {rank}위/{len(our_products_performance)}개"
                        else:
                            rank_status = f"📊 {rank}위/{len(our_products_performance)}개"
                        
                        product_info['브랜드내순위'] = rank_status
                    else:
                        product_info['브랜드내순위'] = "단일 제품"
                else:
                    # 리뷰/평점 데이터가 없는 경우
                    product_info['시장반응도'] = "데이터 없음"
                    product_info['고객만족도'] = "데이터 없음"
                    product_info['브랜드내순위'] = "데이터 없음"
                
                our_product_details.append(product_info)
            
            category_results['business_insights']['our_product_details'] = our_product_details
        
        # 2. 플랫폼별 가격 경쟁력 분석 (개선된 버전)
        if ('최저가 단위가격(100ml당)' in df.columns and 
            '플랫폼' in df.columns and 
            '용량(ml)' in df.columns and 
            '개수' in df.columns):
            
            competitiveness = {}
            for platform in df['플랫폼'].unique():
                if pd.isna(platform):
                    continue
                    
                platform_data = df[df['플랫폼'] == platform]
                our_platform_data = our_products[our_products['플랫폼'] == platform]
                competitor_platform_data = competitor_products[competitor_products['플랫폼'] == platform]
                
                if not our_platform_data.empty and not competitor_platform_data.empty:
                    our_product_competitiveness = []
                    
                    for _, our_product in our_platform_data.iterrows():
                        try:
                            our_volume = our_product.get('용량(ml)')
                            our_count = our_product.get('개수')
                            our_unit_price = our_product.get('최저가 단위가격(100ml당)')
                            
                            if pd.isna(our_volume) or pd.isna(our_count) or pd.isna(our_unit_price):
                                continue
                            
                            # 1단계: 정확히 같은 용량+개수 경쟁사 찾기
                            exact_competitors = competitor_platform_data[
                                (competitor_platform_data['용량(ml)'] == our_volume) & 
                                (competitor_platform_data['개수'] == our_count)
                            ]
                            
                            # 2단계: 정확한 매치가 없으면 유사 용량대 찾기 (±20% 범위)
                            volume_range_min = our_volume * 0.8
                            volume_range_max = our_volume * 1.2
                            similar_volume_competitors = competitor_platform_data[
                                (competitor_platform_data['용량(ml)'] >= volume_range_min) & 
                                (competitor_platform_data['용량(ml)'] <= volume_range_max) &
                                (competitor_platform_data['개수'] == our_count)
                            ]
                            
                            # 3단계: 용량은 다르지만 같은 개수의 경쟁사 찾기
                            same_count_competitors = competitor_platform_data[
                                competitor_platform_data['개수'] == our_count
                            ]
                            
                            # 4단계: 전체 경쟁사와 비교 (단위가격 기준)
                            all_competitors = competitor_platform_data.copy()
                            
                            # 가장 적절한 비교군 선택
                            selected_competitors = None
                            comparison_type = ""
                            
                            if not exact_competitors.empty:
                                selected_competitors = exact_competitors
                                comparison_type = "동일 용량+개수"
                            elif not similar_volume_competitors.empty:
                                selected_competitors = similar_volume_competitors
                                comparison_type = f"유사 용량({volume_range_min:.0f}~{volume_range_max:.0f}ml)+동일개수"
                            elif not same_count_competitors.empty:
                                selected_competitors = same_count_competitors
                                comparison_type = "동일 개수"
                            elif not all_competitors.empty:
                                selected_competitors = all_competitors
                                comparison_type = "전체 시장"
                            
                            if selected_competitors is not None and not selected_competitors.empty:
                                competitor_unit_prices = selected_competitors['최저가 단위가격(100ml당)'].dropna()
                                
                                if len(competitor_unit_prices) > 0:
                                    competitor_avg = competitor_unit_prices.mean()
                                    competitor_min = competitor_unit_prices.min()
                                    competitor_max = competitor_unit_prices.max()
                                    
                                    price_gap = our_unit_price - competitor_avg
                                    price_gap_percent = (price_gap / competitor_avg) * 100 if competitor_avg > 0 else 0
                                    
                                    # 시장 위치 판단
                                    if our_unit_price <= competitor_min:
                                        market_position = "최저가"
                                        position_color = "🎯"
                                    elif our_unit_price <= competitor_avg:
                                        market_position = "평균 이하"
                                        position_color = "📊"
                                    elif our_unit_price <= competitor_max:
                                        market_position = "평균 이상"
                                        position_color = "📈"
                                    else:
                                        market_position = "최고가"
                                        position_color = "💰"
                                    
                                    # 경쟁사 세부 정보 추가
                                    competitor_details = []
                                    for _, comp in selected_competitors.head(3).iterrows():
                                        comp_volume = comp.get('용량(ml)', 'N/A')
                                        comp_count = comp.get('개수', 'N/A')
                                        comp_price = comp.get('최저가 단위가격(100ml당)', 'N/A')
                                        comp_brand = comp.get('브랜드', 'N/A')
                                        competitor_details.append(f"{comp_brand} {comp_volume}ml×{comp_count}개 ({comp_price:,.0f}원/100ml)")
                                    
                                    product_comp = {
                                        '제품': f"{our_product.get('제품명', '')} {our_volume}ml {our_count}개",
                                        '우리_단위가격': f"{our_unit_price:,.0f}원",
                                        '경쟁사_평균': f"{competitor_avg:,.0f}원",
                                        '경쟁사_최저': f"{competitor_min:,.0f}원",
                                        '경쟁사_최고': f"{competitor_max:,.0f}원",
                                        '가격차이': f"{price_gap:+,.0f}원",
                                        '가격차이_퍼센트': f"{price_gap_percent:+.1f}%",
                                        '시장_포지션': f"{position_color} {market_position}",
                                        '경쟁사_수': len(selected_competitors),
                                        '비교_기준': comparison_type,
                                        '주요_경쟁사': competitor_details[:3]
                                    }
                                    our_product_competitiveness.append(product_comp)
                        except Exception as e:
                            continue  # 개별 제품 오류는 건너뛰기
                    
                    if our_product_competitiveness:
                        competitiveness[platform] = our_product_competitiveness
            
            category_results['business_insights']['detailed_competitiveness'] = competitiveness
        
        # 3. 용량별/개수별 시장 현황
        if '용량(ml)' in df.columns and '개수' in df.columns:
            try:
                # NaN 값 제거
                df_for_volume = df.dropna(subset=['용량(ml)', '개수'])
                
                if not df_for_volume.empty:
                    volume_count_combinations = df_for_volume.groupby(['용량(ml)', '개수']).size().reset_index(name='제품수')
                    volume_count_combinations = volume_count_combinations.sort_values('제품수', ascending=False)
                    
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
                        
                        # 해당 조합에서 가격 분포
                        combo_products = df_for_volume[
                            (df_for_volume['용량(ml)'] == volume) & 
                            (df_for_volume['개수'] == count)
                        ]
                        
                        combo_info = {
                            '용량_개수': f"{volume}ml {count}개",
                            '총_제품수': int(total_products),
                            '우리_제품수': int(our_products_in_combo)
                        }
                        
                        if ('최저가 단위가격(100ml당)' in combo_products.columns and 
                            not combo_products['최저가 단위가격(100ml당)'].isna().all()):
                            
                            unit_prices = combo_products['최저가 단위가격(100ml당)'].dropna()
                            if len(unit_prices) > 0:
                                avg_unit_price = unit_prices.mean()
                                min_unit_price = unit_prices.min()
                                max_unit_price = unit_prices.max()
                                
                                combo_info.update({
                                    '평균_단위가격': f"{avg_unit_price:,.0f}원",
                                    '최저_단위가격': f"{min_unit_price:,.0f}원",
                                    '최고_단위가격': f"{max_unit_price:,.0f}원"
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
                        
                        volume_count_market.append(combo_info)
                    
                    category_results['business_insights']['volume_count_market'] = volume_count_market
            except Exception as e:
                st.warning(f"용량별 시장 분석 중 오류: {str(e)}")
        
        # 4. 브랜드별 시장 점유율 (고도화된 다차원 분석)
        try:
            # 기존 제품 수 기준 점유율
            brand_share = unique_products['브랜드'].value_counts()
            total_unique_products = len(unique_products)
            
            # 리뷰/평점 데이터 준비 및 정제
            df_with_reviews = df.copy()
            
            # 리뷰 개수와 평점 컬럼 확인 및 정제 (디버깅 로그 추가)
            review_col = None
            rating_col = None
            
            # 실제 컬럼명 확인 (디버깅용)
            available_columns = list(df_with_reviews.columns)
            
            for col in ['리뷰 개수', '리뷰개수', 'review_count', '리뷰수']:
                if col in available_columns:
                    review_col = col
                    break
            
            for col in ['평점', '평균평점', 'rating', '별점']:
                if col in available_columns:
                    rating_col = col
                    break
            
            # 디버깅 정보 (실제 운영에서는 제거 가능)
            if not review_col or not rating_col:
                st.info(f"🔍 디버깅 정보: 사용 가능한 컬럼들: {available_columns}")
                st.info(f"🔍 찾은 리뷰 컬럼: {review_col}, 찾은 평점 컬럼: {rating_col}")
            
            # 데이터 정제
            if review_col and review_col in df_with_reviews.columns:
                df_with_reviews[review_col] = pd.to_numeric(df_with_reviews[review_col], errors='coerce').fillna(0)
            if rating_col and rating_col in df_with_reviews.columns:
                df_with_reviews[rating_col] = pd.to_numeric(df_with_reviews[rating_col], errors='coerce').fillna(0)
            
            # 브랜드별 종합 분석
            brand_analysis = {}
            
            for brand in df_with_reviews['브랜드'].unique():
                if pd.isna(brand) or brand == '브랜드':  # 헤더 제외
                    continue
                
                brand_data = df_with_reviews[df_with_reviews['브랜드'] == brand]
                brand_unique = unique_products[unique_products['브랜드'] == brand]
                
                analysis = {
                    '제품_수': len(brand_unique),
                    '제품_수_점유율': (len(brand_unique) / total_unique_products) * 100 if total_unique_products > 0 else 0
                }
                
                # 리뷰 기반 분석 (리뷰 개수 컬럼이 있는 경우)
                if review_col and not brand_data[review_col].isna().all():
                    total_reviews = brand_data[review_col].sum()
                    avg_reviews_per_product = brand_data[review_col].mean()
                    
                    analysis.update({
                        '총_리뷰수': int(total_reviews),
                        '제품당_평균_리뷰수': round(avg_reviews_per_product, 1),
                        '리뷰_기반_인지도': total_reviews  # 나중에 전체 대비 비율로 변환
                    })
                
                # 평점 기반 분석 (평점 컬럼이 있는 경우)
                if rating_col and not brand_data[rating_col].isna().all():
                    # 평점이 0이 아닌 제품들만으로 평균 계산
                    valid_ratings = brand_data[brand_data[rating_col] > 0][rating_col]
                    
                    if len(valid_ratings) > 0:
                        avg_rating = valid_ratings.mean()
                        rating_count = len(valid_ratings)  # 평점 있는 제품 수
                        
                        analysis.update({
                            '평균_평점': round(avg_rating, 2),
                            '평점_있는_제품수': rating_count,
                            '평점_커버리지': round((rating_count / len(brand_data)) * 100, 1)  # 평점 있는 제품 비율
                        })
                
                # 시장 영향력 점수 계산 (리뷰와 평점이 모두 있는 경우)
                if review_col and rating_col:
                    # 각 제품별로 (리뷰수 × 평점) 계산 후 합산
                    brand_data_clean = brand_data.copy()
                    brand_data_clean = brand_data_clean[
                        (brand_data_clean[review_col].notna()) & 
                        (brand_data_clean[rating_col].notna()) &
                        (brand_data_clean[rating_col] > 0)
                    ]
                    
                    if not brand_data_clean.empty:
                        # 영향력 점수 = Σ(리뷰수 × 평점)
                        impact_scores = brand_data_clean[review_col] * brand_data_clean[rating_col]
                        total_impact = impact_scores.sum()
                        
                        analysis['시장_영향력_점수'] = round(total_impact, 1)
                
                brand_analysis[brand] = analysis
            
            # 전체 시장 대비 비율 계산
            if review_col:
                total_market_reviews = sum([data.get('총_리뷰수', 0) for data in brand_analysis.values()])
                for brand, data in brand_analysis.items():
                    if '총_리뷰수' in data and total_market_reviews > 0:
                        data['리뷰_점유율'] = round((data['총_리뷰수'] / total_market_reviews) * 100, 1)
            
            if review_col and rating_col:
                total_market_impact = sum([data.get('시장_영향력_점수', 0) for data in brand_analysis.values()])
                for brand, data in brand_analysis.items():
                    if '시장_영향력_점수' in data and total_market_impact > 0:
                        data['영향력_점유율'] = round((data['시장_영향력_점수'] / total_market_impact) * 100, 1)
            
            # 상위 10개 브랜드만 선택 (제품 수 기준)
            top_brands = sorted(brand_analysis.items(), key=lambda x: x[1]['제품_수'], reverse=True)[:10]
            
            # 최종 결과 구성 + 플랫폼별 분석 추가
            enhanced_market_share = {}
            for brand, data in top_brands:
                enhanced_market_share[brand] = data
            
            # 플랫폼별 브랜드 분석 (다차원 고도화)
            platform_analysis = {}
            
            if '플랫폼' in df.columns:
                platforms = df['플랫폼'].unique()
                
                for platform in platforms:
                    if pd.isna(platform):
                        continue
                    
                    # 해당 플랫폼 데이터만 추출
                    platform_data = df[df['플랫폼'] == platform].copy()
                    platform_unique = unique_products[unique_products['플랫폼'].apply(
                        lambda x: platform in x if isinstance(x, list) else x == platform
                    )]
                    
                    if platform_unique.empty:
                        continue
                    
                    # 플랫폼 내 브랜드별 종합 분석
                    platform_brand_analysis = {}
                    
                    for brand in platform_data['브랜드'].unique():
                        if pd.isna(brand) or brand == '브랜드':
                            continue
                        
                        brand_platform_data = platform_data[platform_data['브랜드'] == brand]
                        brand_unique_data = platform_unique[platform_unique['브랜드'] == brand]
                        
                        analysis = {
                            '제품_수': len(brand_unique_data)
                        }
                        
                        # 리뷰 기반 분석
                        if review_col and review_col in brand_platform_data.columns:
                            total_reviews = brand_platform_data[review_col].sum()
                            valid_reviews = brand_platform_data[brand_platform_data[review_col] > 0]
                            avg_reviews = valid_reviews[review_col].mean() if not valid_reviews.empty else 0
                            
                            analysis.update({
                                '총_리뷰수': int(total_reviews) if not pd.isna(total_reviews) else 0,
                                '평균_리뷰수': round(avg_reviews, 1) if not pd.isna(avg_reviews) else 0
                            })
                        
                        # 평점 기반 분석  
                        if rating_col and rating_col in brand_platform_data.columns:
                            valid_ratings = brand_platform_data[brand_platform_data[rating_col] > 0]
                            avg_rating = valid_ratings[rating_col].mean() if not valid_ratings.empty else 0
                            
                            analysis.update({
                                '평균_평점': round(avg_rating, 2) if not pd.isna(avg_rating) else 0,
                                '평점_제품수': len(valid_ratings)
                            })
                        
                        # 종합 영향력 점수 (리뷰 × 평점)
                        if review_col and rating_col:
                            impact_scores = []
                            for _, product in brand_platform_data.iterrows():
                                reviews = product.get(review_col, 0) if not pd.isna(product.get(review_col, 0)) else 0
                                rating = product.get(rating_col, 0) if not pd.isna(product.get(rating_col, 0)) else 0
                                if reviews > 0 and rating > 0:
                                    impact_scores.append(reviews * rating)
                            
                            total_impact = sum(impact_scores) if impact_scores else 0
                            analysis['종합_영향력'] = round(total_impact, 1)
                        
                        platform_brand_analysis[brand] = analysis
                    
                    # 플랫폼별 순위 계산
                    platform_rankings = {
                        '제품수_순위': {},
                        '리뷰수_순위': {},
                        '평점_순위': {},
                        '영향력_순위': {}
                    }
                    
                    # 제품 수 순위
                    product_ranking = sorted(platform_brand_analysis.items(), 
                                           key=lambda x: x[1]['제품_수'], reverse=True)
                    for rank, (brand, _) in enumerate(product_ranking, 1):
                        platform_rankings['제품수_순위'][brand] = rank
                    
                    # 리뷰 수 순위  
                    if review_col:
                        review_ranking = sorted(platform_brand_analysis.items(),
                                              key=lambda x: x[1].get('총_리뷰수', 0), reverse=True)
                        for rank, (brand, _) in enumerate(review_ranking, 1):
                            if platform_brand_analysis[brand].get('총_리뷰수', 0) > 0:
                                platform_rankings['리뷰수_순위'][brand] = rank
                    
                    # 평점 순위
                    if rating_col:
                        rating_ranking = sorted(platform_brand_analysis.items(),
                                              key=lambda x: x[1].get('평균_평점', 0), reverse=True)
                        for rank, (brand, _) in enumerate(rating_ranking, 1):
                            if platform_brand_analysis[brand].get('평균_평점', 0) > 0:
                                platform_rankings['평점_순위'][brand] = rank
                    
                    # 종합 영향력 순위
                    if review_col and rating_col:
                        impact_ranking = sorted(platform_brand_analysis.items(),
                                              key=lambda x: x[1].get('종합_영향력', 0), reverse=True)
                        for rank, (brand, _) in enumerate(impact_ranking, 1):
                            if platform_brand_analysis[brand].get('종합_영향력', 0) > 0:
                                platform_rankings['영향력_순위'][brand] = rank
                    
                    # 서로 브랜드 종합 분석
                    seoro_analysis = {}
                    if "서로" in platform_brand_analysis:
                        seoro_data = platform_brand_analysis["서로"]
                        
                        seoro_analysis = {
                            '제품수_순위': platform_rankings['제품수_순위'].get("서로", None),
                            '리뷰수_순위': platform_rankings['리뷰수_순위'].get("서로", None),
                            '평점_순위': platform_rankings['평점_순위'].get("서로", None),
                            '영향력_순위': platform_rankings['영향력_순위'].get("서로", None),
                            '제품수': seoro_data.get('제품_수', 0),
                            '총_리뷰수': seoro_data.get('총_리뷰수', 0),
                            '평균_평점': seoro_data.get('평균_평점', 0),
                            '종합_영향력': seoro_data.get('종합_영향력', 0)
                        }
                        
                        # 플랫폼별 전략 제안 (다차원 고려)
                        product_rank = seoro_analysis['제품수_순위']
                        review_rank = seoro_analysis['리뷰수_순위'] 
                        rating_rank = seoro_analysis['평점_순위']
                        impact_rank = seoro_analysis['영향력_순위']
                        
                        # 종합 점수 계산 (순위가 낮을수록 좋음)
                        ranks = [r for r in [product_rank, review_rank, rating_rank, impact_rank] if r is not None]
                        avg_rank = sum(ranks) / len(ranks) if ranks else None
                        
                        strategy = ""
                        if avg_rank:
                            if avg_rank <= 2:
                                if product_rank == 1 and review_rank and review_rank <= 2:
                                    strategy = "🏆 종합 리더 - 시장 지배력 유지 및 확장"
                                elif rating_rank == 1:
                                    strategy = "⭐ 품질 리더 - 프리미엄 포지셔닝 강화"
                                else:
                                    strategy = "🥉 강자 - 약점 보완으로 1위 도전"
                            elif avg_rank <= 4:
                                if review_rank and review_rank > 5:
                                    strategy = "📈 도전자 - 마케팅 집중으로 인지도 확대"
                                elif rating_rank and rating_rank > 5:
                                    strategy = "🔧 개선 필요 - 품질 향상 우선"
                                else:
                                    strategy = "📊 중위권 - 차별화 전략 필요"
                            else:
                                strategy = "🚀 신규/도전 - 집중 공략으로 점유율 확대"
                        else:
                            strategy = "🆕 신규 진입 - 틈새 시장 기회 탐색"
                        
                        seoro_analysis['전략_제안'] = strategy
                    
                    platform_analysis[platform] = {
                        '브랜드_분석': platform_brand_analysis,
                        '순위_정보': platform_rankings,
                        '서로_분석': seoro_analysis,
                        '총_브랜드수': len(platform_brand_analysis),
                        '총_제품수': len(platform_unique)
                    }
            
            category_results['business_insights']['enhanced_market_share'] = enhanced_market_share
            category_results['business_insights']['platform_analysis'] = platform_analysis  # 고도화된 분석
            category_results['business_insights']['market_analysis_metadata'] = {
                'has_review_data': review_col is not None,
                'has_rating_data': rating_col is not None,
                'review_column': review_col,
                'rating_column': rating_col,
                'total_brands_analyzed': len(brand_analysis)
            }
            
            # 기존 market_share도 유지 (하위 호환성)
            brand_share_percent = {}
            for brand, count in brand_share.head(10).items():
                if pd.notna(brand) and total_unique_products > 0:
                    percentage = (count / total_unique_products) * 100
                    brand_share_percent[brand] = {
                        '제품_수': int(count),
                        '점유율_퍼센트': round(percentage, 1)
                    }
            
            category_results['business_insights']['market_share'] = brand_share_percent
            
        except Exception as e:
            st.warning(f"브랜드별 점유율 분석 중 오류: {str(e)}")
            # 기존 분석 결과라도 제공
            try:
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
                
                category_results['business_insights']['market_share'] = brand_share_percent
            except:
                pass
        
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
    
    # 안전성 체크
    if not analysis_results:
        st.error("분석 결과가 없습니다.")
        return
    
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
        st.metric("🥤 서로 브랜드", f"{our_count}개")
    
    with col4:
        competitor_count = category_data.get('competitor_unique_products_count', 0)
        st.metric("🏭 경쟁사 제품", f"{competitor_count}개")
    
    st.markdown("---")
    
    # 통합된 우리 제품 현황 (단일 탭)
    st.subheader(f"🥤 서로 브랜드 종합 현황 ({category_type})")
    
    business_insights = category_data.get('business_insights', {})
    
    # 1. 제품별 상세 현황
    st.markdown("### 📊 제품별 상세 현황")
    if 'our_product_details' in business_insights:
        product_details = business_insights['our_product_details']
        
        if product_details:
            # 제품 현황 테이블
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
                            
                            # 시장 포지션 색상 표시 (이미 이모지 포함됨)
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
                for market in untapped_markets[:5]:  # 상위 5개만 표시
                    volume_count = market.get('용량_개수', 'N/A')
                    total_products = market.get('총_제품수', 0)
                    avg_price = market.get('평균_단위가격', 'N/A')
                    st.info(f"**{volume_count}**: {total_products}개 제품, 평균 단위가격 {avg_price}")
        else:
            st.warning("용량별 시장 데이터가 없습니다.")
    else:
        st.info("용량별 시장 분석 데이터가 없습니다.")
    
    st.markdown("---")
    
    # 4. 브랜드별 시장 점유율 (고도화된 분석)
    st.markdown("### 🏆 브랜드별 시장 분석")
    
    if 'enhanced_market_share' in business_insights:
        enhanced_data = business_insights['enhanced_market_share']
        metadata = business_insights.get('market_analysis_metadata', {})
        
        if enhanced_data:
            # 분석 개요
            has_review = metadata.get('has_review_data', False)
            has_rating = metadata.get('has_rating_data', False)
            
            if has_review and has_rating:
                st.success("📊 **종합 분석**: 제품 수 + 리뷰 + 평점 데이터 모두 활용")
            elif has_review or has_rating:
                st.info(f"📊 **부분 분석**: 제품 수 + {'리뷰' if has_review else '평점'} 데이터 활용")
            else:
                st.warning("📊 **기본 분석**: 제품 수만 활용 (리뷰/평점 데이터 없음)")
            
            analysis_tabs = []
            tab_names = ["📊 전체 시장 통합"]
            
            if has_review:
                tab_names.append("👥 리뷰 기반 인지도")
            if has_rating:
                tab_names.append("⭐ 평점 기준 품질")
            if has_review and has_rating:
                tab_names.append("🚀 종합 영향력")
            
            # 플랫폼별 분석 탭 추가
            if 'platform_analysis' in business_insights:
                tab_names.append("🏪 플랫폼별 분석")
            
            analysis_tabs = st.tabs(tab_names)
            
            with analysis_tabs[0]:  # 전체 시장 통합 (기존)
                st.markdown("#### 📊 제품 수 기준 시장 점유율")
                
                product_share_df = pd.DataFrame([
                    {
                        '브랜드': brand, 
                        '제품 수': data.get('제품_수', 0),
                        '점유율(%)': f"{data.get('제품_수_점유율', 0):.1f}%"
                    }
                    for brand, data in enhanced_data.items()
                ])
                
                st.dataframe(product_share_df, use_container_width=True)
                
                # 서로 브랜드 순위
                seoro_rank = None
                for idx, (brand, _) in enumerate(enhanced_data.items(), 1):
                    if brand == "서로":
                        seoro_rank = idx
                        break
                
                if seoro_rank:
                    if seoro_rank == 1:
                        st.success(f"🏆 서로 브랜드가 제품 수 기준 **{seoro_rank}위**입니다!")
                    elif seoro_rank <= 3:
                        st.info(f"🥉 서로 브랜드가 제품 수 기준 **{seoro_rank}위**입니다.")
                    else:
                        st.warning(f"📈 서로 브랜드가 제품 수 기준 **{seoro_rank}위**입니다.")
            
            # 리뷰 기반 분석 탭
            if has_review and len(analysis_tabs) > 1:
                with analysis_tabs[1]:
                    st.markdown("#### 👥 리뷰 기반 시장 인지도")
                    
                    review_data = []
                    for brand, data in enhanced_data.items():
                        if '총_리뷰수' in data:
                            review_data.append({
                                '브랜드': brand,
                                '총 리뷰 수': f"{data.get('총_리뷰수', 0):,}개",
                                '제품당 평균 리뷰': f"{data.get('제품당_평균_리뷰수', 0):.1f}개",
                                '리뷰 점유율(%)': f"{data.get('리뷰_점유율', 0):.1f}%"
                            })
                    
                    if review_data:
                        review_df = pd.DataFrame(review_data)
                        st.dataframe(review_df, use_container_width=True)
                        
                        st.info("💡 **리뷰 기반 인지도**: 실제 구매 고객의 참여도를 반영한 지표")
                    else:
                        st.warning("리뷰 데이터가 충분하지 않습니다.")
            
            # 평점 기반 분석 탭
            if has_rating:
                rating_tab_idx = 1 if not has_review else 2
                if len(analysis_tabs) > rating_tab_idx:
                    with analysis_tabs[rating_tab_idx]:
                        st.markdown("#### ⭐ 평점 기준 품질 순위")
                        
                        rating_data = []
                        for brand, data in enhanced_data.items():
                            if '평균_평점' in data:
                                rating_data.append({
                                    '브랜드': brand,
                                    '평균 평점': f"{data.get('평균_평점', 0):.2f}점",
                                    '평점 있는 제품 수': f"{data.get('평점_있는_제품수', 0)}개",
                                    '평점 커버리지': f"{data.get('평점_커버리지', 0):.1f}%"
                                })
                        
                        if rating_data:
                            # 평점 순으로 정렬
                            rating_data.sort(key=lambda x: float(x['평균 평점'].replace('점', '')), reverse=True)
                            rating_df = pd.DataFrame(rating_data)
                            st.dataframe(rating_df, use_container_width=True)
                            
                            # 서로 브랜드 평점 순위
                            seoro_rating_rank = None
                            for idx, item in enumerate(rating_data, 1):
                                if item['브랜드'] == "서로":
                                    seoro_rating_rank = idx
                                    seoro_rating = float(item['평균 평점'].replace('점', ''))
                                    break
                            
                            if seoro_rating_rank:
                                if seoro_rating >= 4.5:
                                    st.success(f"⭐ 서로 브랜드 평점: **{seoro_rating:.2f}점** ({seoro_rating_rank}위) - 우수한 품질!")
                                elif seoro_rating >= 4.0:
                                    st.info(f"⭐ 서로 브랜드 평점: **{seoro_rating:.2f}점** ({seoro_rating_rank}위) - 양호한 품질")
                                else:
                                    st.warning(f"⭐ 서로 브랜드 평점: **{seoro_rating:.2f}점** ({seoro_rating_rank}위) - 품질 개선 필요")
                            
                            st.info("💡 **품질 지표**: 실제 구매 고객의 만족도를 반영한 지표")
                        else:
                            st.warning("평점 데이터가 충분하지 않습니다.")
            
            # 종합 영향력 분석 탭
            if has_review and has_rating:
                impact_tab_idx = 3
                if len(analysis_tabs) > impact_tab_idx:
                    with analysis_tabs[impact_tab_idx]:
                        st.markdown("#### 🚀 종합 시장 영향력")
                        
                        impact_data = []
                        for brand, data in enhanced_data.items():
                            if '시장_영향력_점수' in data:
                                impact_data.append({
                                    '브랜드': brand,
                                    '영향력 점수': f"{data.get('시장_영향력_점수', 0):,.1f}",
                                    '영향력 점유율(%)': f"{data.get('영향력_점유율', 0):.1f}%",
                                    '제품 수': f"{data.get('제품_수', 0)}개",
                                    '총 리뷰': f"{data.get('총_리뷰수', 0):,}개",
                                    '평균 평점': f"{data.get('평균_평점', 0):.2f}점"
                                })
                        
                        if impact_data:
                            # 영향력 점수 순으로 정렬
                            impact_data.sort(key=lambda x: float(x['영향력 점수'].replace(',', '')), reverse=True)
                            impact_df = pd.DataFrame(impact_data)
                            st.dataframe(impact_df, use_container_width=True)
                            
                            # 서로 브랜드 영향력 순위
                            seoro_impact_rank = None
                            for idx, item in enumerate(impact_data, 1):
                                if item['브랜드'] == "서로":
                                    seoro_impact_rank = idx
                                    seoro_impact_share = float(item['영향력 점유율(%)'].replace('%', ''))
                                    break
                            
                            if seoro_impact_rank:
                                if seoro_impact_rank == 1:
                                    st.success(f"🚀 서로 브랜드가 종합 영향력 **1위**! (점유율: {seoro_impact_share:.1f}%)")
                                elif seoro_impact_rank <= 3:
                                    st.info(f"🚀 서로 브랜드 종합 영향력 **{seoro_impact_rank}위** (점유율: {seoro_impact_share:.1f}%)")
                                else:
                                    st.warning(f"🚀 서로 브랜드 종합 영향력 **{seoro_impact_rank}위** (점유율: {seoro_impact_share:.1f}%)")
                            
                            st.info("💡 **종합 영향력**: 리뷰 수 × 평점을 고려한 실제 시장 영향력 지표")
                        else:
                            st.warning("종합 영향력 계산에 필요한 데이터가 부족합니다.")
            
            # 플랫폼별 분석 탭 (고도화된 다차원 분석)
            if 'platform_analysis' in business_insights and len(analysis_tabs) > (4 if has_review and has_rating else 3 if has_review or has_rating else 1):
                platform_tab_idx = len(analysis_tabs) - 1
                with analysis_tabs[platform_tab_idx]:
                    st.markdown("#### 🏪 플랫폼별 다차원 브랜드 분석")
                    
                    platform_data = business_insights['platform_analysis']
                    
                    if platform_data:
                        # 서로 브랜드 플랫폼별 종합 현황
                        st.markdown("##### 🎯 서로 브랜드 플랫폼별 종합 현황")
                        
                        summary_data = []
                        for platform, data in platform_data.items():
                            seoro_info = data.get('서로_분석', {})
                            
                            if seoro_info:
                                # 각 순위 정보 추출
                                product_rank = seoro_info.get('제품수_순위', '-')
                                review_rank = seoro_info.get('리뷰수_순위', '-')
                                rating_rank = seoro_info.get('평점_순위', '-')
                                impact_rank = seoro_info.get('영향력_순위', '-')
                                
                                # 종합 성과 계산 (순위가 있는 것들의 평균)
                                ranks = [r for r in [product_rank, review_rank, rating_rank, impact_rank] if isinstance(r, int)]
                                avg_rank = round(sum(ranks) / len(ranks), 1) if ranks else None
                                
                                # 플랫폼 상태 이모지
                                if avg_rank and avg_rank <= 2:
                                    platform_emoji = "🏆"
                                elif avg_rank and avg_rank <= 4:
                                    platform_emoji = "🥉"
                                else:
                                    platform_emoji = "📈"
                                
                                summary_data.append({
                                    '플랫폼': f"{platform_emoji} {platform}",
                                    '제품수 순위': f"{product_rank}위" if isinstance(product_rank, int) else '-',
                                    '리뷰수 순위': f"{review_rank}위" if isinstance(review_rank, int) else '-',
                                    '평점 순위': f"{rating_rank}위" if isinstance(rating_rank, int) else '-',
                                    '종합 영향력': f"{impact_rank}위" if isinstance(impact_rank, int) else '-',
                                    '종합 평가': f"{avg_rank}위" if avg_rank else "데이터 부족"
                                })
                            else:
                                summary_data.append({
                                    '플랫폼': f"📊 {platform}",
                                    '제품수 순위': '순위권 밖',
                                    '리뷰수 순위': '-',
                                    '평점 순위': '-', 
                                    '종합 영향력': '-',
                                    '종합 평가': '진출 필요'
                                })
                        
                        summary_df = pd.DataFrame(summary_data)
                        st.dataframe(summary_df, use_container_width=True)
                        
                        # 플랫폼별 상세 분석
                        st.markdown("##### 📊 플랫폼별 상세 분석")
                        
                        for platform, data in platform_data.items():
                            seoro_info = data.get('서로_분석', {})
                            
                            with st.expander(f"🏪 {platform} 다차원 분석"):
                                
                                if seoro_info:
                                    # 전략 제안
                                    strategy = seoro_info.get('전략_제안', '')
                                    if strategy:
                                        if "🏆" in strategy or "리더" in strategy:
                                            st.success(f"**전략**: {strategy}")
                                        elif "🥉" in strategy or "강자" in strategy:
                                            st.info(f"**전략**: {strategy}")
                                        elif "📈" in strategy or "도전" in strategy:
                                            st.warning(f"**전략**: {strategy}")
                                        else:
                                            st.error(f"**전략**: {strategy}")
                                    
                                    # 서로 브랜드 세부 성과
                                    col1, col2, col3, col4 = st.columns(4)
                                    
                                    with col1:
                                        product_rank = seoro_info.get('제품수_순위', '-')
                                        product_count = seoro_info.get('제품수', 0)
                                        if isinstance(product_rank, int):
                                            st.metric("제품 수 순위", f"{product_rank}위", f"{product_count}개 제품")
                                        else:
                                            st.metric("제품 수 순위", "순위권 밖", f"{product_count}개 제품")
                                    
                                    with col2:
                                        review_rank = seoro_info.get('리뷰수_순위', '-')
                                        total_reviews = seoro_info.get('총_리뷰수', 0)
                                        if isinstance(review_rank, int) and total_reviews > 0:
                                            st.metric("리뷰 수 순위", f"{review_rank}위", f"{total_reviews:,}개 리뷰")
                                        else:
                                            st.metric("리뷰 수 순위", "데이터 없음", f"{total_reviews:,}개 리뷰")
                                    
                                    with col3:
                                        rating_rank = seoro_info.get('평점_순위', '-')
                                        avg_rating = seoro_info.get('평균_평점', 0)
                                        if isinstance(rating_rank, int) and avg_rating > 0:
                                            st.metric("평점 순위", f"{rating_rank}위", f"{avg_rating:.2f}점")
                                        else:
                                            st.metric("평점 순위", "데이터 없음", f"{avg_rating:.2f}점")
                                    
                                    with col4:
                                        impact_rank = seoro_info.get('영향력_순위', '-')
                                        impact_score = seoro_info.get('종합_영향력', 0)
                                        if isinstance(impact_rank, int) and impact_score > 0:
                                            st.metric("종합 영향력", f"{impact_rank}위", f"{impact_score:,.1f}점")
                                        else:
                                            st.metric("종합 영향력", "데이터 없음", f"{impact_score:,.1f}점")
                                    
                                    # 플랫폼 내 상위 브랜드 (각 지표별)
                                    st.markdown("**📊 플랫폼 내 주요 경쟁사 현황:**")
                                    
                                    # 탭으로 각 지표별 순위 표시
                                    rank_tabs = st.tabs(["제품 수", "리뷰 수", "평점", "종합 영향력"])
                                    
                                    brand_analysis = data.get('브랜드_분석', {})
                                    rankings = data.get('순위_정보', {})
                                    
                                    with rank_tabs[0]:  # 제품 수
                                        product_ranking = sorted(brand_analysis.items(), 
                                                               key=lambda x: x[1].get('제품_수', 0), reverse=True)[:5]
                                        product_data = []
                                        for rank, (brand, info) in enumerate(product_ranking, 1):
                                            brand_display = f"🎯 {brand}" if brand == "서로" else brand
                                            product_data.append({
                                                '순위': f"{rank}위",
                                                '브랜드': brand_display,
                                                '제품 수': f"{info.get('제품_수', 0)}개"
                                            })
                                        if product_data:
                                            st.dataframe(pd.DataFrame(product_data), use_container_width=True)
                                    
                                    with rank_tabs[1]:  # 리뷰 수
                                        if review_col:
                                            review_ranking = sorted(brand_analysis.items(),
                                                                  key=lambda x: x[1].get('총_리뷰수', 0), reverse=True)[:5]
                                            review_data = []
                                            for rank, (brand, info) in enumerate(review_ranking, 1):
                                                if info.get('총_리뷰수', 0) > 0:
                                                    brand_display = f"🎯 {brand}" if brand == "서로" else brand
                                                    review_data.append({
                                                        '순위': f"{rank}위",
                                                        '브랜드': brand_display,
                                                        '총 리뷰 수': f"{info.get('총_리뷰수', 0):,}개"
                                                    })
                                            if review_data:
                                                st.dataframe(pd.DataFrame(review_data), use_container_width=True)
                                            else:
                                                st.info("리뷰 데이터가 없습니다.")
                                        else:
                                            st.info("리뷰 데이터가 없습니다.")
                                    
                                    with rank_tabs[2]:  # 평점
                                        if rating_col:
                                            rating_ranking = sorted(brand_analysis.items(),
                                                                  key=lambda x: x[1].get('평균_평점', 0), reverse=True)[:5]
                                            rating_data = []
                                            for rank, (brand, info) in enumerate(rating_ranking, 1):
                                                if info.get('평균_평점', 0) > 0:
                                                    brand_display = f"🎯 {brand}" if brand == "서로" else brand
                                                    rating_data.append({
                                                        '순위': f"{rank}위",
                                                        '브랜드': brand_display,
                                                        '평균 평점': f"{info.get('평균_평점', 0):.2f}점"
                                                    })
                                            if rating_data:
                                                st.dataframe(pd.DataFrame(rating_data), use_container_width=True)
                                            else:
                                                st.info("평점 데이터가 없습니다.")
                                        else:
                                            st.info("평점 데이터가 없습니다.")
                                    
                                    with rank_tabs[3]:  # 종합 영향력
                                        if review_col and rating_col:
                                            impact_ranking = sorted(brand_analysis.items(),
                                                                  key=lambda x: x[1].get('종합_영향력', 0), reverse=True)[:5]
                                            impact_data = []
                                            for rank, (brand, info) in enumerate(impact_ranking, 1):
                                                if info.get('종합_영향력', 0) > 0:
                                                    brand_display = f"🎯 {brand}" if brand == "서로" else brand
                                                    impact_data.append({
                                                        '순위': f"{rank}위",
                                                        '브랜드': brand_display,
                                                        '영향력 점수': f"{info.get('종합_영향력', 0):,.1f}"
                                                    })
                                            if impact_data:
                                                st.dataframe(pd.DataFrame(impact_data), use_container_width=True)
                                            else:
                                                st.info("종합 영향력 데이터가 없습니다.")
                                        else:
                                            st.info("종합 영향력 계산에 필요한 데이터가 없습니다.")
                                else:
                                    st.warning(f"{platform}에서 서로 브랜드를 찾을 수 없습니다.")
                                
                                # 시장 규모 정보
                                total_brands = data.get('총_브랜드수', 0)
                                total_products = data.get('총_제품수', 0)
                                st.info(f"💡 {platform} 시장 규모: {total_brands}개 브랜드, {total_products}개 제품")
                        
                        # 전체적인 플랫폼별 전략 인사이트
                        st.markdown("##### 🎯 플랫폼별 전략 우선순위")
                        
                        # 플랫폼별 종합 점수 계산
                        platform_scores = {}
                        for platform, data in platform_data.items():
                            seoro_info = data.get('서로_분석', {})
                            if seoro_info:
                                ranks = []
                                for rank_key in ['제품수_순위', '리뷰수_순위', '평점_순위', '영향력_순위']:
                                    rank = seoro_info.get(rank_key)
                                    if isinstance(rank, int):
                                        ranks.append(rank)
                                
                                if ranks:
                                    avg_rank = sum(ranks) / len(ranks)
                                    platform_scores[platform] = avg_rank
                        
                        if platform_scores:
                            sorted_platforms = sorted(platform_scores.items(), key=lambda x: x[1])
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                best_platform, best_score = sorted_platforms[0]
                                st.success(f"🏆 **최강 플랫폼**: {best_platform} (평균 {best_score:.1f}위)")
                                st.write("→ 현재 포지션 유지 및 공격적 확장")
                            
                            with col2:
                                if len(sorted_platforms) > 1:
                                    worst_platform, worst_score = sorted_platforms[-1]
                                    st.warning(f"📈 **기회 플랫폼**: {worst_platform} (평균 {worst_score:.1f}위)")
                                    st.write("→ 집중 투자로 시장 점유율 확대")
                    
                    else:
                        st.warning("플랫폼별 분석 데이터가 없습니다."),
                                '시장규모': f"{total_products}개 제품"
                            })
                        
                        summary_df = pd.DataFrame(summary_data)
                        st.dataframe(summary_df, use_container_width=True)
                        
                        # 플랫폼별 상세 분석
                        st.markdown("##### 📊 플랫폼별 상세 현황")
                        
                        for platform, data in platform_data.items():
                            with st.expander(f"🏪 {platform} 시장 분석"):
                                
                                # 전략 제안
                                strategy = data.get('전략_제안', '')
                                if strategy:
                                    if "🏆" in strategy:
                                        st.success(strategy)
                                    elif "🥉" in strategy:
                                        st.info(strategy)
                                    elif "📈" in strategy:
                                        st.warning(strategy)
                                    else:
                                        st.error(strategy)
                                
                                # 상위 5개 브랜드 순위표
                                brand_rankings = data.get('브랜드_순위', {})
                                if brand_rankings:
                                    st.markdown("**상위 브랜드 순위:**")
                                    
                                    ranking_data = []
                                    for brand, brand_data in brand_rankings.items():
                                        rank = brand_data.get('순위', 0)
                                        count = brand_data.get('제품수', 0)
                                        share = brand_data.get('점유율', 0)
                                        
                                        # 서로 브랜드 강조
                                        if brand == "서로":
                                            brand_display = f"🎯 {brand}"
                                        else:
                                            brand_display = brand
                                        
                                        ranking_data.append({
                                            '순위': f"{rank}위",
                                            '브랜드': brand_display,
                                            '제품수': f"{count}개",
                                            '점유율': f"{share}%"
                                        })
                                    
                                    ranking_df = pd.DataFrame(ranking_data)
                                    st.dataframe(ranking_df, use_container_width=True)
                                
                                # 시장 규모 정보
                                total_products = data.get('총_제품수', 0)
                                st.info(f"💡 {platform} 수정과 시장: 총 {total_products}개 제품")
                        
                        # 전체적인 인사이트
                        st.markdown("##### 🎯 플랫폼 전략 요약")
                        
                        # 가장 강한 플랫폼과 약한 플랫폼 찾기
                        best_platform = None
                        worst_platform = None
                        best_rank = float('inf')
                        worst_rank = 0
                        
                        for platform, data in platform_data.items():
                            seoro_rank = data.get('서로_순위', None)
                            if seoro_rank:
                                if seoro_rank < best_rank:
                                    best_rank = seoro_rank
                                    best_platform = platform
                                if seoro_rank > worst_rank:
                                    worst_rank = seoro_rank
                                    worst_platform = platform
                        
                        if best_platform and worst_platform and best_platform != worst_platform:
                            st.success(f"🎯 **강점 플랫폼**: {best_platform} ({best_rank}위) - 현재 포지션 유지 및 확장")
                            st.warning(f"📈 **기회 플랫폼**: {worst_platform} ({worst_rank}위) - 집중 마케팅 및 점유율 확대")
                        elif best_platform:
                            st.info(f"🎯 **주력 플랫폼**: {best_platform} ({best_rank}위)")
                    
                    else:
                        st.warning("플랫폼별 분석 데이터가 없습니다.")
        else:
            st.warning("브랜드별 분석 데이터가 없습니다.")
    
    # 기존 분석도 폴백으로 유지
    elif 'market_share' in business_insights:
        share_data = business_insights['market_share']
        
        if share_data:
            st.markdown("#### 📊 기본 제품 수 기준 점유율")
            share_df = pd.DataFrame([
                {'브랜드': brand, '제품 수': data.get('제품_수', 0), '점유율': f"{data.get('점유율_퍼센트', 0)}%"}
                for brand, data in share_data.items()
            ])
            
            st.dataframe(share_df, use_container_width=True)
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
