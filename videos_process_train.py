# Copyright (c) 2022, NVIDIA CORPORATION. All rights reserved.
#
# This script is licensed under the MIT License.

import argparse
import glob
import os
import subprocess
from functools import partial
from time import time as timer

import ffmpeg
from pytubefix import YouTube
from tqdm import tqdm

# videos_crop.py에서 필요한 함수들을 import
from videos_crop import get_h_w, get_fps, trim_and_crop_min_size

parser = argparse.ArgumentParser()
parser.add_argument('--video_ids_file', type=str, required=True,
                    help='File containing video IDs (one per line).')
parser.add_argument('--tubes_file', type=str, required=True,
                    help='File containing video tube information.')
parser.add_argument('--output_dir', type=str, required=True,
                    help='Directory to save cropped clips.')
parser.add_argument('--temp_raw_dir', type=str, default='train/temp_raw_videos',
                    help='Temporary directory for raw downloaded videos.')
parser.add_argument('--temp_split_dir', type=str, default='train/temp_1min_clips',
                    help='Temporary directory for 1-minute split videos.')
parser.add_argument('--delete_temp', type=str, default='on', choices=['on', 'off'],
                    help='Whether to delete temporary files (raw videos and 1-min clips) after cropping. Default: on')
parser.add_argument('--min_crop_width', type=int, default=256,
                    help='Minimum crop width in pixels. Only videos with crop width >= this value will be processed.')
parser.add_argument('--min_crop_height', type=int, default=256,
                    help='Minimum crop height in pixels. Only videos with crop height >= this value will be processed.')
parser.add_argument('--num_workers', type=int, default=8,
                    help='How many multiprocessing workers for cropping?')
args = parser.parse_args()


def download_video(output_dir, video_id):
    # 비디오를 다운로드하는 함수
    # output_dir: 비디오를 저장할 디렉토리 경로
    # video_id: YouTube 비디오 ID (예: '--Y9imYnfBw')
    # 반환값: 다운로드된 비디오 파일 경로, 실패 시 None
    
    # 저장될 비디오 파일 경로를 생성한다
    # 예) output_dir='train/temp_raw_videos', video_id='--Y9imYnfBw'이면
    #     'train/temp_raw_videos/--Y9imYnfBw.mp4'가 video_path가 된다
    video_path = os.path.join(output_dir, video_id + '.mp4')
    
    # 파일이 이미 존재하면 다운로드하지 않고 경로만 반환한다
    # os.path.isfile()은 파일이 존재하는지 확인한다
    if os.path.isfile(video_path):
        print('File exists: %s' % (video_id))
        return video_path
    
    # 파일이 없으면 다운로드를 시도한다
    try:
        # YouTube 객체를 생성한다
        # 'https://www.youtube.com/watch?v=%s' 형식의 URL을 사용한다
        # 예) video_id='--Y9imYnfBw'이면 'https://www.youtube.com/watch?v=--Y9imYnfBw'
        yt = YouTube('https://www.youtube.com/watch?v=%s' % (video_id))
        # 가장 높은 화질의 mp4 스트림을 찾는다
        # progressive=True는 비디오와 오디오가 함께 있는 스트림을 의미한다
        # adaptive=True는 적응형 스트림을 포함한다
        stream = yt.streams.filter(subtype='mp4', progressive=True, adaptive=True).first()
        # 조건에 맞는 스트림이 없으면 mp4 타입 중 첫 번째를 선택한다
        if stream is None:
            stream = yt.streams.filter(subtype='mp4').first()
        # 비디오를 다운로드한다
        # output_path는 저장할 디렉토리, filename은 파일명이다
        stream.download(output_path=output_dir, filename=video_id + '.mp4')
        print('Downloaded: %s' % (video_id))
        return video_path
    except Exception as e:
        # 다운로드 실패 시 에러 메시지를 출력하고 None을 반환한다
        print(e)
        print('Failed to download %s' % (video_id))
        return None


