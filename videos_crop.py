# Copyright (c) 2022, NVIDIA CORPORATION. All rights reserved.
#
# This script is licensed under the MIT License.

import argparse
import multiprocessing as mp
import os
from functools import partial
from time import time as timer

import ffmpeg
from tqdm import tqdm


parser = argparse.ArgumentParser()
parser.add_argument('--input_dir', type=str, required=True,
                    help='Dir containing youtube clips.')
parser.add_argument('--clip_info_file', type=str, required=True,
                    help='File containing clip information.')
parser.add_argument('--output_dir', type=str, required=True,
                    help='Location to dump outputs.')
parser.add_argument('--num_workers', type=int, default=8,
                    help='How many multiprocessing workers?')
parser.add_argument('--min_crop_width', type=int, default=256,
                    help='Minimum crop width in pixels. Only videos with crop width >= this value will be processed.')
parser.add_argument('--min_crop_height', type=int, default=256,
                    help='Minimum crop height in pixels. Only videos with crop height >= this value will be processed.')
args = parser.parse_args()


def get_h_w(filepath):
    probe = ffmpeg.probe(filepath)
    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    height = int(video_stream['height'])
    width = int(video_stream['width'])
    return height, width


def get_fps(filepath):
    # 비디오 파일의 fps(초당 프레임 수)를 가져온다
    # ffmpeg.probe()로 비디오 파일의 메타데이터를 읽어온다
    probe = ffmpeg.probe(filepath)
    # 비디오 스트림을 찾는다
    # codec_type이 'video'인 스트림을 찾아서 video_stream에 저장한다
    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    # fps를 계산한다
    # r_frame_rate는 "30/1" 같은 문자열 형식으로 저장되어 있다
    # 이를 분자와 분모로 나눠서 실제 fps 값을 계산한다
    # 예) "30/1" → 30.0, "29.97/1" → 29.97
    r_frame_rate = video_stream['r_frame_rate']
    num, den = map(int, r_frame_rate.split('/'))
    fps = num / den if den > 0 else 30.0  # 분모가 0이면 기본값 30.0 사용
    return fps


