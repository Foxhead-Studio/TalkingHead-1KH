# import argparse  # 명령행 인자를 파싱하기 위한 argparse 모듈 임포트
# import multiprocessing as mp  # 멀티프로세싱을 위한 모듈 임포트
# import os  # OS 관련 작업을 위한 모듈 임포트
# from functools import partial  # 함수 인자를 고정시켜 새로운 함수 생성을 위한 partial 임포트
# from time import time as timer  # 시간 측정을 위해 time의 time 함수를 timer로 임포트

# # from pytube import YouTube  # (주석처리) pytube 라이브러리에서 YouTube 객체 임포트
# from pytubefix import YouTube  # pytubefix 라이브러리에서 YouTube 객체 임포트
# from tqdm import tqdm  # 진행바를 보여주는 tqdm 임포트

# parser = argparse.ArgumentParser()  # ArgumentParser 객체를 생성
# parser.add_argument('--input_list', type=str, required=True,
#                     help='List of youtube video ids')  # input_list 인자 추가
# parser.add_argument('--output_dir', type=str, default='data/youtube_videos',
#                     help='Location to download videos')  # output_dir 인자 추가
# parser.add_argument('--num_workers', type=int, default=8,
#                     help='How many multiprocessing workers?')  # num_workers 인자 추가
# args = parser.parse_args()  # 인자를 파싱해서 args에 저장

# def download_video(output_dir, video_id):  # 비디오를 다운로드하는 함수 정의
#     r"""Download video."""  # 함수의 docstring
#     video_path = '%s/%s.mp4' % (output_dir, video_id)  # 저장될 비디오 파일 경로 생성 'small/raw_videos/--Y9imYnfBw.mp4'
#     if not os.path.isfile(video_path):  # 파일이 이미 존재하지 않을 경우
#         try:
#             # Download the highest quality mp4 stream.  # (설명) 가장 높은 화질의 mp4 스트림 다운로드
#             yt = YouTube('https://www.youtube.com/watch?v=%s' % (video_id))  # 해당 video_id로 YouTube 객체 생성
#             # stream = yt.streams.filter(subtype='mp4', only_video=True, adaptive=True).first() # 음성 제외 비디오만 다운
#             stream = yt.streams.filter(subtype='mp4', progressive=True, adaptive=True).first() # 음성 포함 비디오 다운
#             if stream is None:  # 해당 조건에 맞는 stream이 없을 경우
#                 stream = yt.streams.filter(subtype='mp4').first()  # mp4 타입 중 첫 번째 stream 선택
#             stream.download(output_path=output_dir, filename=video_id + '.mp4')  # 비디오 다운로드 실행
#         except Exception as e:  # 예외 발생 시
#             print(e)  # 에러 메시지 출력
#             print('Failed to download %s' % (video_id))  # 다운로드 실패 메시지 출력
#     else:
#         print('File exists: %s' % (video_id))  # 파일이 이미 존재한다고 출력

# if __name__ == '__main__':  # 메인 실행부
#     # Read list of videos.  # (설명) 비디오 리스트 읽기
#     video_ids = []  # 비디오 아이디를 저장할 리스트 생성
#     with open(args.input_list) as fin:  # input_list 파일 열기
#         for line in fin:  # 한 줄씩 읽기
#             video_ids.append(line.strip())  # 줄 끝의 공백 제거 후 리스트에 추가
#     # video_ids = ['--Y9imYnfBw', '-7TMJtnhiPM']
#     # Create output folder.  # (설명) 출력 폴더 생성
#     os.makedirs(args.output_dir, exist_ok=True)  # 출력 폴더가 없으면 생성

#     # Download videos.  # (설명) 비디오 다운로드 실행
#     downloader = partial(download_video, args.output_dir)  # output_dir를 고정시킨 download_video 함수 생성

#     start = timer()  # 시작 시간 기록
#     pool_size = args.num_workers  # 사용할 워커(프로세스) 수 저장
#     print('Using pool size of %d' % (pool_size))  # 풀 사이즈 출력
#     with mp.Pool(processes=pool_size) as p:  # 멀티프로세싱 풀 생성
#         _ = list(tqdm(p.imap_unordered(downloader, video_ids), total=len(video_ids)))  # tqdm 진행바 사용해서 멀티프로세싱으로 다운로드 실행
#     print('Elapsed time: %.2f' % (timer() - start))  # 전체 실행에 걸린 시간 출력

