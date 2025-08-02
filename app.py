"""
서로 수정과 시장 가격 분석 대시보드
모듈화된 구조로 구성된 메인 애플리케이션
"""

import streamlit as st
import json
from datetime import datetime

# 모듈화된 컴포넌트들 임포트
from config import AppConfig
from data_handler import DataProcessor
from analysis_engine import BusinessAnalyzer
from dashboard_components import DashboardRenderer
from github_connector import GitHubStorage


class SujeonggwaApp:
    """수정과 시장 분석 메인 애플리케이션 클래스"""
    
    def __init__(self):
        """앱 초기화 - 모든 모듈 컴포넌트 초기화"""
        self.config = AppConfig()
        self.data_processor = DataProcessor()
        self.business_analyzer = BusinessAnalyzer()
        self.dashboard_renderer = DashboardRenderer()
        self.github_storage = GitHubStorage()
        
        # 세션 상태 초기화
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """세션 상태 초기화"""
        session_defaults = {
            'run_analysis': False,
            'analysis_results': None,
            'json_content': None,
            'timestamp': None
        }
        
        for key, default_value in session_defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value
    
    def render_header(self):
        """앱 헤더 렌더링"""
        st.title("🥤 서로 수정과 - 시장 가격 분석 대시보드")
        st.markdown("##### *플랫폼별 가격 경쟁력 및 시장 포지셔닝 분석*")
        st.markdown("---")
    
    def render_sidebar(self):
        """사이드바 렌더링
        
        Returns:
            list: 업로드된 파일 리스트
        """
        with st.sidebar:
            st.header("📊 분석 설정")
            
            # 파일 업로드
            uploaded_files = st.file_uploader(
                "엑셀 파일 업로드",
                type=['xlsx', 'xls'],
                accept_multiple_files=True,
                help=self.config.UI_MESSAGES['upload_help']
            )
            
            st.markdown("---")
            
            # 파일 정보 표시
            self.dashboard_renderer.render_sidebar_file_info(uploaded_files, self.data_processor)
            
            # 데이터 품질 정보
            if uploaded_files:
                self._render_data_quality_info(uploaded_files)
            
            # 분석 시작 버튼
            if st.button("🚀 분석 시작", type="primary", disabled=not uploaded_files):
                st.session_state.run_analysis = True
            
            st.markdown("---")
            
            # 분석 항목 표시
            self.dashboard_renderer.render_sidebar_analysis_items()
            
            # GitHub 상태 정보
            self._render_github_status()
            
        return uploaded_files
    
    def _render_data_quality_info(self, uploaded_files):
        """데이터 품질 정보 렌더링"""
        with st.expander("📊 데이터 품질 확인", expanded=False):
            temp_df_list = []
            for file in uploaded_files:
                df, platform, missing_cols = self.data_processor.load_and_standardize_excel(file)
                if df is not None:
                    temp_df_list.append(df)
            
            if temp_df_list:
                self.dashboard_renderer.render_data_quality_info(temp_df_list, self.data_processor)
    
    def _render_github_status(self):
        """GitHub 상태 정보 렌더링"""
        st.markdown("---")
        st.markdown("### 💾 GitHub 저장소")
        
        storage_info = self.github_storage.get_storage_info()
        if storage_info['is_connected']:
            st.success("✅ 연결됨")
            if storage_info.get('analysis_files_count', 0) > 0:
                st.info(f"📁 저장된 분석 결과: {storage_info['analysis_files_count']}개")
                
                # 분석 히스토리 표시
                with st.expander("📋 분석 히스토리", expanded=False):
                    history = self.github_storage.get_analysis_history(limit=5)
                    if history:
                        for item in history:
                            st.write(f"📄 {item['timestamp']} ({item['size_kb']}KB)")
                    else:
                        st.write("히스토리가 없습니다.")
        else:
            st.warning("⚠️ GitHub 토큰 미설정")
            st.caption("GitHub 저장 기능을 사용하려면 토큰을 설정하세요.")
    
    def process_uploaded_files(self, uploaded_files):
        """업로드된 파일들 처리
        
        Args:
            uploaded_files (list): 업로드된 파일 리스트
            
        Returns:
            list: 처리된 DataFrame 리스트
        """
        df_list = []
        
        # 프로그레스 표시
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        # 파일 처리
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"{self.config.UI_MESSAGES['file_processing']}: {uploaded_file.name}")
            progress_bar.progress((i + 1) / len(uploaded_files) * 0.4)
            
            df, platform, missing_cols = self.data_processor.load_and_standardize_excel(uploaded_file)
            
            if df is not None:
                df_list.append(df)
        
        # 프로그레스 정리
        progress_bar.progress(1.0)
        status_text.empty()
        progress_container.empty()
        
        return df_list
    
    def perform_analysis(self, df_list):
        """분석 수행
        
        Args:
            df_list (list): 처리된 DataFrame 리스트
            
        Returns:
            tuple: (분석 결과, GitHub 저장 성공 여부)
        """
        if not df_list:
            st.error("처리할 수 있는 파일이 없습니다.")
            return None, False
        
        # 분석 진행 표시
        with st.spinner(self.config.UI_MESSAGES['market_analysis']):
            analysis_results, handmade_df, all_products_df = self.business_analyzer.analyze_business_critical_data(df_list)
        
        if not analysis_results:
            st.error("분석 중 오류가 발생했습니다.")
            return None, False
        
        # GitHub에 저장
        github_success = False
        with st.spinner(self.config.UI_MESSAGES['github_save']):
            if self.github_storage.is_connected:
                github_success = self.github_storage.auto_save_with_cleanup(
                    analysis_results, keep_files=3
                )
            else:
                st.info("GitHub 연결이 없어 분석 결과를 로컬에서만 표시합니다.")
        
        # 세션 상태에 저장
        st.session_state.analysis_results = analysis_results
        st.session_state.json_content = json.dumps(analysis_results, ensure_ascii=False, indent=2)
        st.session_state.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return analysis_results, github_success
    
    def load_previous_analysis(self):
        """이전 분석 결과 로드"""
        if not st.session_state.get('analysis_results'):
            with st.spinner("GitHub에서 최신 분석 결과를 불러오는 중..."):
                latest_analysis = self.github_storage.load_latest_analysis()
                
                if latest_analysis:
                    st.session_state.analysis_results = latest_analysis
                    st.session_state.json_content = json.dumps(latest_analysis, ensure_ascii=False, indent=2)
                    st.session_state.timestamp = latest_analysis.get('timestamp', 'unknown')
                    st.success("✅ GitHub에서 최신 분석 결과를 불러왔습니다!")
    
    def render_analysis_results(self, analysis_results, github_success):
        """분석 결과 렌더링
        
        Args:
            analysis_results (dict): 분석 결과
            github_success (bool): GitHub 저장 성공 여부
        """
        self.dashboard_renderer.render_analysis_results(
            analysis_results,
            st.session_state.get('json_content', ''),
            st.session_state.get('timestamp', 'unknown'),
            github_success
        )
    
    def run(self):
        """메인 앱 실행"""
        # Streamlit 페이지 설정
        st.set_page_config(**self.config.PAGE_CONFIG)
        
        # 헤더 렌더링
        self.render_header()
        
        # 사이드바 렌더링
        uploaded_files = self.render_sidebar()
        
        # 메인 로직
        if uploaded_files and st.session_state.get('run_analysis', False):
            # 새로운 분석 수행
            df_list = self.process_uploaded_files(uploaded_files)
            analysis_results, github_success = self.perform_analysis(df_list)
            
            if analysis_results:
                self.render_analysis_results(analysis_results, github_success)
            
            # 분석 완료 후 상태 리셋
            st.session_state.run_analysis = False
            
        elif st.session_state.get('analysis_results') or not uploaded_files:
            # 기존 분석 결과 표시 또는 초기 화면
            if not uploaded_files:
                self.load_previous_analysis()
            
            if st.session_state.get('analysis_results'):
                self.render_analysis_results(
                    st.session_state.analysis_results,
                    True  # 기존 결과는 이미 저장된 것으로 간주
                )
            else:
                # 초기 환영 화면
                self.dashboard_renderer.render_welcome_message()


def main():
    """메인 함수 - 앱 인스턴스 생성 및 실행"""
    try:
        app = SujeonggwaApp()
        app.run()
    except Exception as e:
        st.error(f"앱 실행 중 오류가 발생했습니다: {str(e)}")
        st.info("페이지를 새로고침하거나 관리자에게 문의하세요.")


if __name__ == "__main__":
    main()
