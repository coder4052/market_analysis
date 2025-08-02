import streamlit as st

class AppConfig:
    """수정과 시장 분석 앱의 모든 설정을 관리하는 클래스"""
    
    # 🎨 Streamlit 앱 기본 설정
    PAGE_CONFIG = {
        "page_title": "서로 수정과 - 시장 가격 분석",
        "page_icon": "🥤",
        "layout": "wide"
    }
    
    # 🏷️ 브랜드 설정
    OUR_BRAND = "서로"
    
    # 📊 분석에 필요한 엑셀 컬럼들
    REQUIRED_COLUMNS = [
        "브랜드", 
        "제품명", 
        "용량(ml)", 
        "개수", 
        "일반 판매가", 
        "일반 판매가 단위가격(100ml당)", 
        "상시 할인가", 
        "상시 할인가 단위가격(100ml당)",
        "배송비", 
        "최저가(배송비 포함)", 
        "최저가 단위가격(100ml당)", 
        "공장형 여부", 
        "리뷰 개수", 
        "평점"
    ]
    
    # 🏪 플랫폼 매핑 (파일명에서 플랫폼을 찾기 위한 키워드)
    PLATFORM_KEYWORDS = {
        '네이버': '네이버',
        '쿠팡': '쿠팡', 
        '올웨이즈': '올웨이즈'
    }
    
    # 🔢 분석 관련 설정
    ANALYSIS_SETTINGS = {
        'volume_similarity_range': 0.2,  # 유사 용량 범위 (±20%)
        'top_brands_count': 10,          # 상위 브랜드 개수
        'top_volume_combinations': 10,   # 상위 용량 조합 개수
        'main_competitors_count': 3      # 주요 경쟁사 표시 개수
    }
    
    # 📁 GitHub 설정을 가져오는 함수
    @staticmethod
    def get_github_config():
        """GitHub 토큰과 저장소 정보를 안전하게 가져옵니다"""
        try:
            return {
                'token': st.secrets.get("GITHUB_TOKEN", "") if hasattr(st, 'secrets') else "",
                'repo': st.secrets.get("GITHUB_REPO", "coder4052/market_analysis") if hasattr(st, 'secrets') else "coder4052/market_analysis"
            }
        except:
            # secrets가 없어도 기본값으로 동작하도록
            return {
                'token': "",
                'repo': "coder4052/market_analysis"
            }
    
    # 📈 UI 메시지들
    UI_MESSAGES = {
        'upload_help': "네이버, 쿠팡, 올웨이즈 수정과 가격 데이터",
        'analysis_items': [
            "✅ 제품별 가격 경쟁력",
            "✅ 용량/개수별 시장 분석",  
            "✅ 브랜드별 점유율",
            "✅ 진출 기회 발견"
        ],
        'file_processing': "📂 파일 처리 중",
        'market_analysis': "🔍 시장 데이터 분석 중...",
        'visualization': "📈 시각화 생성 중...",
        'github_save': "💾 GitHub에 저장 중..."
    }
    
    # 🎯 비즈니스 인사이트 관련 설정
    BUSINESS_INSIGHTS = {
        'market_position_thresholds': {
            'best_price': 'minimum',      # 최저가 조건
            'below_average': 'average',   # 평균 이하 조건  
            'above_average': 'above_avg', # 평균 이상 조건
            'premium': 'maximum'          # 프리미엄 조건
        },
        'performance_metrics': {
            'excellent_rating': 4.5,     # 우수 평점 기준
            'good_rating': 4.0,          # 양호 평점 기준
            'high_engagement_multiplier': 2.0,  # 높은 관심도 배수
            'good_engagement_multiplier': 1.0   # 양호한 관심도 배수
        }
    }