def split_video(input_file, output_dir):
    # 비디오를 1분 단위로 분할하는 함수
    # input_file: 입력 비디오 파일 경로
    # output_dir: 분할된 비디오를 저장할 디렉토리 경로
    # 반환값: 성공 시 True, 실패 시 False
    
    # 파일 경로에서 파일명만 추출하고 확장자를 제거한다
    # os.path.basename()은 경로에서 마지막 부분(파일명)만 추출한다
    # 예) "train/temp_raw_videos/--Y9imYnfBw.mp4" → "--Y9imYnfBw.mp4"
    # os.path.splitext()는 파일명과 확장자를 분리한다
    # 예) "--Y9imYnfBw.mp4" → ("--Y9imYnfBw", ".mp4")
    # [0]은 파일명 부분만 가져온다 → "--Y9imYnfBw"
    filename_without_ext = os.path.splitext(os.path.basename(input_file))[0]
    
    # 출력 파일명 패턴을 생성한다
    # os.path.join()은 경로를 올바르게 결합한다
    # 예) output_dir="train/temp_1min_clips", filename_without_ext="--Y9imYnfBw"이면
    #     "train/temp_1min_clips/--Y9imYnfBw_%04d.mp4"가 된다
    # %04d는 ffmpeg의 segment 포맷에서 사용하는 4자리 숫자 자동 증가 패턴이다 (0000, 0001, 0002, ...)
    output_pattern = os.path.join(output_dir, f'{filename_without_ext}_%04d.mp4')
    
    # ffmpeg 명령어를 실행하여 비디오를 1분 단위로 분할한다
    # subprocess.run()은 외부 명령어를 실행한다
    # -i: 입력 파일을 지정한다
    # -c copy: 비디오/오디오 코덱을 재인코딩하지 않고 복사한다 (빠르고 품질 손실 없음)
    # -map 0: 입력 파일의 모든 스트림(비디오, 오디오 등)을 매핑한다
    # -segment_time 00:01:00: 각 세그먼트의 길이를 1분(00:01:00)으로 설정한다
    # -f segment: 세그먼트 포맷으로 출력한다 (여러 파일로 분할)
    # output_pattern: 출력 파일명 패턴을 지정한다
    # 예를 들어, --Y9imYnfBw.mp4가 3분 길이면 --Y9imYnfBw_0000.mp4, --Y9imYnfBw_0001.mp4, --Y9imYnfBw_0002.mp4가 생성된다
    try:
        result = subprocess.run([
            'ffmpeg',
            '-i', input_file,
            '-c', 'copy',
            '-map', '0',
            '-segment_time', '00:01:00',
            '-f', 'segment',
            output_pattern
        ], check=False, capture_output=True, text=True)  # check=False는 오류가 발생해도 예외를 발생시키지 않는다
        # capture_output=True는 stdout과 stderr를 캡처한다
        # text=True는 출력을 문자열로 받는다
        
        # ffmpeg가 성공적으로 실행되었는지 확인한다
        # returncode가 0이면 성공이다
        if result.returncode == 0:
            print('Split video: %s' % (os.path.basename(input_file)))
            return True
        else:
            print('Failed to split video: %s' % (os.path.basename(input_file)))
            print(result.stderr)
            return False
    except Exception as e:
        print('Error splitting video %s: %s' % (os.path.basename(input_file), str(e)))
        return False


def get_tubes_for_video(tubes_file, video_id):
    # 특정 비디오 ID에 해당하는 모든 tube 정보를 가져오는 함수
    # tubes_file: tube 정보가 담긴 파일 경로
    # video_id: 비디오 ID (예: '--Y9imYnfBw')
    # 반환값: 해당 비디오의 tube 정보 리스트
    
    # tube 정보를 저장할 리스트를 생성한다
    tubes = []
    
    # tube 정보 파일을 읽어온다
    # open()은 파일을 열고, with 문을 사용하면 파일 읽기가 끝나면 자동으로 파일을 닫는다
    with open(tubes_file, 'r') as fin:
        # 파일의 각 줄을 순회한다
        for line in fin:
            # 각 줄의 앞뒤 공백을 제거한다
            # strip()은 줄바꿈 문자(\n)와 앞뒤 공백을 제거한다
            line = line.strip()
            # 빈 줄은 건너뛴다
            if not line:
                continue
            
            # tube 정보의 첫 번째 필드는 비디오명이다 (예: '--Y9imYnfBw_0000')
            # split(',')으로 콤마를 기준으로 분리하고 [0]으로 첫 번째 필드를 가져온다
            # strip()으로 앞뒤 공백을 제거한다
            tube_video_name = line.split(',')[0].strip()
            
            # tube의 비디오명이 현재 비디오 ID로 시작하는지 확인한다
            # startswith()는 문자열이 특정 문자열로 시작하는지 확인한다
            # 예) tube_video_name='--Y9imYnfBw_0000', video_id='--Y9imYnfBw'이면 True
            #     tube_video_name='-7TMJtnhiPM_0000', video_id='--Y9imYnfBw'이면 False
            if tube_video_name.startswith(video_id + '_'):
                # 조건을 만족하면 해당 tube 정보를 리스트에 추가한다
                tubes.append(line)
    
    # 해당 비디오의 모든 tube 정보를 반환한다
    return tubes


