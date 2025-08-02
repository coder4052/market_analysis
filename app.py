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

# Streamlit 설정
st.set_page_config(**AppConfig.PAGE_CONFIG)

# GitHub 설정
github_config = AppConfig.get_github_config()
GITHUB_TOKEN = github_config['token']
GITHUB_REPO = github_config['repo']


class SujeonggwaMarketAnalyzer:
    def __init__(self):
        self.required_columns = AppConfig.REQUIRED_COLUMNS
        self.our_brand = AppConfig.OUR_BRAND
    
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
            all_products_df = combined_df.copy()
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
                                        if comp_price != 'N/A':
                                            competitor_details.append(f"{comp_brand} {comp_volume}ml×{comp_count}개 ({comp_price:,.0f}원/100ml)")
                                        else:
                                            competitor_details.append(f"{comp_brand} {comp_volume}ml×{comp_count}개 (가격정보없음)")
                                    
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
                            continue
                    
                    if our_product_competitiveness:
                        competitiveness[platform] = our_product_competitiveness
            
            category_results['business_insights']['detailed_competitiveness'] = competitiveness
        
        # 3. 용량별/개수별 시장 현황
        if '용량(ml)' in df.columns and '개수' in df.columns:
            try:
                df_for_volume = df.dropna(subset=['용량(ml)', '개수'])
                
                if not df_for_volume.empty:
                    volume_count_combinations = df_for_volume.groupby(['용량(ml)', '개수']).size().reset_index(name='제품수')
                    volume_count_combinations = volume_count_combinations.sort_values('제품수', ascending=False)
                    
                    volume_count_market = []
                    for _, combo in volume_count_combinations.head(10).iterrows():
                        volume = combo['용량(ml)']
                        count = combo['개수']
                        total_products = combo['제품수']
                        
                        our_products_in_combo = len(our_products[
                            (our_products['용량(ml)'] == volume) & 
                            (our_products['개수'] == count)
                        ])
                        
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
        
        # 4. 브랜드별 시장 점유율 분석 (기본만 유지)
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
            
        except Exception as e:
            st.warning(f"브랜드별 점유율 분석 중 오류: {str(e)}")
        
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
            
            response = requests.get(GITHUB_API_URL, headers=headers)
            
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
        if not GITHUB_TOKEN:
            return False
        
        try:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.get(GITHUB_API_URL, headers=headers)
            
            if response.status_code == 200:
                files = response.json()
                analysis_files = [f for f in files if f['name'].startswith('analysis_results') and f['name'].endswith('.json')]
                
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
