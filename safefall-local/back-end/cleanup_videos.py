import os
import shutil
from datetime import datetime

def cleanup_video_files():
    """비디오 파일 정리 도구"""
    video_dir = 'saved_videos'
    
    if not os.path.exists(video_dir):
        print("saved_videos 폴더가 없습니다.")
        return
    
    print("📁 비디오 파일 정리 도구")
    print("=" * 50)
    
    # 모든 비디오 파일 목록
    all_files = []
    for filename in os.listdir(video_dir):
        if filename.lower().endswith(('.mp4', '.avi')):
            file_path = os.path.join(video_dir, filename)
            file_size = os.path.getsize(file_path)
            file_mtime = os.path.getmtime(file_path)
            
            all_files.append({
                'name': filename,
                'path': file_path,
                'size': file_size,
                'mtime': file_mtime,
                'date': datetime.fromtimestamp(file_mtime).strftime('%Y-%m-%d %H:%M')
            })
    
    # 파일 크기별로 정렬
    all_files.sort(key=lambda x: x['mtime'], reverse=True)
    
    print(f"📊 총 비디오 파일: {len(all_files)}개")
    
    # 용량 계산
    total_size = sum(f['size'] for f in all_files)
    print(f"📦 총 용량: {total_size:,} bytes ({total_size/1024/1024:.1f} MB)")
    
    # 카테고리별 분류
    categories = {
        'web_compatible': [],    # 웹 호환 테스트 파일들
        'recent_original': [],   # 최근 원본 파일들 (보존 권장)
        'old_original': [],      # 오래된 원본 파일들 (삭제 후보)
        'converted': [],         # 변환된 파일들
        'test_files': []         # 각종 테스트 파일들
    }
    
    current_time = datetime.now().timestamp()
    week_ago = current_time - (7 * 24 * 3600)  # 1주일 전
    
    for file_info in all_files:
        filename = file_info['name']
        
        if filename.startswith('web_test_h264') or filename.startswith('web_reliable') or filename.startswith('simple_web') or filename.startswith('minimal_web'):
            categories['web_compatible'].append(file_info)
        elif filename.startswith('web_'):
            categories['converted'].append(file_info)
        elif 'test' in filename.lower():
            categories['test_files'].append(file_info)
        elif filename.startswith('fall_detection_'):
            if file_info['mtime'] > week_ago:
                categories['recent_original'].append(file_info)
            else:
                categories['old_original'].append(file_info)
        else:
            categories['test_files'].append(file_info)
    
    # 카테고리별 출력
    for category, files in categories.items():
        if files:
            category_size = sum(f['size'] for f in files)
            print(f"\n📂 {category}: {len(files)}개 파일, {category_size/1024/1024:.1f} MB")
            for file_info in files[:3]:  # 처음 3개만 표시
                print(f"   - {file_info['name']} ({file_info['size']/1024:.0f} KB, {file_info['date']})")
            if len(files) > 3:
                print(f"   ... 외 {len(files)-3}개")
    
    # 삭제 권장 사항
    print(f"\n🗑️ 삭제 권장:")
    
    # 1. 오래된 원본 파일들
    if categories['old_original']:
        old_size = sum(f['size'] for f in categories['old_original'])
        print(f"   - 오래된 원본 파일들: {len(categories['old_original'])}개, {old_size/1024/1024:.1f} MB")
    
    # 2. 변환된 파일들 (웹에서 재생 안됨)
    if categories['converted']:
        converted_size = sum(f['size'] for f in categories['converted'])
        print(f"   - 변환 파일들 (재생불가): {len(categories['converted'])}개, {converted_size/1024/1024:.1f} MB")
    
    # 3. 테스트 파일들
    if categories['test_files']:
        test_size = sum(f['size'] for f in categories['test_files'])
        print(f"   - 테스트 파일들: {len(categories['test_files'])}개, {test_size/1024/1024:.1f} MB")
    
    total_deletable = sum(f['size'] for f in categories['old_original'] + categories['converted'] + categories['test_files'])
    
    print(f"\n💾 삭제 시 절약 가능: {total_deletable/1024/1024:.1f} MB")
    
    # 보존 권장
    keep_files = categories['recent_original'] + categories['web_compatible']
    if keep_files:
        keep_size = sum(f['size'] for f in keep_files)
        print(f"📌 보존 권장: {len(keep_files)}개, {keep_size/1024/1024:.1f} MB")
    
    return categories

def delete_category(categories, category_name):
    """특정 카테고리 파일들 삭제"""
    if category_name not in categories:
        print(f"❌ '{category_name}' 카테고리가 없습니다.")
        return
    
    files = categories[category_name]
    if not files:
        print(f"📂 '{category_name}' 카테고리에 파일이 없습니다.")
        return
    
    total_size = sum(f['size'] for f in files)
    print(f"🗑️ '{category_name}' 카테고리 삭제: {len(files)}개 파일, {total_size/1024/1024:.1f} MB")
    
    # 백업 폴더 생성 (혹시 모를 상황 대비)
    backup_dir = 'backup_deleted_videos'
    os.makedirs(backup_dir, exist_ok=True)
    
    deleted_count = 0
    for file_info in files:
        try:
            # 백업 복사
            backup_path = os.path.join(backup_dir, file_info['name'])
            shutil.copy2(file_info['path'], backup_path)
            
            # 원본 삭제
            os.remove(file_info['path'])
            print(f"   ✅ 삭제: {file_info['name']}")
            deleted_count += 1
            
        except Exception as e:
            print(f"   ❌ 삭제 실패: {file_info['name']} - {e}")
    
    print(f"✅ {deleted_count}개 파일 삭제 완료")
    print(f"📁 백업 위치: {backup_dir}")

if __name__ == "__main__":
    # 1. 파일 분석
    categories = cleanup_video_files()
    
    print(f"\n" + "=" * 50)
    print("🔧 삭제 옵션:")
    print("1. old_original - 오래된 원본 파일들")
    print("2. converted - 변환된 파일들 (재생 불가)")
    print("3. test_files - 테스트 파일들")
    print("4. 모든 삭제 권장 파일들")
    print("\n주의: 파일들은 backup_deleted_videos 폴더에 백업됩니다.")
    
    # 사용자 입력 대신 자동으로 안전한 삭제만 수행
    print(f"\n🤖 자동 정리 권장사항:")
    
    # 변환된 파일들 (재생되지 않음)
    if categories.get('converted'):
        print(f"   - 변환 파일들: 웹에서 재생되지 않으므로 삭제 권장")
    
    # 테스트 파일들 (web_test_h264.mp4 제외)
    if categories.get('test_files'):
        print(f"   - 테스트 파일들: 개발용이므로 삭제 권장")
    
    print(f"\n수동 삭제를 원한다면:")
    print(f"   delete_category(categories, 'converted')")
    print(f"   delete_category(categories, 'test_files')")