# import argparse
# import multiprocessing as mp
# import os
# from functools import partial
# from time import time as timer

# from yt_dlp import YoutubeDL

# def download_video(output_dir, video_id, cookie_file):
#     url = f'https://www.youtube.com/watch?v={video_id}'
#     output_path = os.path.join(output_dir, f'{video_id}.mp4')
#     if os.path.isfile(output_path):
#         print(f'File exists: {video_id}')
#         return

#     ydl_opts = {
#         'outtmpl': output_path,
#         'cookiefile': cookie_file,
#         'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
#         'merge_output_format': 'mp4',
#         # 아래 옵션들은 필요에 따라 추가 가능
#         # 'retries': 3,
#         # 'sleep_interval': 1,
#         # 'max_sleep_interval': 5,
#     }

#     try:
#         with YoutubeDL(ydl_opts) as ydl:
#             ydl.download([url])
#     except Exception as e:
#         print(f'Error downloading {video_id}: {e}')

# def main():
#     parser = argparse.ArgumentParser()
#     parser.add_argument('--input_list', type=str, required=True,
#                         help='List of youtube video ids (one per line)')
#     parser.add_argument('--output_dir', type=str, default='data/youtube_videos',
#                         help='Directory to save downloaded videos')
#     parser.add_argument('--cookies', type=str, default='www.youtube.com_cookies.txt',
#                         help='Path to cookies.txt for logged-in session')
#     parser.add_argument('--num_workers', type=int, default=8,
#                         help='Number of parallel workers for download')
#     args = parser.parse_args()

#     os.makedirs(args.output_dir, exist_ok=True)

#     with open(args.input_list, 'r') as f:
#         video_ids = [line.strip() for line in f if line.strip()]

#     downloader = partial(download_video, args.output_dir, cookie_file=args.cookies)

#     print('Using pool size of', args.num_workers)
#     start = timer()
#     with mp.Pool(processes=args.num_workers) as pool:
#         list(pool.imap_unordered(downloader, video_ids))
#     elapsed = timer() - start
#     print(f'Elapsed time: {elapsed:.2f} sec')

# if __name__ == '__main__':
#     main()

# import argparse
# import multiprocessing as mp
# import os
# from functools import partial
# from time import time as timer

# from yt_dlp import YoutubeDL


# def log_line(log_file, text):
#     """간단한 로그 함수. 여러 프로세스가 동시에 써도 append면 거의 안전하다."""
#     if log_file is None:
#         return
#     # 한 줄씩만 쓰기 때문에 append는 원자적으로 처리되는 편이다.
#     with open(log_file, "a", encoding="utf-8") as f:
#         f.write(text + "\n")


# def download_video(output_dir, video_id, cookie_file, log_file):
#     """
#     output_dir   : 저장 디렉토리
#     video_id     : 유튜브 영상 ID
#     cookie_file  : www.youtube.com_cookies.txt 경로
#     log_file     : 로그를 남길 txt 파일 경로
#     반환값       : "ok" | "exists" | "fail"
#     """
#     url = f"https://www.youtube.com/watch?v={video_id}"
#     output_path = os.path.join(output_dir, f"{video_id}.mp4")

#     # 이미 파일이 있으면 스킵
#     if os.path.isfile(output_path):
#         msg = f"EXISTS\t{video_id}\t{output_path}"
#         print(msg)
#         log_line(log_file, msg)
#         return "exists"

#     ydl_opts = {
#         "outtmpl": output_path,
#         "cookiefile": cookie_file,
#         "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
#         "merge_output_format": "mp4",

#         # 오류 관련 옵션들
#         "retries": 5,               # 네트워크 오류 재시도
#         "fragment_retries": 5,      # 조각 다운로드 재시도
#         "ignoreerrors": True,       # 한 영상 실패해도 전체는 계속 진행

#         # 필요하면 로그를 줄이고 싶을 때 사용
#         # "quiet": True,
#         # "no_warnings": True,
#     }

#     print(f"Downloading {video_id} -> {output_path}")
#     log_line(log_file, f"START\t{video_id}\t{url}")

#     try:
#         with YoutubeDL(ydl_opts) as ydl:
#             ydl.download([url])
#     except Exception as e:
#         # yt-dlp 내부 DownloadError 등
#         err_str = str(e)
#         reason = "ERROR"

