import pandas as pd
import streamlit as st
from datetime import datetime
from config import AppConfig

class DataProcessor:
    """엑셀 파일 로드 및 데이터 표준화를 담당하는 클래스"""
    
    def __init__(self):
        """데이터 처리기 초기화"""
        self.required_columns = AppConfig.REQUIRED_COLUMNS
        self.platform_keywords = AppConfig.PLATFORM_KEYWORDS
    
    def extract_platform_from_filename(self, filename):
        """파일명에서 플랫폼 추출
        
        Args:
            filename (str): 업로드된 파일의 이름
            
        Returns:
            str: 추출된 플랫폼 이름 (네이버, 쿠팡, 올웨이즈, 기타)
        """
        filename_lower = filename.lower()
        
        # config.py에서 정의한 키워드로 플랫폼 찾기
        for keyword, platform_name in self.platform_keywords.items():
            if keyword in filename:
                return platform_name
        
        # 키워드가 없으면 기타로 분류
        return '기타'
    
    def load_and_standardize_excel(self, uploaded_file):
        """엑셀 파일 로드 및 표준화
        
        Args:
            uploaded_file: Streamlit의 UploadedFile 객체
            
        Returns:
            tuple: (정제된 DataFrame, 플랫폼명, 누락된 컬럼 리스트)
        """
        try:
            # 엑셀 파일 읽기
            df = pd.read_excel(uploaded_file, sheet_name=0)
            
            # 플랫폼 추출
            platform = self.extract_platform_from_filename(uploaded_file.name)
            
            # 사용 가능한 컬럼과 누락된 컬럼 확인
            available_columns = [col for col in self.required_columns if col in df.columns]
            missing_columns = [col for col in self.required_columns if col not in df.columns]
            
            # 누락된 컬럼이 있으면 경고 표시
            if missing_columns:
                st.warning(f"[{platform}] 누락된 컬럼: {missing_columns}")
            
            # 필수 컬럼이 없으면 에러
            if not available_columns:
                st.error(f"[{platform}] 필수 컬럼이 없습니다.")
                return None, None, None
            
            # 데이터 정제 수행
            df_clean = self._clean_data(df, available_columns, platform)
            
            return df_clean, platform, missing_columns
            
        except Exception as e:
            st.error(f"파일 처리 중 오류: {str(e)}")
            return None, None, None
    
    def _clean_data(self, df, available_columns, platform):
        """데이터 정제 및 표준화
        
        Args:
            df (DataFrame): 원본 데이터프레임
            available_columns (list): 사용 가능한 컬럼 리스트
            platform (str): 플랫폼명
            
        Returns:
            DataFrame: 정제된 데이터프레임
        """
        # 필요한 컬럼만 추출
        df_clean = df[available_columns].copy()
        
        # 메타데이터 추가
        df_clean['플랫폼'] = platform
        df_clean['분석_시간'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # 숫자형 컬럼 변환
        numeric_columns = self._get_numeric_columns()
        for col in numeric_columns:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
        
        # 필수 데이터가 없는 행 제거
        essential_columns = ['브랜드', '제품명']
        for col in essential_columns:
            if col in df_clean.columns:
                df_clean = df_clean.dropna(subset=[col])
        
        return df_clean
    
    def _get_numeric_columns(self):
        """숫자형으로 변환해야 하는 컬럼 리스트 반환
        
        Returns:
            list: 숫자형 컬럼 이름들
        """
        return [
            '용량(ml)', 
            '개수', 
            '일반 판매가',
            '일반 판매가 단위가격(100ml당)',
            '상시 할인가',
            '상시 할인가 단위가격(100ml당)',
            '배송비',
            '최저가(배송비 포함)', 
            '최저가 단위가격(100ml당)', 
            '공장형 여부',
            '리뷰 개수',
            '평점'
        ]
    
    def validate_data_quality(self, df_list):
        """업로드된 데이터들의 품질을 검증
        
        Args:
            df_list (list): 정제된 DataFrame들의 리스트
            
        Returns:
            dict: 검증 결과 정보
        """
        if not df_list:
            return {
                'total_files': 0,
                'total_products': 0,
                'platforms': [],
                'quality_issues': ['업로드된 파일이 없습니다.']
            }
        
        validation_result = {
            'total_files': len(df_list),
            'total_products': sum(len(df) for df in df_list),
            'platforms': [],
            'quality_issues': []
        }
        
        for df in df_list:
            if '플랫폼' in df.columns:
                platforms = df['플랫폼'].unique().tolist()
                validation_result['platforms'].extend(platforms)
            
            # 데이터 품질 이슈 체크
            issues = self._check_data_issues(df)
            validation_result['quality_issues'].extend(issues)
        
        # 플랫폼 중복 제거
        validation_result['platforms'] = list(set(validation_result['platforms']))
        
        return validation_result
    
    def _check_data_issues(self, df):
        """개별 DataFrame의 데이터 품질 이슈 확인
        
        Args:
            df (DataFrame): 확인할 데이터프레임
            
        Returns:
            list: 발견된 이슈들
        """
        issues = []
        
        if df.empty:
            issues.append("빈 데이터프레임이 있습니다.")
            return issues
        
        platform = df['플랫폼'].iloc[0] if '플랫폼' in df.columns else '알 수 없음'
        
        # 필수 컬럼 확인
        essential_cols = ['브랜드', '제품명']
        for col in essential_cols:
            if col not in df.columns:
                issues.append(f"[{platform}] 필수 컬럼 '{col}'이 없습니다.")
            elif df[col].isna().all():
                issues.append(f"[{platform}] '{col}' 컬럼의 모든 값이 비어있습니다.")
        
        # 가격 정보 확인
        price_cols = ['최저가(배송비 포함)', '최저가 단위가격(100ml당)']
        price_available = False
        for col in price_cols:
            if col in df.columns and not df[col].isna().all():
                price_available = True
                break
        
        if not price_available:
            issues.append(f"[{platform}] 가격 정보가 없습니다.")
        
        # 용량/개수 정보 확인
        volume_info = ['용량(ml)', '개수']
        volume_available = False
        for col in volume_info:
            if col in df.columns and not df[col].isna().all():
                volume_available = True
                break
                
        if not volume_available:
            issues.append(f"[{platform}] 용량/개수 정보가 없습니다.")
        
        # 서로 브랜드 제품 확인
        if '브랜드' in df.columns:
            our_products = df[df['브랜드'] == AppConfig.OUR_BRAND]
            if our_products.empty:
                issues.append(f"[{platform}] '{AppConfig.OUR_BRAND}' 브랜드 제품이 없습니다.")
        
        return issues
    
    def get_file_summary(self, df_list):
        """업로드된 파일들의 요약 정보 생성
        
        Args:
            df_list (list): 정제된 DataFrame들의 리스트
            
        Returns:
            list: 파일별 요약 정보
        """
        summary = []
        
        for df in df_list:
            if df.empty:
                continue
                
            platform = df['플랫폼'].iloc[0] if '플랫폼' in df.columns else '알 수 없음'
            
            file_info = {
                'platform': platform,
                'total_products': len(df),
                'unique_brands': len(df['브랜드'].unique()) if '브랜드' in df.columns else 0,
                'our_products': len(df[df['브랜드'] == AppConfig.OUR_BRAND]) if '브랜드' in df.columns else 0,
                'has_price_info': '최저가(배송비 포함)' in df.columns and not df['최저가(배송비 포함)'].isna().all(),
                'has_volume_info': '용량(ml)' in df.columns and not df['용량(ml)'].isna().all()
            }
            
            summary.append(file_info)
        
        return summary
