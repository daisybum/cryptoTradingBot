#!/bin/bash
# 프로그레스 바가 추가된 하이퍼옵트 실행 스크립트

# 색상 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 프로젝트 루트 디렉토리 설정
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 필요한 디렉토리 생성
mkdir -p "${PROJECT_ROOT}/user_data/hyperopt_results"
chmod -R 777 "${PROJECT_ROOT}/user_data/hyperopt_results" 2>/dev/null || true

# 하이퍼옵트 설정
STRATEGY="NASOSv5_mod3"
TIMERANGE="20230101-20230331"  # 2023년 1월-3월 기간으로 변경
EPOCHS=100  # 100 에포크로 감소
SPACES="buy sell roi stoploss"  # 최적화 공간 확장
LOSS_FUNCTION="SharpeHyperOptLoss"  # 샴프 비율 기반 손실 함수
JOBS=16  # CPU 코어 수를 16개로 제한

echo -e "${GREEN}하이퍼파라미터 최적화 시작...${NC}"
echo -e "${BLUE}전략: ${STRATEGY}${NC}"
echo -e "${BLUE}기간: ${TIMERANGE}${NC}"
echo -e "${BLUE}에포크: ${EPOCHS}${NC}"
echo -e "${BLUE}최적화 공간: ${SPACES}${NC}"
echo -e "${BLUE}손실 함수: ${LOSS_FUNCTION}${NC}"
echo -e "${BLUE}병렬 작업 수: ${JOBS}${NC}"

# 프로그레스 바 관련 함수
show_progress() {
    local pid=$1
    local delay=2
    local spinstr='|/-\'
    local temp_file="/tmp/hyperopt_progress_$$.tmp"
    
    echo "" > $temp_file
    
    while ps -p $pid > /dev/null; do
        local temp=$(grep -a "Progress" $temp_file | tail -n 1)
        if [[ "$temp" != "" ]]; then
            echo -ne "\r$temp"
        else
            local i=$(( (i+1) % 4 ))
            echo -ne "\r[${spinstr:$i:1}] 하이퍼옵트 실행 중... "
        fi
        sleep $delay
    done
    echo -ne "\r\033[K"
}

# 로그 파일 설정
LOG_FILE="${PROJECT_ROOT}/hyperopt_$(date +%Y%m%d_%H%M%S).log"
PROGRESS_FILE="/tmp/hyperopt_progress_$$.tmp"

echo -e "${YELLOW}로그 파일: ${LOG_FILE}${NC}"

# Docker 실행 명령
(docker run --rm \
  -v "${PROJECT_ROOT}/user_data:/freqtrade/user_data" \
  -v "${PROJECT_ROOT}/config:/freqtrade/config" \
  --memory=24g \
  --memory-swap=30g \
  freqtradeorg/freqtrade:stable \
  hyperopt \
  --config /freqtrade/config/freqtrade.json \
  --hyperopt-loss $LOSS_FUNCTION \
  --strategy $STRATEGY \
  --timerange $TIMERANGE \
  --spaces $SPACES \
  --epochs $EPOCHS \
  --job-workers $JOBS \
  --print-all \
  --no-color 2>&1 | tee ${LOG_FILE} | grep -a "Progress" > ${PROGRESS_FILE}) &

DOCKER_PID=$!

# 프로그레스 바 표시
show_progress $DOCKER_PID

# 결과 대기
wait $DOCKER_PID
RESULT=$?

# 결과 출력
if [ $RESULT -eq 0 ]; then
    echo -e "${GREEN}하이퍼파라미터 최적화가 성공적으로 완료되었습니다!${NC}"
    
    # 최적의 파라미터 추출 및 표시
    echo -e "${YELLOW}최적의 파라미터 결과:${NC}"
    grep -A 20 "Best result:" ${LOG_FILE} | grep -v "Best result:" | head -n 20
    
    echo -e "${BLUE}전체 로그는 ${LOG_FILE} 파일에서 확인할 수 있습니다.${NC}"
else
    echo -e "${RED}하이퍼파라미터 최적화 중 오류가 발생했습니다.${NC}"
    echo -e "${RED}로그 파일을 확인하세요: ${LOG_FILE}${NC}"
fi

# 임시 파일 정리
rm -f ${PROGRESS_FILE}

echo -e "${GREEN}스크립트 실행 완료${NC}"