def trim_and_crop(input_dir, output_dir, clip_params):
    # 예시 clip_params: '--Y9imYnfBw_0000, 720, 1280, 0, 271, 504, 63, 792, 351'
    # 각 항목의 의미를 설명하면 아래와 같다:
    #   video_name: '--Y9imYnfBw_0000'
    #   H: 720          # 원본 영상의 height (세로 픽셀 수)
    #   W: 1280         # 원본 영상의 width (가로 픽셀 수)
    #   S: 0            # 시작 프레임 번호
    #   E: 271          # 끝 프레임 번호
    #   L: 504          # crop할 영역의 left 좌표 (픽셀, 원본 기준)
    #   T: 63           # crop할 영역의 top 좌표 (픽셀, 원본 기준)
    #   R: 792          # crop할 영역의 right 좌표 (픽셀, 원본 기준)
    #   B: 351          # crop할 영역의 bottom 좌표 (픽셀, 원본 기준)
    
    # clip_params 문자열(콤마로 구분된 값들)을 파싱해서 각각의 변수로 나눈다.
    video_name, H, W, S, E, L, T, R, B = clip_params.strip().split(',')

    # H, W, S, E, L, T, R, B를 문자열에서 정수(int)로 변환한다.
    # 예) H=720, W=1280, S=0, E=271, L=504, T=63, R=792, B=351
    H, W, S, E, L, T, R, B = int(H), int(W), int(S), int(E), int(L), int(T), int(R), int(B)
    
    # 출력 파일명을 지정한다.
    # 예) '--Y9imYnfBw_0000_S0_E271_L504_T63_R792_B351.mp4'
    output_filename = '{}_S{}_E{}_L{}_T{}_R{}_B{}.mp4'.format(video_name, S, E, L, T, R, B)
    output_filepath = os.path.join(output_dir, output_filename)

    # 만약 출력 파일이 이미 존재하면, 처리하지 않고 넘어간다(중복 방지).
    if os.path.exists(output_filepath):
        print('Output file %s exists, skipping' % (output_filepath))
        return

    # 입력 영상 파일 경로를 지정한다.
    # 예) input_dir이 'small/1min_clips', video_name='--Y9imYnfBw_0000'이면
    # 'small/1min_clips/--Y9imYnfBw_0000.mp4'가 input_filepath가 된다.
    input_filepath = os.path.join(input_dir, video_name + '.mp4')

    # 만약 입력 파일이 존재하지 않을 경우, 처리하지 않고 넘어간다.
    if not os.path.exists(input_filepath):
        print('Input file %s does not exist, skipping' % (input_filepath))
        return

    # 영상의 실제 height(h), width(w)를 ffmpeg.probe로 읽어온다.
    # 실제 영상 크기가 crop 정보와 다를 수 있으니(리사이즈 등), crop 좌표 보정을 위해 필요함.
    h, w = get_h_w(input_filepath)
    # 예시: h=720, w=1280 (일치하거나 다를 수 있음)
    # 비디오 파일의 fps(초당 프레임 수)를 가져온다
    # 오디오를 동일한 시간 범위로 trim하기 위해 fps가 필요하다
    # 예) fps=30이면 1초에 30프레임이다
    fps = get_fps(input_filepath)

    # crop 좌표를 실제 프레임에 맞게 보정한다.
    # 예) t = int(63 / 720 * 720) = 63
    #     b = int(351 / 720 * 720) = 351
    #     l = int(504 / 1280 * 1280) = 504
    #     r = int(792 / 1280 * 1280) = 792
    # (실제 h, w가 clip에서 온 H, W와 다르면 비례해서 변환)
    t = int(T / H * h)   # top 좌표, 예: 63
    b = int(B / H * h)   # bottom 좌표, 예: 351
    l = int(L / W * w)   # left 좌표, 예: 504
    r = int(R / W * w)   # right 좌표, 예: 792

    # ffmpeg 입력 스트림 생성
    # ffmpeg.input()은 비디오 파일을 입력 스트림으로 로드한다
    # input_filepath에 지정된 비디오 파일을 읽어온다
    input_stream = ffmpeg.input(input_filepath)
    # 비디오와 오디오 스트림을 분리한다
    # input_stream['v:0']은 첫 번째 비디오 스트림을 의미한다
    # input_stream['a:0']은 첫 번째 오디오 스트림을 의미한다 (오디오가 없는 경우 None일 수 있음)
    video = input_stream['v:0']
    # 오디오 스트림이 있는지 확인한다
    # try-except를 사용하여 오디오 스트림이 없을 경우를 처리한다
    try:
        audio = input_stream['a:0']
        has_audio = True
    except:
        has_audio = False
    
    # 비디오 스트림에 특정 프레임 구간만 자르기(trim)
    # ffmpeg.trim()의 start_frame/end_frame은 프레임 번호로 작동하지 않으므로 select 필터를 사용한다
    # select 필터의 between(n,S,E)는 n번째 프레임이 S와 E 사이(포함)에 있으면 선택한다
    # 예를 들어, S=1015, E=1107인 경우 1015~1107 프레임(총 93프레임)을 추출한다
    # setpts=PTS-STARTPTS는 선택된 프레임들의 타임스탬프를 0부터 시작하도록 재설정한다
    # stream = ffmpeg.trim(stream, start_frame=S, end_frame=E+1)  # 이 방법은 프레임 번호로 작동하지 않음
    video = video.filter('select', f'between(n,{S},{E})').filter('setpts', 'PTS-STARTPTS')
    # crop 적용 (좌상단 l,t, 너비 r-l, 높이 b-t로 자른다)
    # 예) l=504, t=63, r-l=288, b-t=288
    video = ffmpeg.crop(video, l, t, r-l, b-t)
    
    # 오디오 스트림도 동일한 시간 범위로 trim한다
    # 프레임 번호를 시간(초)으로 변환한다
    # start_time = S / fps는 시작 시간(초)이다
    # 예) S=1015, fps=30이면 start_time = 1015/30 = 33.83초
    # duration = (E - S + 1) / fps는 지속 시간(초)이다
    # 예) S=1015, E=1107, fps=30이면 duration = (1107-1015+1)/30 = 93/30 = 3.1초
    if has_audio:
        start_time = S / fps
        duration = (E - S + 1) / fps
        # atrim 필터는 오디오를 특정 시간 범위로 자른다
        # start=start_time은 시작 시간, duration=duration은 지속 시간이다
        # asetpts=PTS-STARTPTS는 오디오 타임스탬프를 0부터 시작하도록 재설정한다
        audio = audio.filter('atrim', start=start_time, duration=duration).filter('asetpts', 'PTS-STARTPTS')
    
    # 출력 파일로 저장할 스트림 설정
    # ffmpeg.output()은 처리된 스트림을 파일로 출력하도록 설정한다
    # output_filepath에 지정된 경로에 비디오 파일이 저장된다
    # 오디오가 있으면 비디오와 오디오를 모두 포함하고, 없으면 비디오만 포함한다
    if has_audio:
        stream = ffmpeg.output(video, audio, output_filepath)
    else:
        stream = ffmpeg.output(video, output_filepath)
    # 실제로 ffmpeg를 실행해 clip을 생성한다.
    # ffmpeg.run()은 설정된 ffmpeg 파이프라인을 실행하여 비디오 처리를 수행한다
    # 비디오가 성공적으로 생성되면 output_filepath에 파일이 저장된다
    ffmpeg.run(stream)


