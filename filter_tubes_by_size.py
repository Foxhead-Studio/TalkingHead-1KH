import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument('--input_file', type=str, required=True,
                    help='Input tubes file (e.g., train_video_tubes.txt).')
parser.add_argument('--output_file', type=str, required=True,
                    help='Output filtered tubes file.')
parser.add_argument('--video_ids_output_file', type=str, default=None,
                    help='Output file for video IDs (e.g., train_video_ids_512x512.txt). If not specified, will be auto-generated.')
parser.add_argument('--min_width', type=int, default=512,
                    help='Minimum crop width in pixels. Default: 512')
parser.add_argument('--min_height', type=int, default=512,
                    help='Minimum crop height in pixels. Default: 512')
args = parser.parse_args()


def filter_tubes_by_size(input_file, output_file, min_width=512, min_height=512, video_ids_output_file=None):
    # train_video_tubes.txt 파일에서 크롭 크기가 min_width x min_height 이상인 줄만 필터링하는 함수
    # input_file: 입력 tube 정보 파일 경로
    # output_file: 필터링된 결과를 저장할 파일 경로
    # min_width: 최소 크롭 너비(픽셀)
    # min_height: 최소 크롭 높이(픽셀)
    # video_ids_output_file: 비디오 ID를 저장할 파일 경로 (None이면 저장하지 않음)
    # 반환값: (필터링된 줄의 개수, 추출된 비디오 ID 개수)
    
    # 필터링된 줄을 저장할 리스트
    filtered_lines = []
    # 추출된 비디오 ID를 저장할 set (중복 제거를 위해 set 사용)
    # set은 중복된 값을 자동으로 제거하는 자료구조이다
    video_ids = set()
    
    # 입력 파일을 읽어온다
    # open()은 파일을 열고, with 문을 사용하면 파일 읽기가 끝나면 자동으로 파일을 닫는다
    # 'r' 모드는 읽기 모드이다
    with open(input_file, 'r') as fin:
        # 파일의 각 줄을 순회한다
        # for 루프는 파일의 각 줄을 한 번에 하나씩 읽어온다
        for line_num, line in enumerate(fin, start=1):
            # 각 줄의 앞뒤 공백을 제거한다
            # strip()은 줄바꿈 문자(\n)와 앞뒤 공백을 제거한다
            line = line.strip()
            
            # 빈 줄은 건너뛴다
            if not line:
                continue
            
            # tube 정보를 파싱한다
            # 예시: '--Y9imYnfBw_0000, 720, 1280, 0, 271, 504, 63, 792, 351'
            # split(',')으로 콤마를 기준으로 분리한다
            # 예) ['--Y9imYnfBw_0000', ' 720', ' 1280', ' 0', ' 271', ' 504', ' 63', ' 792', ' 351']
            parts = line.split(',')
            
            # 필드 개수가 충분한지 확인한다
            # tube 정보는 최소 9개의 필드가 필요하다 (video_name, H, W, S, E, L, T, R, B)
            if len(parts) < 9:
                print('Warning: Line %d has insufficient fields, skipping: %s' % (line_num, line[:50]))
                continue
            
            try:
                # 각 필드를 정수로 변환한다
                # strip()으로 앞뒤 공백을 제거한 후 int()로 변환한다
                # 예) H=720, W=1280, S=0, E=271, L=504, T=63, R=792, B=351
                H = int(parts[1].strip())  # 원본 영상의 height
                W = int(parts[2].strip())  # 원본 영상의 width
                S = int(parts[3].strip())  # 시작 프레임 번호
                E = int(parts[4].strip())  # 끝 프레임 번호
                L = int(parts[5].strip())  # crop할 영역의 left 좌표
                T = int(parts[6].strip())  # crop할 영역의 top 좌표
                R = int(parts[7].strip())  # crop할 영역의 right 좌표
                B = int(parts[8].strip())  # crop할 영역의 bottom 좌표
                
                # 크롭된 영역의 너비와 높이를 계산한다
                # R-L은 crop된 영역의 가로 너비(픽셀)이다
                # 예) R=792, L=504이면 crop_width = 792 - 504 = 288
                crop_width = R - L
                # B-T는 crop된 영역의 세로 높이(픽셀)이다
                # 예) B=351, T=63이면 crop_height = 351 - 63 = 288
                crop_height = B - T
                
                # 크롭 크기가 min_width x min_height 이상인지 확인한다
                # crop_width >= min_width는 가로 너비가 min_width픽셀 이상인지 확인한다
                # crop_height >= min_height는 세로 높이가 min_height픽셀 이상인지 확인한다
                # 두 조건을 모두 만족해야만 필터링된 리스트에 추가한다 (and 연산자 사용)
                # 예) crop_width=288, crop_height=288, min_width=512, min_height=512이면 288 >= 512는 False이므로 건너뛴다
                #     crop_width=600, crop_height=600, min_width=512, min_height=512이면 600 >= 512는 True이므로 추가한다
                if crop_width >= min_width and crop_height >= min_height:
                    # 조건을 만족하면 필터링된 리스트에 추가한다
                    # 원본 줄을 그대로 추가한다 (공백 포함)
                    filtered_lines.append(line)
                    
                    # 비디오 ID를 추출한다
                    # parts[0]은 비디오명이다 (예: '--Y9imYnfBw_0000')
                    # strip()으로 앞뒤 공백을 제거한다
                    video_name = parts[0].strip()
                    # 비디오명에서 비디오 ID를 추출한다
                    # 비디오명 형식은 'VIDEO_ID_SEGMENT'이다 (예: '--Y9imYnfBw_0000')
                    # rsplit('_', 1)은 오른쪽부터 첫 번째 언더스코어를 기준으로 분리한다
                    # 예) '--Y9imYnfBw_0000'.rsplit('_', 1) → ['--Y9imYnfBw', '0000']
                    # [0]은 비디오 ID 부분만 가져온다 → '--Y9imYnfBw'
                    video_id = video_name.rsplit('_', 1)[0]
                    # set에 비디오 ID를 추가한다 (중복은 자동으로 제거됨)
                    video_ids.add(video_id)
            except ValueError as e:
                # 정수 변환 실패 시 에러 메시지를 출력하고 건너뛴다
                print('Warning: Line %d has invalid numeric values, skipping: %s' % (line_num, line[:50]))
                continue
    
    # 출력 파일의 디렉토리가 없으면 생성한다
    # os.path.dirname()은 파일 경로에서 디렉토리 부분만 추출한다
    # 예) "data_list/filtered_tubes.txt" → "data_list"
    output_dir = os.path.dirname(output_file)
    # os.path.dirname()이 빈 문자열을 반환하면 현재 디렉토리를 의미한다
    if output_dir and not os.path.exists(output_dir):
        # os.makedirs()는 디렉토리를 생성한다
        # exist_ok=True는 디렉토리가 이미 존재해도 오류를 발생시키지 않는다
        os.makedirs(output_dir, exist_ok=True)
    
    # 필터링된 결과를 출력 파일에 저장한다
    # open()은 파일을 열고, 'w' 모드는 쓰기 모드이다
    # with 문을 사용하면 파일 쓰기가 끝나면 자동으로 파일을 닫는다
    with open(output_file, 'w') as fout:
        # 필터링된 각 줄을 파일에 쓴다
        # for 루프로 filtered_lines 리스트의 각 줄을 순회한다
        for line in filtered_lines:
            # write()는 파일에 문자열을 쓴다
            # 줄바꿈 문자(\n)를 추가하여 각 줄을 구분한다
            fout.write(line + '\n')
    
    # 비디오 ID를 저장할 파일 경로가 지정된 경우
    if video_ids_output_file:
        # 출력 파일의 디렉토리가 없으면 생성한다
        # os.path.dirname()은 파일 경로에서 디렉토리 부분만 추출한다
        video_ids_output_dir = os.path.dirname(video_ids_output_file)
        if video_ids_output_dir and not os.path.exists(video_ids_output_dir):
            # os.makedirs()는 디렉토리를 생성한다
            # exist_ok=True는 디렉토리가 이미 존재해도 오류를 발생시키지 않는다
            os.makedirs(video_ids_output_dir, exist_ok=True)
        
        # 비디오 ID를 정렬하여 저장한다
        # sorted()는 리스트나 set을 정렬하여 새로운 리스트를 반환한다
        # 정렬된 비디오 ID 리스트를 생성한다
        sorted_video_ids = sorted(video_ids)
        
        # 비디오 ID를 파일에 저장한다
        # open()은 파일을 열고, 'w' 모드는 쓰기 모드이다
        # with 문을 사용하면 파일 쓰기가 끝나면 자동으로 파일을 닫는다
        with open(video_ids_output_file, 'w') as fout:
            # 정렬된 각 비디오 ID를 파일에 쓴다
            # for 루프로 sorted_video_ids 리스트의 각 비디오 ID를 순회한다
            for video_id in sorted_video_ids:
                # write()는 파일에 문자열을 쓴다
                # 줄바꿈 문자(\n)를 추가하여 각 줄을 구분한다
                fout.write(video_id + '\n')
    
    # 필터링된 줄의 개수와 추출된 비디오 ID 개수를 반환한다
    return len(filtered_lines), len(video_ids)