def delete_video_files(video_path):
    # 비디오 파일을 삭제하는 함수
    # video_path: 삭제할 비디오 파일 경로
    # 반환값: 성공 시 True, 실패 시 False
    
    try:
        # os.path.exists()는 파일이나 디렉토리가 존재하는지 확인한다
        if os.path.exists(video_path):
            # os.remove()는 파일을 삭제한다
            os.remove(video_path)
            print('Deleted: %s' % (os.path.basename(video_path)))
            return True
        else:
            # 파일이 없으면 삭제할 필요가 없다
            return True
    except Exception as e:
        # 삭제 실패 시 에러 메시지를 출력한다
        print('Failed to delete %s: %s' % (video_path, str(e)))
        return False


def delete_split_clips(split_dir, video_id):
    # 특정 비디오 ID의 모든 분할된 클립을 삭제하는 함수
    # split_dir: 분할된 클립이 있는 디렉토리 경로
    # video_id: 비디오 ID (예: '--Y9imYnfBw')
    # 반환값: 삭제된 파일 개수
    
    # 삭제할 파일 패턴을 생성한다
    # glob.glob()은 와일드카드 패턴을 사용하여 파일을 찾는다
    # 예) split_dir='train/temp_1min_clips', video_id='--Y9imYnfBw'이면
    #     'train/temp_1min_clips/--Y9imYnfBw_*.mp4' 패턴으로 모든 분할된 클립을 찾는다
    pattern = os.path.join(split_dir, f'{video_id}_*.mp4')
    # glob.glob()은 매칭되는 모든 파일 경로를 리스트로 반환한다
    # 예) ['train/temp_1min_clips/--Y9imYnfBw_0000.mp4', 'train/temp_1min_clips/--Y9imYnfBw_0001.mp4', ...]
    files_to_delete = glob.glob(pattern)
    
    # 삭제된 파일 개수를 세는 변수
    deleted_count = 0
    
    # 각 파일을 삭제한다
    for file_path in files_to_delete:
        if delete_video_files(file_path):
            deleted_count += 1
    
    # 삭제된 파일 개수를 반환한다
    return deleted_count