def trim_and_crop_min_size(input_dir, output_dir, clip_params, min_crop_width=256, min_crop_height=256):
    # trim_and_crop_min_size: 프레임 크기가 min_crop_width x min_crop_height 이상인 경우만 처리하는 함수
    # 입력 인자는 trim_and_crop과 동일하다
    # input_dir: 입력 비디오가 있는 디렉토리 경로
    # output_dir: 출력 비디오를 저장할 디렉토리 경로
    # clip_params: 비디오 클립 정보가 담긴 문자열 (콤마로 구분)
    # min_crop_width: 최소 crop 너비(픽셀), 이 값 이상인 경우만 처리한다
    # min_crop_height: 최소 crop 높이(픽셀), 이 값 이상인 경우만 처리한다
    
    # 예시 clip_params: '--Y9imYnfBw_0000, 720, 1280, 0, 271, 504, 63, 792, 351'
    # 각 항목의 의미는 trim_and_crop 함수와 동일하다
    #   video_name: '--Y9imYnfBw_0000'
    #   H: 720          # 원본 영상의 height (세로 픽셀 수)
    #   W: 1280         # 원본 영상의 width (가로 픽셀 수)
    #   S: 0            # 시작 프레임 번호
    #   E: 271          # 끝 프레임 번호
    #   L: 504          # crop할 영역의 left 좌표 (픽셀, 원본 기준)
    #   T: 63           # crop할 영역의 top 좌표 (픽셀, 원본 기준)
    #   R: 792          # crop할 영역의 right 좌표 (픽셀, 원본 기준)
    #   B: 351          # crop할 영역의 bottom 좌표 (픽셀, 원본 기준)
    
    # clip_params 문자열(콤마로 구분된 값들)을 파싱해서 각각의 변수로 나눈다
    # strip()은 앞뒤 공백을 제거하고, split(',')은 콤마를 기준으로 문자열을 분리한다
    # 예) '--Y9imYnfBw_0000, 720, 1280, 0, 271, 504, 63, 792, 351' → 
    #     ['--Y9imYnfBw_0000', ' 720', ' 1280', ' 0', ' 271', ' 504', ' 63', ' 792', ' 351']
    video_name, H, W, S, E, L, T, R, B = clip_params.strip().split(',')

    # H, W, S, E, L, T, R, B를 문자열에서 정수(int)로 변환한다
    # 각 변수는 앞뒤 공백이 있을 수 있으므로 int() 변환 시 자동으로 처리된다
    # 예) H=720, W=1280, S=0, E=271, L=504, T=63, R=792, B=351
    H, W, S, E, L, T, R, B = int(H), int(W), int(S), int(E), int(L), int(T), int(R), int(B)
    
    # 출력 파일명을 지정한다
    # format() 메서드를 사용하여 파일명에 각 파라미터 값을 삽입한다
    # 예) '--Y9imYnfBw_0000_S0_E271_L504_T63_R792_B351.mp4'
    output_filename = '{}_S{}_E{}_L{}_T{}_R{}_B{}.mp4'.format(video_name, S, E, L, T, R, B)
    # os.path.join()을 사용하여 출력 디렉토리와 파일명을 결합한다
    # 예) output_dir='small/cropped_clips', output_filename='--Y9imYnfBw_0000_S0_E271_L504_T63_R792_B351.mp4'
    #     → 'small/cropped_clips/--Y9imYnfBw_0000_S0_E271_L504_T63_R792_B351.mp4'
    output_filepath = os.path.join(output_dir, output_filename)

    # 만약 출력 파일이 이미 존재하면, 처리하지 않고 넘어간다(중복 방지)
    # os.path.exists()는 파일이나 디렉토리가 존재하는지 확인한다
    # 이미 처리된 파일은 다시 처리하지 않아 시간을 절약한다
    if os.path.exists(output_filepath):
        # 출력 파일이 존재한다는 메시지를 출력한다
        # %s는 문자열 포맷팅으로, output_filepath 값이 삽입된다
        print('Output file %s exists, skipping' % (output_filepath))
        # 함수를 종료하고 다음 클립으로 넘어간다
        return

    # 입력 영상 파일 경로를 지정한다
    # os.path.join()을 사용하여 입력 디렉토리와 비디오 파일명을 결합한다
    # video_name에 '.mp4' 확장자를 추가한다
    # 예) input_dir이 'small/1min_clips', video_name='--Y9imYnfBw_0000'이면
    #     'small/1min_clips/--Y9imYnfBw_0000.mp4'가 input_filepath가 된다
    input_filepath = os.path.join(input_dir, video_name + '.mp4')

    # 만약 입력 파일이 존재하지 않을 경우, 처리하지 않고 넘어간다
    # not os.path.exists()는 파일이 존재하지 않으면 True를 반환한다
    # 파일이 없으면 처리할 수 없으므로 건너뛴다
    if not os.path.exists(input_filepath):
        # 입력 파일이 존재하지 않는다는 메시지를 출력한다
        # %s는 문자열 포맷팅으로, input_filepath 값이 삽입된다
        print('Input file %s does not exist, skipping' % (input_filepath))
        # 함수를 종료하고 다음 클립으로 넘어간다
        return

    # 영상의 실제 height(h), width(w)를 ffmpeg.probe로 읽어온다
    # get_h_w() 함수는 ffmpeg.probe를 사용하여 비디오 파일의 실제 해상도를 가져온다
    # 실제 영상 크기가 crop 정보와 다를 수 있으니(리사이즈 등), crop 좌표 보정을 위해 필요함
    # 예시: h=720, w=1280 (일치하거나 다를 수 있음)
    h, w = get_h_w(input_filepath)
    # 비디오 파일의 fps(초당 프레임 수)를 가져온다
    # 오디오를 동일한 시간 범위로 trim하기 위해 fps가 필요하다
    # 예) fps=30이면 1초에 30프레임이다
    fps = get_fps(input_filepath)

    # crop 좌표를 실제 프레임에 맞게 보정한다
    # 원본 영상 크기(H, W)와 실제 영상 크기(h, w)가 다를 수 있으므로 비례 계산을 수행한다
    # 예) T=63, H=720, h=720이면 t = int(63 / 720 * 720) = 63
    #     B=351, H=720, h=720이면 b = int(351 / 720 * 720) = 351
    #     L=504, W=1280, w=1280이면 l = int(504 / 1280 * 1280) = 504
    #     R=792, W=1280, w=1280이면 r = int(792 / 1280 * 1280) = 792
    # (실제 h, w가 clip에서 온 H, W와 다르면 비례해서 변환)
    t = int(T / H * h)   # top 좌표를 실제 영상 크기에 맞게 보정, 예: 63
    b = int(B / H * h)   # bottom 좌표를 실제 영상 크기에 맞게 보정, 예: 351
    l = int(L / W * w)   # left 좌표를 실제 영상 크기에 맞게 보정, 예: 504
    r = int(R / W * w)   # right 좌표를 실제 영상 크기에 맞게 보정, 예: 792

    # crop된 영역의 너비와 높이를 계산한다
    # r-l은 crop된 영역의 가로 너비(픽셀)이다
    # 예) r=792, l=504이면 r-l=288 (가로 288픽셀)
    crop_width = r - l
    # b-t는 crop된 영역의 세로 높이(픽셀)이다
    # 예) b=351, t=63이면 b-t=288 (세로 288픽셀)
    crop_height = b - t

    # crop된 영역의 크기가 min_crop_width x min_crop_height 이상인지 확인한다
    # crop_width >= min_crop_width는 가로 너비가 min_crop_width픽셀 이상인지 확인한다
    # crop_height >= min_crop_height는 세로 높이가 min_crop_height픽셀 이상인지 확인한다
    # 두 조건을 모두 만족해야만 처리한다 (and 연산자 사용)
    # 예) crop_width=288, crop_height=288, min_crop_width=512, min_crop_height=512이면 288 >= 512는 False이므로 건너뛴다
    #     crop_width=600, crop_height=600, min_crop_width=512, min_crop_height=512이면 600 >= 512는 True이므로 처리한다
    if crop_width >= min_crop_width and crop_height >= min_crop_height:
        # ffmpeg 입력 스트림 생성
        # ffmpeg.input()은 비디오 파일을 입력 스트림으로 로드한다
        # input_filepath에 지정된 비디오 파일을 읽어온다
        input_stream = ffmpeg.input(input_filepath)
        # 비디오와 오디오 스트림을 분리한다
        # input_stream['v:0']은 첫 번째 비디오 스트림을 의미한다
        # input_stream['a:0']은 첫 번째 오디오 스트림을 의미한다 (오디오가 없는 경우 None일 수 있음)
        video = input_stream['v:0']
        # 오디오 스트림이 있는지 확인한다
        # try-except를 사용하여 오디오 스트림이 없을 경우를 처리한다
        try:
            audio = input_stream['a:0']
            has_audio = True
        except:
            has_audio = False
        
        # 비디오 스트림에 특정 프레임 구간만 자르기(trim)
        # ffmpeg.trim()의 start_frame/end_frame은 프레임 번호로 작동하지 않으므로 select 필터를 사용한다
        # select 필터의 between(n,S,E)는 n번째 프레임이 S와 E 사이(포함)에 있으면 선택한다
        # 예를 들어, S=1015, E=1107인 경우 1015~1107 프레임(총 93프레임)을 추출한다
        # setpts=PTS-STARTPTS는 선택된 프레임들의 타임스탬프를 0부터 시작하도록 재설정한다
        # stream = ffmpeg.trim(stream, start_frame=S, end_frame=E+1)  # 이 방법은 프레임 번호로 작동하지 않음
        video = video.filter('select', f'between(n,{S},{E})').filter('setpts', 'PTS-STARTPTS')
        # crop 적용 (좌상단 l,t, 너비 crop_width, 높이 crop_height로 자른다)
        # ffmpeg.crop()은 비디오에서 특정 영역만 잘라낸다
        # 첫 번째 인자 l은 왼쪽 시작 좌표, 두 번째 인자 t는 위쪽 시작 좌표이다
        # 세 번째 인자 crop_width는 잘라낼 가로 너비, 네 번째 인자 crop_height는 잘라낼 세로 높이이다
        # 예) l=504, t=63, crop_width=288, crop_height=288이면
        #     (504, 63) 위치에서 288x288 크기의 영역을 잘라낸다
        video = ffmpeg.crop(video, l, t, crop_width, crop_height)
        
        # 오디오 스트림도 동일한 시간 범위로 trim한다
        # 프레임 번호를 시간(초)으로 변환한다
        # start_time = S / fps는 시작 시간(초)이다
        # 예) S=1015, fps=30이면 start_time = 1015/30 = 33.83초
        # duration = (E - S + 1) / fps는 지속 시간(초)이다
        # 예) S=1015, E=1107, fps=30이면 duration = (1107-1015+1)/30 = 93/30 = 3.1초
        if has_audio:
            start_time = S / fps
            duration = (E - S + 1) / fps
            # atrim 필터는 오디오를 특정 시간 범위로 자른다
            # start=start_time은 시작 시간, duration=duration은 지속 시간이다
            # asetpts=PTS-STARTPTS는 오디오 타임스탬프를 0부터 시작하도록 재설정한다
            audio = audio.filter('atrim', start=start_time, duration=duration).filter('asetpts', 'PTS-STARTPTS')
        
        # 출력 파일로 저장할 스트림 설정
        # ffmpeg.output()은 처리된 스트림을 파일로 출력하도록 설정한다
        # output_filepath에 지정된 경로에 비디오 파일이 저장된다
        # 오디오가 있으면 비디오와 오디오를 모두 포함하고, 없으면 비디오만 포함한다
        if has_audio:
            stream = ffmpeg.output(video, audio, output_filepath)
        else:
            stream = ffmpeg.output(video, output_filepath)
        # 실제로 ffmpeg를 실행해 clip을 생성한다
        # ffmpeg.run()은 설정된 ffmpeg 파이프라인을 실행하여 비디오 처리를 수행한다
        # 비디오가 성공적으로 생성되면 output_filepath에 파일이 저장된다
        ffmpeg.run(stream)
    else:
        # crop된 영역의 크기가 min_crop_width x min_crop_height 미만인 경우 건너뛴다
        # print()를 사용하여 건너뛴다는 메시지를 출력한다
        # %s는 문자열 포맷팅으로, video_name 값이 삽입된다
        # crop_width와 crop_height 값도 함께 출력하여 디버깅에 도움이 되도록 한다
        print('Skipping %s: crop size (%dx%d) is smaller than %dx%d' % (video_name, crop_width, crop_height, min_crop_width, min_crop_height))
        # 함수를 종료하고 다음 클립으로 넘어간다
        return