if __name__ == '__main__':
    # 입력 파일이 존재하는지 확인한다
    # os.path.exists()는 파일이나 디렉토리가 존재하는지 확인한다
    if not os.path.exists(args.input_file):
        print('Error: Input file does not exist: %s' % (args.input_file))
        exit(1)
    
    # 비디오 ID 출력 파일이 지정되지 않은 경우 자동으로 생성한다
    # 예) input_file='data_list/train_video_tubes.txt', min_width=512, min_height=512이면
    #     video_ids_output_file='data_list/train_video_ids_512x512.txt'
    if args.video_ids_output_file is None:
        # 입력 파일의 디렉토리 경로를 가져온다
        # os.path.dirname()은 파일 경로에서 디렉토리 부분만 추출한다
        # 예) 'data_list/train_video_tubes.txt' → 'data_list'
        input_dir = os.path.dirname(args.input_file)
        # 비디오 ID 출력 파일명을 생성한다
        # os.path.join()은 경로를 올바르게 결합한다
        # 예) input_dir='data_list'이면 'data_list/train_video_ids_512x512.txt'
        video_ids_output_file = os.path.join(input_dir, 'train_video_ids_%dx%d.txt' % (args.min_width, args.min_height))
    else:
        video_ids_output_file = args.video_ids_output_file
    
    # 필터링 작업을 수행한다
    # filter_tubes_by_size() 함수를 호출하여 크롭 크기가 min_width x min_height 이상인 줄만 필터링한다
    # 반환값은 (필터링된 줄의 개수, 추출된 비디오 ID 개수) 튜플이다
    filtered_count, video_ids_count = filter_tubes_by_size(
        args.input_file, args.output_file, 
        min_width=args.min_width, min_height=args.min_height,
        video_ids_output_file=video_ids_output_file
    )
    
    # 결과를 출력한다
    # 필터링된 줄의 개수를 출력한다
    print('Filtered %d tubes with size >= %dx%d' % (filtered_count, args.min_width, args.min_height))
    print('Output saved to: %s' % (args.output_file))
    # 추출된 비디오 ID 개수를 출력한다
    print('Extracted %d unique video IDs' % (video_ids_count))
    print('Video IDs saved to: %s' % (video_ids_output_file))

