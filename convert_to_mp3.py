from moviepy import VideoFileClip

def convert_mp4_to_mp3(mp4_file, mp3_file):
    try:
        # 1. 비디오 파일 불러오기
        video = VideoFileClip(mp4_file)
        
        # 2. 오디오 데이터 추출하여 저장하기
        video.audio.write_audiofile(mp3_file)
        
        # 3. 파일 닫기 (메모리 해제)
        video.close()
        print(f"변환 성공: {mp3_file}")
        
    except Exception as e:
        print(f"오류 발생: {e}")

# 실행 예시
convert_mp4_to_mp3("your_video.mp4", "extracted_audio.mp3")