if __name__ == '__main__':
    # Read list of videos.
    # clip_info는 비디오 클립 정보를 저장할 리스트이다
    # 빈 리스트로 초기화한다
    clip_info = []
    # 클립 정보 파일을 읽어온다
    # open()은 파일을 열고, args.clip_info_file에 지정된 파일 경로를 사용한다
    # with 문을 사용하면 파일 읽기가 끝나면 자동으로 파일을 닫는다
    # 'r' 모드는 기본값이므로 생략 가능하다 (읽기 모드)
    with open(args.clip_info_file) as fin:
        # 파일의 각 줄을 순회한다
        # for 루프는 파일의 각 줄을 한 번에 하나씩 읽어온다
        for line in fin:
            # 각 줄의 앞뒤 공백을 제거하고 clip_info 리스트에 추가한다
            # strip()은 줄바꿈 문자(\n)와 앞뒤 공백을 제거한다
            # append()는 리스트의 끝에 새로운 요소를 추가한다
            # 예) 파일에 '--Y9imYnfBw_0000, 720, 1280, 0, 271, 504, 63, 792, 351'이 있으면
            #     이 문자열이 공백 제거 후 clip_info 리스트에 추가된다
            # 실제 비디오 파일 크기는 다를 수 있으므로(리사이즈 등), 여기서는 모든 줄을 읽고
            # 나중에 trim_and_crop_min_size 함수에서 실제 파일 크기를 확인한 후 필터링한다
            clip_info.append(line.strip())

    # Create output folder.
    # os.makedirs()는 출력 디렉토리를 생성한다
    # exist_ok=True는 디렉토리가 이미 존재해도 오류를 발생시키지 않는다
    # 예) args.output_dir이 'small/cropped_clips'이면 이 경로가 생성된다
    os.makedirs(args.output_dir, exist_ok=True)

    # Download videos.
    # trim_and_crop_min_size 함수를 사용하여 downloader를 생성한다
    # partial()은 함수의 일부 인자를 고정하여 새로운 함수를 만드는 함수이다
    # trim_and_crop_min_size 함수의 첫 번째, 두 번째, 네 번째, 다섯 번째 인자(input_dir, output_dir, min_crop_width, min_crop_height)를 고정하고
    # 세 번째 인자(clip_params)만 받는 새로운 함수를 만든다
    # 이렇게 하면 multiprocessing에서 각 클립 정보만 전달하면 된다
    # trim_and_crop_min_size는 실제 비디오 파일 크기를 확인한 후 min_crop_width x min_crop_height 이상인 경우만 처리한다
    # 실제 파일 크기가 다를 수 있으므로(리사이즈 등), 함수 내에서 실제 크기를 확인하는 것이 더 정확하다
    downloader = partial(trim_and_crop_min_size, args.input_dir, args.output_dir, min_crop_width=args.min_crop_width, min_crop_height=args.min_crop_height)

    # 시작 시간을 기록한다
    # timer()는 현재 시간을 초 단위로 반환한다
    # 처리 시간을 측정하기 위해 시작 시점의 시간을 저장한다
    start = timer()
    # 멀티프로세싱 풀 크기를 설정한다
    # args.num_workers는 명령줄 인자로 전달된 워커 수이다 (기본값 8)
    # pool_size는 동시에 실행될 프로세스의 개수를 의미한다
    # 예) pool_size=8이면 8개의 프로세스가 동시에 작업을 처리한다
    pool_size = args.num_workers
    # 사용할 풀 크기를 출력한다
    # print()를 사용하여 현재 사용 중인 워커 수를 표시한다
    # %d는 정수 포맷팅으로, pool_size 값이 삽입된다
    print('Using pool size of %d' % (pool_size))
    # 멀티프로세싱 풀을 생성하고 작업을 실행한다
    # mp.Pool()은 프로세스 풀을 생성한다
    # processes=pool_size는 풀에 포함될 프로세스의 개수를 지정한다
    # with 문을 사용하면 작업이 끝나면 자동으로 풀을 종료한다
    with mp.Pool(processes=pool_size) as p:
        # imap_unordered()는 각 클립 정보를 downloader 함수에 전달하여 비동기적으로 실행한다
        # imap_unordered는 결과를 순서와 관계없이 반환한다 (처리 순서가 중요하지 않을 때 사용)
        # downloader는 각 clip_params를 받아서 trim_and_crop_min_size 함수를 실행한다
        # tqdm()은 진행률 표시줄을 보여준다
        # total=len(clip_info)는 전체 작업 개수를 지정하여 진행률을 정확히 계산한다
        # list()로 감싸면 모든 작업이 완료될 때까지 대기한다
        # _는 반환값을 사용하지 않는다는 의미이다 (결과 리스트를 저장하지 않음)
        _ = list(tqdm(p.imap_unordered(downloader, clip_info), total=len(clip_info)))
    # 경과 시간을 출력한다
    # timer() - start는 현재 시간에서 시작 시간을 빼서 경과 시간을 계산한다
    # %.2f는 소수점 둘째 자리까지 표시하는 포맷팅이다
    # 예) 123.45초가 걸렸으면 "Elapsed time: 123.45"가 출력된다
    print('Elapsed time: %.2f' % (timer() - start))
