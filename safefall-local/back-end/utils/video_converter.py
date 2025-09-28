import os
import cv2
import threading
from datetime import datetime

class VideoConverter:
    """AVI 파일을 웹 호환 MP4로 변환하는 유틸리티"""
    
    def __init__(self):
        self._conversion_lock = threading.Lock()
    
    def avi_to_mp4(self, avi_path, mp4_path=None, remove_original=False):
        """AVI 파일을 MP4로 변환
        
        Args:
            avi_path: 원본 AVI 파일 경로
            mp4_path: 변환될 MP4 파일 경로 (없으면 자동 생성)
            remove_original: 변환 후 원본 AVI 파일 삭제 여부
            
        Returns:
            dict: 변환 결과 {'success': bool, 'mp4_path': str, 'error': str}
        """
        with self._conversion_lock:
            try:
                if not os.path.exists(avi_path):
                    return {'success': False, 'error': f'AVI 파일이 없습니다: {avi_path}'}
                
                if mp4_path is None:
                    mp4_path = avi_path.replace('.avi', '.mp4')
                
                print(f"🔄 AVI → MP4 변환 시작: {avi_path} → {mp4_path}")
                
                # 원본 AVI 파일 열기
                cap = cv2.VideoCapture(avi_path)
                if not cap.isOpened():
                    return {'success': False, 'error': f'AVI 파일을 열 수 없습니다: {avi_path}'}
                
                # 원본 비디오 정보 가져오기
                fps = cap.get(cv2.CAP_PROP_FPS)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                
                print(f"원본 비디오 정보: {width}x{height}, {fps}fps, {total_frames}프레임")
                
                # MP4 writer 생성 (웹 호환 코덱 사용)
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(mp4_path, fourcc, fps, (width, height))
                
                if not out.isOpened():
                    cap.release()
                    return {'success': False, 'error': f'MP4 writer를 생성할 수 없습니다: {mp4_path}'}
                
                # 프레임별 변환
                frame_count = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    out.write(frame)
                    frame_count += 1
                    
                    # 진행률 출력
                    if frame_count % 50 == 0 or frame_count == total_frames:
                        progress = (frame_count / total_frames) * 100 if total_frames > 0 else 0
                        print(f"변환 진행률: {progress:.1f}% ({frame_count}/{total_frames})")
                
                # 리소스 해제
                cap.release()
                out.release()
                
                # 변환된 파일 검증
                if os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 1000:
                    # MP4 파일이 정상적으로 재생되는지 확인
                    test_cap = cv2.VideoCapture(mp4_path)
                    if test_cap.isOpened():
                        test_frames = int(test_cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        test_cap.release()
                        
                        print(f"✅ 변환 완료: {mp4_path} ({test_frames}프레임)")
                        
                        # 원본 파일 삭제 (옵션)
                        if remove_original:
                            try:
                                os.remove(avi_path)
                                print(f"🗑️ 원본 AVI 파일 삭제: {avi_path}")
                            except Exception as e:
                                print(f"⚠️ 원본 파일 삭제 실패: {e}")
                        
                        return {
                            'success': True, 
                            'mp4_path': mp4_path,
                            'original_frames': total_frames,
                            'converted_frames': test_frames
                        }
                    else:
                        return {'success': False, 'error': f'변환된 MP4 파일을 재생할 수 없습니다: {mp4_path}'}
                else:
                    return {'success': False, 'error': f'MP4 파일이 정상적으로 생성되지 않았습니다: {mp4_path}'}
                    
            except Exception as e:
                return {'success': False, 'error': f'변환 중 오류 발생: {str(e)}'}
    
    def convert_all_avi_in_directory(self, directory, remove_originals=False):
        """디렉토리 내 모든 AVI 파일을 MP4로 변환
        
        Args:
            directory: 검사할 디렉토리 경로
            remove_originals: 변환 후 원본 AVI 파일들 삭제 여부
            
        Returns:
            dict: 변환 결과 통계
        """
        if not os.path.isdir(directory):
            return {'success': False, 'error': f'디렉토리가 없습니다: {directory}'}
        
        avi_files = [f for f in os.listdir(directory) if f.lower().endswith('.avi')]
        if not avi_files:
            return {'success': True, 'message': 'AVI 파일이 없습니다', 'converted': 0}
        
        print(f"📁 {len(avi_files)}개의 AVI 파일을 MP4로 변환합니다...")
        
        results = {'converted': 0, 'failed': 0, 'errors': []}
        
        for avi_file in avi_files:
            avi_path = os.path.join(directory, avi_file)
            mp4_path = os.path.join(directory, avi_file.replace('.avi', '.mp4'))
            
            # 이미 MP4가 존재하면 건너뛰기
            if os.path.exists(mp4_path):
                print(f"⏩ MP4 파일이 이미 존재하여 건너뛰기: {mp4_path}")
                continue
            
            result = self.avi_to_mp4(avi_path, mp4_path, remove_originals)
            
            if result['success']:
                results['converted'] += 1
                print(f"✅ 변환 성공: {avi_file}")
            else:
                results['failed'] += 1
                results['errors'].append(f"{avi_file}: {result['error']}")
                print(f"❌ 변환 실패: {avi_file} - {result['error']}")
        
        results['success'] = True
        results['total_avi_files'] = len(avi_files)
        
        print(f"🎬 변환 완료: {results['converted']}개 성공, {results['failed']}개 실패")
        
        return results

def test_converter():
    """변환기 테스트"""
    converter = VideoConverter()
    
    # saved_videos 디렉토리의 모든 AVI 파일 변환
    saved_videos_dir = os.path.join(os.path.dirname(__file__), '..', 'saved_videos')
    saved_videos_dir = os.path.abspath(saved_videos_dir)
    
    print(f"🔍 AVI 파일 검색 중: {saved_videos_dir}")
    
    if os.path.exists(saved_videos_dir):
        result = converter.convert_all_avi_in_directory(saved_videos_dir)
        print(f"변환 결과: {result}")
    else:
        print(f"디렉토리가 존재하지 않습니다: {saved_videos_dir}")

if __name__ == "__main__":
    test_converter()