#         # 자주 등장하는 패턴들을 구분해서 적어준다
#         if "Private video" in err_str:
#             reason = "PRIVATE"
#         elif "Sign in to confirm you’re not a bot" in err_str or \
#              "Sign in to confirm you're not a bot" in err_str:
#             reason = "BOT_CHECK"
#         elif "This video is unavailable" in err_str:
#             reason = "UNAVAILABLE"

#         msg = f"FAIL\t{video_id}\t{reason}\t{err_str}"
#         print(msg)
#         log_line(log_file, msg)
#         return "fail"

#     # 예외는 없었는데도 파일이 안 생겼을 때를 한 번 더 체크
#     if os.path.isfile(output_path):
#         msg = f"OK\t{video_id}\t{output_path}"
#         print(msg)
#         log_line(log_file, msg)
#         return "ok"
#     else:
#         msg = f"FAIL\t{video_id}\tNO_FILE_CREATED"
#         print(msg)
#         log_line(log_file, msg)
#         return "fail"


# def main():
#     parser = argparse.ArgumentParser()
#     parser.add_argument(
#         "--input_list", type=str, required=True,
#         help="List of youtube video ids (one per line)"
#     )
#     parser.add_argument(
#         "--output_dir", type=str, default="data/youtube_videos",
#         help="Directory to save downloaded videos"
#     )
#     parser.add_argument(
#         "--cookies", type=str, default="www.youtube.com_cookies.txt",
#         help="Path to cookies.txt for logged-in session"
#     )
#     parser.add_argument(
#         "--num_workers", type=int, default=8,
#         help="Number of parallel workers for download"
#     )
#     parser.add_argument(
#         "--log_file", type=str, default="videos_download.log",
#         help="Path to log file for successes/failures"
#     )
#     args = parser.parse_args()

#     os.makedirs(args.output_dir, exist_ok=True)

#     with open(args.input_list, "r", encoding="utf-8") as f:
#         video_ids = [line.strip() for line in f if line.strip()]

#     # 시작할 때 로그 헤더 한 줄 써두기
#     log_line(args.log_file, f"# START DOWNLOAD | input={args.input_list} | "
#                             f"output_dir={args.output_dir}")

#     downloader = partial(
#         download_video,
#         args.output_dir,
#         cookie_file=args.cookies,
#         log_file=args.log_file,
#     )

#     print("Using pool size of", args.num_workers)
#     start = timer()
#     with mp.Pool(processes=args.num_workers) as pool:
#         results = list(pool.imap_unordered(downloader, video_ids))
#     elapsed = timer() - start

#     # 요약
#     ok_cnt = sum(1 for r in results if r == "ok")
#     exist_cnt = sum(1 for r in results if r == "exists")
#     fail_cnt = sum(1 for r in results if r == "fail")

#     summary = (f"SUMMARY\tOK={ok_cnt}\tEXISTS={exist_cnt}\tFAIL={fail_cnt}\t"
#                f"TOTAL={len(video_ids)}\tELAPSED={elapsed:.2f}s")
#     print(summary)
#     log_line(args.log_file, summary)


# if __name__ == "__main__":
#     main()

# import argparse
# import multiprocessing as mp
# import os
# import random
# import time
# from functools import partial
# from time import time as timer

# from yt_dlp import YoutubeDL


# def log_line(log_file, text):
#     """로그 한 줄 쓰기."""
#     if not log_file:
#         return
#     with open(log_file, "a", encoding="utf-8") as f:
#         f.write(text + "\n")


# def download_video(output_dir, video_id, cookie_file,
#                    log_file, sleep_min, sleep_max):
#     """
#     output_dir : 저장 디렉토리
#     video_id   : 유튜브 영상 ID
#     cookie_file: cookies.txt 경로
#     log_file   : 로그 파일 경로
#     sleep_min, sleep_max : 각 영상 시작 전 랜덤 딜레이 구간(초)
#     반환값: "ok" | "exists" | "fail"
#     """
#     url = f"https://www.youtube.com/watch?v={video_id}"
#     output_path = os.path.join(output_dir, f"{video_id}.mp4")

#     # 이미 있으면 스킵
#     if os.path.isfile(output_path):
#         msg = f"EXISTS\t{video_id}\t{output_path}"
#         print(msg)
#         log_line(log_file, msg)
#         return "exists"

#     # 각 작업 시작 전에 랜덤 딜레이
#     if sleep_max > 0:
#         delay = random.uniform(max(0.0, sleep_min), sleep_max)
#         if delay > 0:
#             time.sleep(delay)