if __name__ == '__main__':
    # 비디오 ID 리스트를 읽어온다
    # video_ids는 비디오 ID를 저장할 리스트이다
    # 빈 리스트로 초기화한다
    video_ids = []
    # video_ids_file을 열어서 각 줄을 읽어온다
    # open()은 파일을 열고, with 문을 사용하면 파일 읽기가 끝나면 자동으로 파일을 닫는다
    with open(args.video_ids_file, 'r') as fin:
        # 파일의 각 줄을 순회한다
        for line in fin:
            # 각 줄의 앞뒤 공백을 제거하고 리스트에 추가한다
            # strip()은 줄바꿈 문자(\n)와 앞뒤 공백을 제거한다
            video_id = line.strip()
            # 빈 줄은 건너뛴다
            if video_id:
                video_ids.append(video_id)
    
    # 출력 디렉토리와 임시 디렉토리들을 생성한다
    # os.makedirs()는 디렉토리를 생성한다
    # exist_ok=True는 디렉토리가 이미 존재해도 오류를 발생시키지 않는다
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.temp_raw_dir, exist_ok=True)
    os.makedirs(args.temp_split_dir, exist_ok=True)
    
    # 전체 시작 시간을 기록한다
    # timer()는 현재 시간을 초 단위로 반환한다
    total_start = timer()
    
    # 각 비디오에 대해 순차적으로 처리한다
    # tqdm()은 진행률 표시줄을 보여준다
    # total=len(video_ids)는 전체 작업 개수를 지정하여 진행률을 정확히 계산한다
    for video_id in tqdm(video_ids, desc='Processing videos'):
        # 현재 비디오의 시작 시간을 기록한다
        video_start = timer()
        
        print('\n=== Processing video: %s ===' % (video_id))
        
        # 1. 비디오 다운로드
        # download_video() 함수를 호출하여 비디오를 다운로드한다
        # temp_raw_dir에 원본 비디오가 저장된다
        video_path = download_video(args.temp_raw_dir, video_id)
        
        # 다운로드가 실패하면 다음 비디오로 넘어간다
        # video_path가 None이면 다운로드 실패를 의미한다
        if video_path is None:
            print('Skipping video %s due to download failure' % (video_id))
            continue
        
        # 2. 비디오를 1분 단위로 분할
        # split_video() 함수를 호출하여 비디오를 1분 단위로 분할한다
        # temp_split_dir에 분할된 비디오들이 저장된다
        if not split_video(video_path, args.temp_split_dir):
            print('Skipping video %s due to split failure' % (video_id))
            # 분할 실패 시 원본 비디오를 삭제할지 결정한다
            # delete_temp가 'on'이면 원본 비디오도 삭제한다
            if args.delete_temp == 'on':
                delete_video_files(video_path)
            continue
        
        # 3. 해당 비디오의 tube 정보를 가져온다
        # get_tubes_for_video() 함수를 호출하여 해당 비디오 ID로 시작하는 모든 tube 정보를 가져온다
        # 예) video_id='--Y9imYnfBw'이면 '--Y9imYnfBw_0000', '--Y9imYnfBw_0001' 등의 tube 정보를 가져온다
        tubes = get_tubes_for_video(args.tubes_file, video_id)
        
        # tube 정보가 없으면 크롭할 것이 없으므로 다음 비디오로 넘어간다
        if not tubes:
            print('No tubes found for video %s' % (video_id))
            # delete_temp가 'on'이면 임시 파일들을 삭제한다
            if args.delete_temp == 'on':
                delete_video_files(video_path)
                delete_split_clips(args.temp_split_dir, video_id)
            continue
        
        print('Found %d tubes for video %s' % (len(tubes), video_id))
        
        # 4. 크롭 작업을 수행한다
        # trim_and_crop_min_size 함수를 사용하여 크롭 작업을 수행한다
        # partial()은 함수의 일부 인자를 고정하여 새로운 함수를 만드는 함수이다
        # trim_and_crop_min_size 함수의 첫 번째, 두 번째, 네 번째, 다섯 번째 인자(input_dir, output_dir, min_crop_width, min_crop_height)를 고정하고
        # 세 번째 인자(clip_params)만 받는 새로운 함수를 만든다
        # 이렇게 하면 multiprocessing에서 각 tube 정보만 전달하면 된다
        cropper = partial(trim_and_crop_min_size, args.temp_split_dir, args.output_dir, 
                         min_crop_width=args.min_crop_width, min_crop_height=args.min_crop_height)
        
        # 멀티프로세싱을 사용하여 크롭 작업을 수행한다
        # mp.Pool()은 프로세스 풀을 생성한다
        # processes=args.num_workers는 풀에 포함될 프로세스의 개수를 지정한다
        # with 문을 사용하면 작업이 끝나면 자동으로 풀을 종료한다
        import multiprocessing as mp
        with mp.Pool(processes=args.num_workers) as p:
            # imap_unordered()는 각 tube 정보를 cropper 함수에 전달하여 비동기적으로 실행한다
            # imap_unordered는 결과를 순서와 관계없이 반환한다 (처리 순서가 중요하지 않을 때 사용)
            # cropper는 각 tube 정보를 받아서 trim_and_crop_min_size 함수를 실행한다
            # list()로 감싸면 모든 작업이 완료될 때까지 대기한다
            _ = list(p.imap_unordered(cropper, tubes))
        
        print('Cropped %d clips for video %s' % (len(tubes), video_id))
        
        # 5. 임시 파일 삭제 (delete_temp가 'on'인 경우)
        # delete_temp가 'on'이면 원본 비디오와 분할된 클립들을 삭제한다
        if args.delete_temp == 'on':
            # 원본 비디오를 삭제한다
            delete_video_files(video_path)
            # 분할된 클립들을 삭제한다
            deleted_count = delete_split_clips(args.temp_split_dir, video_id)
            print('Deleted %d temporary files for video %s' % (deleted_count + 1, video_id))
        
        # 현재 비디오 처리 시간을 출력한다
        # timer() - video_start는 현재 시간에서 비디오 시작 시간을 빼서 경과 시간을 계산한다
        # %.2f는 소수점 둘째 자리까지 표시하는 포맷팅이다
        video_elapsed = timer() - video_start
        print('Completed video %s in %.2f seconds' % (video_id, video_elapsed))
    
    # 전체 처리 시간을 출력한다
    # timer() - total_start는 현재 시간에서 전체 시작 시간을 빼서 경과 시간을 계산한다
    total_elapsed = timer() - total_start
    print('\n=== Total elapsed time: %.2f seconds ===' % (total_elapsed))

