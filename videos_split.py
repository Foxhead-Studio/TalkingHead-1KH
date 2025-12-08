import argparse
import glob
import os
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--input_dir', type=str, required=True,
                    help='Directory containing input videos.')
parser.add_argument('--output_dir', type=str, required=True,
                    help='Directory to save split videos.')
args = parser.parse_args()


if __name__ == '__main__':
    # Create output directory
    # 출력 디렉토리를 생성한다
    # os.makedirs는 디렉토리가 이미 존재해도 오류를 발생시키지 않는다 (exist_ok=True)
    # 예를 들어, output_dir이 "small/1min_clips"이면 이 경로가 생성된다
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Get all .mp4 files in input directory
    # 입력 디렉토리 내의 모든 .mp4 파일을 찾는다
    # glob.glob()은 와일드카드 패턴을 사용하여 파일을 찾는다
    # 예를 들어, input_dir이 "small/raw_videos"이면 "small/raw_videos/*.mp4" 패턴으로 모든 .mp4 파일을 찾는다
    # 결과는 파일 경로 리스트가 된다 (예: ["small/raw_videos/video1.mp4", "small/raw_videos/video2.mp4"])
    mp4_files = glob.glob(os.path.join(args.input_dir, '*.mp4'))
    
    # Process each video file
    # 각 비디오 파일에 대해 반복한다
    # for 루프를 사용하여 mp4_files 리스트의 각 파일을 처리한다
    for input_file in mp4_files:
        # Extract filename without extension
        # 파일 경로에서 파일명만 추출하고 확장자를 제거한다
        # os.path.basename()은 경로에서 마지막 부분(파일명)만 추출한다
        # 예를 들어, "small/raw_videos/video1.mp4" → "video1.mp4"
        # os.path.splitext()는 파일명과 확장자를 분리한다
        # 예를 들어, "video1.mp4" → ("video1", ".mp4")
        # [0]은 파일명 부분만 가져온다 → "video1"
        filename_without_ext = os.path.splitext(os.path.basename(input_file))[0]
        
        # Construct output file pattern
        # 출력 파일명 패턴을 생성한다
        # os.path.join()은 경로를 올바르게 결합한다
        # 예를 들어, output_dir="small/1min_clips", filename_without_ext="video1"이면
        # "small/1min_clips/video1_%04d.mp4"가 된다
        # %04d는 ffmpeg의 segment 포맷에서 사용하는 4자리 숫자 자동 증가 패턴이다 (0000, 0001, 0002, ...)
        output_pattern = os.path.join(args.output_dir, f'{filename_without_ext}_%04d.mp4')
        
        # Run ffmpeg command to split video into 1-minute segments
        # ffmpeg 명령어를 실행하여 비디오를 1분 단위로 분할한다
        # subprocess.run()은 외부 명령어를 실행한다
        # -i: 입력 파일을 지정한다
        # -c copy: 비디오/오디오 코덱을 재인코딩하지 않고 복사한다 (빠르고 품질 손실 없음)
        # -map 0: 입력 파일의 모든 스트림(비디오, 오디오 등)을 매핑한다
        # -segment_time 00:01:00: 각 세그먼트의 길이를 1분(00:01:00)으로 설정한다
        # -f segment: 세그먼트 포맷으로 출력한다 (여러 파일로 분할)
        # output_pattern: 출력 파일명 패턴을 지정한다
        # 예를 들어, video1.mp4가 3분 길이면 video1_0000.mp4, video1_0001.mp4, video1_0002.mp4가 생성된다
        subprocess.run([
            'ffmpeg',
            '-i', input_file,
            '-c', 'copy',
            '-map', '0',
            '-segment_time', '00:01:00',
            '-f', 'segment',
            output_pattern
        ], check=False)  # check=False는 ffmpeg 오류가 발생해도 스크립트가 계속 진행되도록 한다