#     ydl_opts = {
#         "outtmpl": output_path,
#         "cookiefile": cookie_file,
#         "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
#         "merge_output_format": "mp4",

#         # 일시적인 네트워크 오류용 재시도
#         "retries": 5,
#         "fragment_retries": 5,

#         # 각 영상 사이에 추가 딜레이(yt-dlp 내부)
#         # (0이면 비활성)
#         "sleep_interval": sleep_min if sleep_min > 0 else 0,
#         "max_sleep_interval": sleep_max if sleep_max > 0 else 0,
#     }

#     print(f"Downloading {video_id} -> {output_path}")
#     log_line(log_file, f"START\t{video_id}\t{url}")

#     try:
#         with YoutubeDL(ydl_opts) as ydl:
#             ydl.download([url])
#     except Exception as e:
#         err_str = str(e)
#         err_low = err_str.lower()

#         reason = "ERROR"
#         if "private video" in err_str:
#             reason = "PRIVATE"
#         elif "rate-limited" in err_low or "rate limited" in err_low:
#             reason = "RATE_LIMIT"
#         elif "this content isn't available, try again later" in err_low:
#             reason = "UNAVAILABLE"
#         elif "sign in to confirm you’re not a bot" in err_str or \
#              "sign in to confirm you're not a bot" in err_str:
#             reason = "BOT_CHECK"

#         msg = f"FAIL\t{video_id}\t{reason}\t{err_str}"
#         print(msg)
#         log_line(log_file, msg)
#         return "fail"

#     # 예외는 안 났는데 파일이 없으면 실패로 처리
#     if os.path.isfile(output_path):
#         msg = f"OK\t{video_id}\t{output_path}"
#         print(msg)
#         log_line(log_file, msg)
#         return "ok"
#     else:
#         msg = f"FAIL\t{video_id}\tNO_FILE_CREATED"
#         print(msg)
#         log_line(log_file, msg)
#         return "fail"


# def main():
#     parser = argparse.ArgumentParser()
#     parser.add_argument(
#         "--input_list", type=str, required=True,
#         help="List of youtube video ids (one per line)"
#     )
#     parser.add_argument(
#         "--output_dir", type=str, default="data/youtube_videos",
#         help="Directory to save downloaded videos"
#     )
#     parser.add_argument(
#         "--cookies", type=str, default="www.youtube.com_cookies.txt",
#         help="Path to cookies.txt for logged-in session"
#     )
#     parser.add_argument(
#         "--num_workers", type=int, default=2,
#         help="Number of parallel workers for download"
#     )
#     parser.add_argument(
#         "--log_file", type=str, default="videos_download.log",
#         help="Path to log file for successes/failures"
#     )
#     parser.add_argument(
#         "--sleep_min", type=float, default=1.0,
#         help="Min random sleep (sec) before each download"
#     )
#     parser.add_argument(
#         "--sleep_max", type=float, default=3.0,
#         help="Max random sleep (sec) before each download"
#     )
#     args = parser.parse_args()

#     os.makedirs(args.output_dir, exist_ok=True)

#     with open(args.input_list, "r", encoding="utf-8") as f:
#         video_ids = [line.strip() for line in f if line.strip()]

#     log_line(args.log_file,
#              f"# START DOWNLOAD | input={args.input_list} | "
#              f"output_dir={args.output_dir}")

#     downloader = partial(
#         download_video,
#         args.output_dir,
#         cookie_file=args.cookies,
#         log_file=args.log_file,
#         sleep_min=args.sleep_min,
#         sleep_max=args.sleep_max,
#     )

#     print("Using pool size of", args.num_workers)
#     start = timer()
#     with mp.Pool(processes=args.num_workers) as pool:
#         results = list(pool.imap_unordered(downloader, video_ids))
#     elapsed = timer() - start

#     ok_cnt = sum(1 for r in results if r == "ok")
#     exist_cnt = sum(1 for r in results if r == "exists")
#     fail_cnt = sum(1 for r in results if r == "fail")

#     summary = (f"SUMMARY\tOK={ok_cnt}\tEXISTS={exist_cnt}\tFAIL={fail_cnt}\t"
#                f"TOTAL={len(video_ids)}\tELAPSED={elapsed:.2f}s")
#     print(summary)
#     log_line(args.log_file, summary)


# if __name__ == "__main__":
#     main()

