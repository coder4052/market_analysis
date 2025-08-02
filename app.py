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
# dashboard_components.py에서 UI 컴포넌트 가져오기
from dashboard_components import DashboardRenderer



# Streamlit 설정
st.set_page_config(**AppConfig.PAGE_CONFIG)

class SujeonggwaMarketAnalyzer:
    def __init__(self):
        self.required_columns = AppConfig.REQUIRED_COLUMNS
        self.our_brand = AppConfig.OUR_BRAND
        self.data_processor = DataProcessor()  # 데이터 처리기
        self.business_analyzer = BusinessAnalyzer()  # 분석 엔진 추가
        self.dashboard_renderer = DashboardRenderer()  # UI 렌더러 추가
    

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
        
        analyzer.dashboard_renderer.render_sidebar_file_info(uploaded_files, analyzer.data_processor)

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
        
        # 분석 항목 표
        analyzer.dashboard_renderer.render_sidebar_analysis_items()
    

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
                analyzer.dashboard_renderer.render_analysis_results(analysis_results, json_content, timestamp, github_success)
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
            analyzer.dashboard_renderer.render_analysis_results(
                st.session_state.analysis_results, 
                st.session_state.get('json_content', ''), 
                st.session_state.get('timestamp', 'unknown'),
                True
            )

        else:
            # 초기 화면
            analyzer.dashboard_renderer.render_welcome_message()


# Streamlit 앱 실행
if __name__ == "__main__":
    main()
