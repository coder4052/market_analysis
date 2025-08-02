import streamlit as st
import requests
import json
import base64
from datetime import datetime
from config import AppConfig

class GitHubStorage:
    """GitHub 저장소와의 연동을 담당하는 클래스"""
    
    def __init__(self):
        """GitHub 연동 초기화"""
        self.github_config = AppConfig.get_github_config()
        self.token = self.github_config['token']
        self.repo = self.github_config['repo']
        self.api_url = AppConfig.get_github_api_url()
        
        # GitHub 연결 상태 확인
        self.is_connected = bool(self.token)
    
    def check_connection(self):
        """GitHub 연결 상태 확인
        
        Returns:
            tuple: (연결 성공 여부, 상태 메시지)
        """
        if not self.token:
            return False, "GitHub 토큰이 설정되지 않았습니다."
        
        try:
            headers = self._get_headers()
            response = requests.get(self.api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return True, "GitHub 연결 성공"
            elif response.status_code == 401:
                return False, "GitHub 토큰이 유효하지 않습니다."
            elif response.status_code == 404:
                return False, "GitHub 저장소를 찾을 수 없습니다."
            else:
                return False, f"GitHub 연결 실패: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "GitHub 연결 시간 초과"
        except requests.exceptions.ConnectionError:
            return False, "GitHub 연결 오류"
        except Exception as e:
            return False, f"GitHub 연결 확인 중 오류: {str(e)}"
    
    def _get_headers(self):
        """GitHub API 헤더 생성
        
        Returns:
            dict: API 요청 헤더
        """
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def load_latest_analysis(self):
        """GitHub에서 최신 분석 결과 불러오기
        
        Returns:
            dict or None: 분석 결과 데이터 또는 None
        """
        if not self.is_connected:
            st.warning("GitHub 토큰이 설정되지 않아 저장된 분석 결과를 불러올 수 없습니다.")
            return None
        
        try:
            headers = self._get_headers()
            response = requests.get(self.api_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                files = response.json()
                
                # 분석 결과 파일 찾기
                analysis_files = [
                    f for f in files 
                    if f['name'].startswith('analysis_results') and f['name'].endswith('.json')
                ]
                
                if analysis_files:
                    # 가장 최신 파일 선택 (파일명 기준)
                    latest_file = max(analysis_files, key=lambda x: x['name'])
                    
                    # 파일 내용 다운로드
                    file_response = requests.get(latest_file['download_url'], timeout=15)
                    
                    if file_response.status_code == 200:
                        analysis_data = json.loads(file_response.text)
                        
                        # 메타데이터 추가
                        analysis_data['_github_metadata'] = {
                            'filename': latest_file['name'],
                            'download_url': latest_file['download_url'],
                            'size': latest_file['size'],
                            'sha': latest_file['sha']
                        }
                        
                        return analysis_data
                    else:
                        st.error(f"파일 다운로드 실패: {file_response.status_code}")
                else:
                    st.info("저장된 분석 결과 파일이 없습니다.")
                
            elif response.status_code == 401:
                st.error("GitHub 토큰이 유효하지 않습니다.")
            elif response.status_code == 404:
                st.error("GitHub 저장소를 찾을 수 없습니다.")
            else:
                st.error(f"GitHub API 오류: {response.status_code}")
                
            return None
            
        except requests.exceptions.Timeout:
            st.error("GitHub 연결 시간 초과")
            return None
        except requests.exceptions.ConnectionError:
            st.error("GitHub 연결 오류")
            return None
        except json.JSONDecodeError:
            st.error("분석 결과 파일 형식 오류")
            return None
        except Exception as e:
            st.error(f"GitHub에서 분석 결과 로드 중 오류: {str(e)}")
            return None
    
    def save_analysis_results(self, analysis_data, custom_filename=None):
        """GitHub에 분석 결과 저장
        
        Args:
            analysis_data (dict): 저장할 분석 데이터
            custom_filename (str, optional): 사용자 정의 파일명
            
        Returns:
            tuple: (저장 성공 여부, 파일명)
        """
        if not self.is_connected:
            st.warning("GitHub 토큰이 설정되지 않아 분석 결과를 저장할 수 없습니다.")
            return False, None
        
        try:
            # 파일명 생성
            if custom_filename:
                filename = custom_filename
            else:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"analysis_results_{timestamp}.json"
            
            # JSON 콘텐츠 생성
            json_content = json.dumps(analysis_data, ensure_ascii=False, indent=2)
            content_encoded = base64.b64encode(json_content.encode('utf-8')).decode()
            
            # GitHub API 요청
            url = f"{self.api_url}/{filename}"
            headers = self._get_headers()
            
            data = {
                "message": f"📊 수정과 시장 분석 결과 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "content": content_encoded,
            }
            
            response = requests.put(url, headers=headers, json=data, timeout=20)
            
            if response.status_code in [200, 201]:
                st.success(f"✅ GitHub에 분석 결과 저장 완료: {filename}")
                return True, filename
            else:
                st.error(f"GitHub 업로드 실패: HTTP {response.status_code}")
                if response.status_code == 409:
                    st.error("파일이 이미 존재합니다. 다른 파일명을 사용하세요.")
                return False, None
                
        except requests.exceptions.Timeout:
            st.error("GitHub 저장 시간 초과")
            return False, None
        except requests.exceptions.ConnectionError:
            st.error("GitHub 연결 오류")
            return False, None
        except Exception as e:
            st.error(f"GitHub 저장 중 오류: {str(e)}")
            return False, None
    
    def clear_old_analysis_results(self, keep_latest=1):
        """GitHub에서 기존 분석 결과 파일들 정리
        
        Args:
            keep_latest (int): 보관할 최신 파일 개수 (기본값: 1)
            
        Returns:
            tuple: (정리 성공 여부, 삭제된 파일 수)
        """
        if not self.is_connected:
            return False, 0
        
        try:
            headers = self._get_headers()
            response = requests.get(self.api_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                files = response.json()
                
                # 분석 결과 파일들 찾기
                analysis_files = [
                    f for f in files 
                    if f['name'].startswith('analysis_results') and f['name'].endswith('.json')
                ]
                
                if len(analysis_files) <= keep_latest:
                    st.info("정리할 파일이 없습니다.")
                    return True, 0
                
                # 파일명 기준으로 정렬 (최신 순)
                analysis_files.sort(key=lambda x: x['name'], reverse=True)
                
                # 보관할 파일 제외하고 나머지 삭제
                files_to_delete = analysis_files[keep_latest:]
                deleted_count = 0
                
                for file_info in files_to_delete:
                    delete_success = self._delete_file(file_info, headers)
                    if delete_success:
                        deleted_count += 1
                    else:
                        st.warning(f"파일 삭제 실패: {file_info['name']}")
                
                if deleted_count > 0:
                    st.success(f"✅ {deleted_count}개의 이전 분석 결과 파일이 정리되었습니다.")
                
                return True, deleted_count
            else:
                st.error(f"GitHub 파일 목록 조회 실패: {response.status_code}")
                return False, 0
                
        except Exception as e:
            st.error(f"GitHub 파일 정리 중 오류: {str(e)}")
            return False, 0
    
    def _delete_file(self, file_info, headers):
        """개별 파일 삭제
        
        Args:
            file_info (dict): 파일 정보
            headers (dict): API 헤더
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            delete_url = f"{self.api_url}/{file_info['name']}"
            delete_data = {
                "message": f"정리: 이전 분석 결과 삭제 - {file_info['name']}",
                "sha": file_info['sha']
            }
            
            delete_response = requests.delete(
                delete_url, 
                headers=headers, 
                json=delete_data, 
                timeout=15
            )
            
            return delete_response.status_code == 200
            
        except Exception:
            return False
    
    def get_analysis_history(self, limit=10):
        """분석 결과 히스토리 조회
        
        Args:
            limit (int): 조회할 최대 파일 수
            
        Returns:
            list: 분석 결과 파일 목록
        """
        if not self.is_connected:
            return []
        
        try:
            headers = self._get_headers()
            response = requests.get(self.api_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                files = response.json()
                
                # 분석 결과 파일들 찾기
                analysis_files = [
                    f for f in files 
                    if f['name'].startswith('analysis_results') and f['name'].endswith('.json')
                ]
                
                # 파일명 기준으로 정렬 (최신 순)
                analysis_files.sort(key=lambda x: x['name'], reverse=True)
                
                # 파일 정보 정리
                history = []
                for file_info in analysis_files[:limit]:
                    # 파일명에서 타임스탬프 추출
                    filename = file_info['name']
                    if '_' in filename:
                        timestamp_part = filename.split('_')[-1].replace('.json', '')
                        try:
                            # 타임스탬프를 읽기 쉬운 형태로 변환
                            dt = datetime.strptime(timestamp_part, '%Y%m%d_%H%M%S')
                            readable_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            readable_time = timestamp_part
                    else:
                        readable_time = "시간 불명"
                    
                    history.append({
                        'filename': filename,
                        'timestamp': readable_time,
                        'size_kb': round(file_info['size'] / 1024, 1),
                        'download_url': file_info['download_url'],
                        'sha': file_info['sha']
                    })
                
                return history
            else:
                return []
                
        except Exception as e:
            st.error(f"분석 히스토리 조회 중 오류: {str(e)}")
            return []
    
    def auto_save_with_cleanup(self, analysis_data, keep_files=3):
        """분석 결과 자동 저장 및 정리
        
        Args:
            analysis_data (dict): 저장할 분석 데이터
            keep_files (int): 보관할 파일 수
            
        Returns:
            bool: 전체 작업 성공 여부
        """
        # 1. 새 분석 결과 저장
        save_success, filename = self.save_analysis_results(analysis_data)
        
        if save_success:
            # 2. 이전 파일들 정리
            cleanup_success, deleted_count = self.clear_old_analysis_results(keep_files)
            
            return True
        else:
            return False
    
    def get_storage_info(self):
        """GitHub 저장소 정보 조회
        
        Returns:
            dict: 저장소 정보
        """
        info = {
            'is_connected': self.is_connected,
            'repo': self.repo,
            'api_url': self.api_url,
            'token_configured': bool(self.token)
        }
        
        if self.is_connected:
            try:
                # 연결 상태 및 파일 수 확인
                headers = self._get_headers()
                response = requests.get(self.api_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    files = response.json()
                    analysis_files = [
                        f for f in files 
                        if f['name'].startswith('analysis_results') and f['name'].endswith('.json')
                    ]
                    
                    info.update({
                        'status': 'connected',
                        'total_files': len(files),
                        'analysis_files_count': len(analysis_files),
                        'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                else:
                    info.update({
                        'status': 'error',
                        'error_code': response.status_code
                    })
            except Exception as e:
                info.update({
                    'status': 'error',
                    'error_message': str(e)
                })
        else:
            info['status'] = 'not_configured'
        
        return info