# 실행 명령어: python videos_download.py --input_list data_list/train_video_ids_340x340_12s.txt --output_dir train/raw_videos --cookies www.youtube.com_cookies.txt --sleep_min 15 --sleep_max 40

import argparse
import os
import random
import time
from time import time as timer
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

def log_line(log_file, text):
    """로그 한 줄 쓰기."""
    if not log_file:
        return
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(text + "\n")

def download_video_sequential(output_dir, video_id, cookie_file, log_file, sleep_min, sleep_max):
    """
    순차 다운로드 함수
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    output_path = os.path.join(output_dir, f"{video_id}.mp4")

    # 이미 있으면 스킵
    if os.path.isfile(output_path):
        msg = f"EXISTS\t{video_id}\t{output_path}"
        print(msg)
        log_line(log_file, msg)
        return "exists"

    # 다운로드 전 랜덤 딜레이 (사람처럼 보이기 위함)
    if sleep_max > 0:
        delay = random.uniform(sleep_min, sleep_max)
        print(f"Sleeping for {delay:.2f} seconds...")
        time.sleep(delay)

    ydl_opts = {
        "outtmpl": output_path,
        # 쿠키 파일이 없으면 None 처리 (필요 없으면 인자에서 빼는 게 좋음)
        "cookiefile": cookie_file if cookie_file and os.path.exists(cookie_file) else None,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        
        # 네트워크 오류 재시도
        "retries": 10,
        "fragment_retries": 10,
        
        # 상세 로그 끄기 (깔끔하게 보려면)
        "quiet": True,
        "no_warnings": True,
    }

    print(f"Downloading {video_id} -> {output_path}")
    log_line(log_file, f"START\t{video_id}\t{url}")

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        err_str = str(e)
        err_low = err_str.lower()
        reason = "ERROR"
        
        # Rate Limit 감지 시 매우 긴 대기 시간 필요
        if "rate-limited" in err_low or "429" in err_str:
            reason = "RATE_LIMIT"
            print("\n!!! RATE LIMIT DETECTED !!!")
            print("Sleeping for 5 minutes before trying next video...\n")
            time.sleep(300) # 5분 대기
        elif "private video" in err_low:
            reason = "PRIVATE"
        elif "unavailable" in err_low:
            reason = "UNAVAILABLE"
        elif "sign in" in err_low:
            reason = "LOGIN_REQUIRED"

        msg = f"FAIL\t{video_id}\t{reason}\t{err_str}"
        print(msg)
        log_line(log_file, msg)
        return "fail"

    if os.path.isfile(output_path):
        msg = f"OK\t{video_id}\t{output_path}"
        print(msg)
        log_line(log_file, msg)
        return "ok"
    else:
        msg = f"FAIL\t{video_id}\tNO_FILE_CREATED"
        print(msg)
        log_line(log_file, msg)
        return "fail"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_list", type=str, required=True)
    parser.add_argument("--output_dir", type=str, default="data/youtube_videos")
    parser.add_argument("--cookies", type=str, default=None, help="Path to cookies.txt (Optional)")
    # num_workers 인자는 제거함 (순차 처리)
    parser.add_argument("--log_file", type=str, default="videos_download.log")
    
    # 딜레이 기본값을 늘림
    parser.add_argument("--sleep_min", type=float, default=5.0) 
    parser.add_argument("--sleep_max", type=float, default=15.0)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    with open(args.input_list, "r", encoding="utf-8") as f:
        video_ids = [line.strip() for line in f if line.strip()]

    log_line(args.log_file, f"# START DOWNLOAD | input={args.input_list}")

    ok_cnt = 0
    exist_cnt = 0
    fail_cnt = 0
    
    start_total = timer()

    for i, vid in enumerate(video_ids):
        print(f"[{i+1}/{len(video_ids)}] Processing {vid}...")
        result = download_video_sequential(
            args.output_dir, 
            vid, 
            args.cookies, 
            args.log_file, 
            args.sleep_min, 
            args.sleep_max
        )
        
        if result == "ok": ok_cnt += 1
        elif result == "exists": exist_cnt += 1
        else: fail_cnt += 1

    elapsed = timer() - start_total
    summary = (f"SUMMARY\tOK={ok_cnt}\tEXISTS={exist_cnt}\tFAIL={fail_cnt}\t"
               f"TOTAL={len(video_ids)}\tELAPSED={elapsed:.2f}s")
    print("\n" + summary)
    log_line(args.log_file, summary)

if __name__ == "__main__":
    main()