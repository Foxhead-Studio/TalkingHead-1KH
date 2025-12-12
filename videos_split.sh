#!/bin/bash
# #!/bin/bash: 이 스크립트를 bash 셸로 실행하라는 shebang 라인이다
# 스크립트 실행 시 시스템이 자동으로 /bin/bash를 사용하여 이 파일을 해석한다

in_dir=$1
# in_dir=$1: 첫 번째 명령줄 인자를 in_dir 변수에 저장한다
# 예를 들어, ./videos_split.sh small/raw_videos small/1min_clips를 실행하면
# $1은 "small/raw_videos"가 되고, in_dir 변수에 이 값이 저장된다

out_dir=$2
# out_dir=$2: 두 번째 명령줄 인자를 out_dir 변수에 저장한다
# 위 예시에서 $2는 "small/1min_clips"가 되고, out_dir 변수에 이 값이 저장된다

mkdir $out_dir;
# mkdir $out_dir: 출력 디렉토리를 생성한다
# $out_dir 변수의 값(예: "small/1min_clips")이 디렉토리로 생성된다
# 이미 존재하는 경우 오류가 발생할 수 있지만, 스크립트는 계속 진행한다

for f in $in_dir/*.mp4
# for f in $in_dir/*.mp4: 입력 디렉토리($in_dir) 내의 모든 .mp4 파일에 대해 반복한다
# 예를 들어, small/raw_videos/ 디렉토리에 video1.mp4, video2.mp4가 있으면
# f는 각각 "small/raw_videos/video1.mp4", "small/raw_videos/video2.mp4" 값을 가진다
# *는 와일드카드로, 모든 .mp4 확장자를 가진 파일을 매칭한다

do
  y=${f##*/};
  # y=${f##*/}: 파일 경로에서 파일명만 추출한다
  # ${f##*/}는 bash의 파라미터 확장 문법으로, 마지막 / 이후의 문자열만 남긴다
  # 예를 들어, f가 "small/raw_videos/video1.mp4"이면 y는 "video1.mp4"가 된다
  # ##은 가장 긴 매칭을 의미하며, */ 패턴과 매칭되는 부분을 모두 제거한다

  ffmpeg -i $f -c copy -map 0 -segment_time 00:01:00 -f segment $out_dir/${y/.mp4}_%04d.mp4;
  # ffmpeg -i $f: 입력 파일($f)을 지정한다
  # -c copy: 비디오/오디오 코덱을 재인코딩하지 않고 복사한다 (빠르고 품질 손실 없음)
  # -map 0: 입력 파일의 모든 스트림(비디오, 오디오 등)을 매핑한다
  # -segment_time 00:01:00: 각 세그먼트의 길이를 1분(00:01:00)으로 설정한다
  # -f segment: 세그먼트 포맷으로 출력한다 (여러 파일로 분할)
  # $out_dir/${y/.mp4}_%04d.mp4: 출력 파일명 패턴을 지정한다
  # ${y/.mp4}는 y 변수에서 .mp4를 제거한다 (예: "video1.mp4" → "video1")
  # %04d는 4자리 숫자로 자동 증가하는 번호를 의미한다 (0000, 0001, 0002, ...)
  # 예를 들어, video1.mp4가 3분 길이면 video1_0000.mp4, video1_0001.mp4, video1_0002.mp4가 생성된다
  # 최종 출력 경로는 "small/1min_clips/video1_0000.mp4" 같은 형태가 된다

done
# done: for 루프의 끝을 나타낸다
# 모든 .mp4 파일에 대한 처리가 완료되면 스크립트가 종료된다