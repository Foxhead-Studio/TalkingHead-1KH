import argparse  # 명령행 인자를 파싱하기 위한 argparse 모듈 임포트
import multiprocessing as mp  # 멀티프로세싱을 위한 모듈 임포트
import os  # OS 관련 작업을 위한 모듈 임포트
from functools import partial  # 함수 인자를 고정시켜 새로운 함수 생성을 위한 partial 임포트
from time import time as timer  # 시간 측정을 위해 time의 time 함수를 timer로 임포트

# from pytube import YouTube  # (주석처리) pytube 라이브러리에서 YouTube 객체 임포트
from pytubefix import YouTube  # pytubefix 라이브러리에서 YouTube 객체 임포트
from tqdm import tqdm  # 진행바를 보여주는 tqdm 임포트

parser = argparse.ArgumentParser()  # ArgumentParser 객체를 생성
parser.add_argument('--input_list', type=str, required=True,
                    help='List of youtube video ids')  # input_list 인자 추가
parser.add_argument('--output_dir', type=str, default='data/youtube_videos',
                    help='Location to download videos')  # output_dir 인자 추가
parser.add_argument('--num_workers', type=int, default=8,
                    help='How many multiprocessing workers?')  # num_workers 인자 추가
args = parser.parse_args()  # 인자를 파싱해서 args에 저장

def download_video(output_dir, video_id):  # 비디오를 다운로드하는 함수 정의
    r"""Download video."""  # 함수의 docstring
    video_path = '%s/%s.mp4' % (output_dir, video_id)  # 저장될 비디오 파일 경로 생성 'small/raw_videos/--Y9imYnfBw.mp4'
    if not os.path.isfile(video_path):  # 파일이 이미 존재하지 않을 경우
        try:
            # Download the highest quality mp4 stream.  # (설명) 가장 높은 화질의 mp4 스트림 다운로드
            yt = YouTube('https://www.youtube.com/watch?v=%s' % (video_id))  # 해당 video_id로 YouTube 객체 생성
            # stream = yt.streams.filter(subtype='mp4', only_video=True, adaptive=True).first() # 음성 제외 비디오만 다운
            stream = yt.streams.filter(subtype='mp4', progressive=True, adaptive=True).first() # 음성 포함 비디오 다운
            if stream is None:  # 해당 조건에 맞는 stream이 없을 경우
                stream = yt.streams.filter(subtype='mp4').first()  # mp4 타입 중 첫 번째 stream 선택
            stream.download(output_path=output_dir, filename=video_id + '.mp4')  # 비디오 다운로드 실행
        except Exception as e:  # 예외 발생 시
            print(e)  # 에러 메시지 출력
            print('Failed to download %s' % (video_id))  # 다운로드 실패 메시지 출력
    else:
        print('File exists: %s' % (video_id))  # 파일이 이미 존재한다고 출력

if __name__ == '__main__':  # 메인 실행부
    # Read list of videos.  # (설명) 비디오 리스트 읽기
    video_ids = []  # 비디오 아이디를 저장할 리스트 생성
    with open(args.input_list) as fin:  # input_list 파일 열기
        for line in fin:  # 한 줄씩 읽기
            video_ids.append(line.strip())  # 줄 끝의 공백 제거 후 리스트에 추가
    # video_ids = ['--Y9imYnfBw', '-7TMJtnhiPM']
    # Create output folder.  # (설명) 출력 폴더 생성
    os.makedirs(args.output_dir, exist_ok=True)  # 출력 폴더가 없으면 생성

    # Download videos.  # (설명) 비디오 다운로드 실행
    downloader = partial(download_video, args.output_dir)  # output_dir를 고정시킨 download_video 함수 생성

    start = timer()  # 시작 시간 기록
    pool_size = args.num_workers  # 사용할 워커(프로세스) 수 저장
    print('Using pool size of %d' % (pool_size))  # 풀 사이즈 출력
    with mp.Pool(processes=pool_size) as p:  # 멀티프로세싱 풀 생성
        _ = list(tqdm(p.imap_unordered(downloader, video_ids), total=len(video_ids)))  # tqdm 진행바 사용해서 멀티프로세싱으로 다운로드 실행
    print('Elapsed time: %.2f' % (timer() - start))  # 전체 실행에 걸린 시간 출력
