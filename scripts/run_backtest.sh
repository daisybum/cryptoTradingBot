#!/bin/bash
# 백테스트 실행 스크립트
# 이 스크립트는 백테스트 프레임워크를 쉽게 실행할 수 있는 명령어를 제공합니다.

# 프로젝트 루트 디렉토리 설정
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="python3"
BACKTEST_SCRIPT="$PROJECT_ROOT/src/strategy_engine/run_backtest.py"
CONFIG_FILE="$PROJECT_ROOT/config/freqtrade.json"
DATA_DIR="$PROJECT_ROOT/data"

# 색상 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 사용법 출력
function show_usage {
    echo -e "${BLUE}NASOSv5_mod3 백테스트 도구${NC}"
    echo ""
    echo "사용법: $(basename $0) [명령] [옵션]"
    echo ""
    echo "명령:"
    echo "  download     백테스트용 데이터 다운로드"
    echo "  backtest     백테스트 실행"
    echo "  optimize     하이퍼파라미터 최적화 실행"
    echo "  walkforward  워크포워드 테스팅 실행"
    echo "  compare      여러 전략 비교"
    echo "  params       매개변수 최적화 실행"
    echo "  help         이 도움말 표시"
    echo ""
    echo "예시:"
    echo "  $(basename $0) download --pairs BTC/USDT,ETH/USDT --start 20230101 --end 20231231"
    echo "  $(basename $0) backtest --timerange 20230101-20231231 --visualize"
    echo "  $(basename $0) optimize --timerange 20230101-20230630 --epochs 100"
    echo "  $(basename $0) walkforward --start 20230101 --end 20231231 --window 30 --step 7"
    echo ""
    echo "자세한 옵션은 '$(basename $0) [명령] --help'를 실행하세요."
}

# 데이터 다운로드 사용법
function show_download_usage {
    echo -e "${BLUE}데이터 다운로드 명령${NC}"
    echo ""
    echo "사용법: $(basename $0) download [옵션]"
    echo ""
    echo "옵션:"
    echo "  --pairs, -p     다운로드할 거래쌍 (쉼표로 구분, 예: BTC/USDT,ETH/USDT)"
    echo "  --timeframes, -t 다운로드할 타임프레임 (쉼표로 구분, 예: 5m,15m,1h)"
    echo "  --start, -s     시작 날짜 (YYYYMMDD 형식)"
    echo "  --end, -e       종료 날짜 (YYYYMMDD 형식)"
    echo "  --help          이 도움말 표시"
    echo ""
    echo "예시:"
    echo "  $(basename $0) download --pairs BTC/USDT,ETH/USDT --timeframes 5m,15m,1h --start 20230101 --end 20231231"
}

# 백테스트 사용법
function show_backtest_usage {
    echo -e "${BLUE}백테스트 명령${NC}"
    echo ""
    echo "사용법: $(basename $0) backtest [옵션]"
    echo ""
    echo "옵션:"
    echo "  --strategy, -s    백테스트할 전략 이름 (기본값: NASOSv5_mod3)"
    echo "  --timerange, -t   백테스트 시간 범위 (YYYYMMDD-YYYYMMDD 형식)"
    echo "  --params, -p      전략 매개변수 파일"
    echo "  --stake, -a       거래당 주문 금액"
    echo "  --trades, -n      최대 동시 거래 수"
    echo "  --visualize, -v   백테스트 결과 시각화 활성화"
    echo "  --help            이 도움말 표시"
    echo ""
    echo "예시:"
    echo "  $(basename $0) backtest --timerange 20230101-20231231 --stake 100 --trades 5 --visualize"
}

# 최적화 사용법
function show_optimize_usage {
    echo -e "${BLUE}하이퍼파라미터 최적화 명령${NC}"
    echo ""
    echo "사용법: $(basename $0) optimize [옵션]"
    echo ""
    echo "옵션:"
    echo "  --strategy, -s    최적화할 전략 이름 (기본값: NASOSv5_mod3)"
    echo "  --timerange, -t   최적화 시간 범위 (YYYYMMDD-YYYYMMDD 형식)"
    echo "  --epochs, -e      최적화 반복 횟수 (기본값: 100)"
    echo "  --spaces, -p      최적화할 공간 (쉼표로 구분, 예: buy,sell,roi,stoploss)"
    echo "  --loss, -l        최적화에 사용할 손실 함수 (기본값: SharpeHyperOptLoss)"
    echo "  --trades, -n      최대 동시 거래 수"
    echo "  --help            이 도움말 표시"
    echo ""
    echo "예시:"
    echo "  $(basename $0) optimize --timerange 20230101-20230630 --epochs 100 --spaces buy,sell"
}

# 워크포워드 사용법
function show_walkforward_usage {
    echo -e "${BLUE}워크포워드 테스팅 명령${NC}"
    echo ""
    echo "사용법: $(basename $0) walkforward [옵션]"
    echo ""
    echo "옵션:"
    echo "  --strategy, -s    테스트할 전략 이름 (기본값: NASOSv5_mod3)"
    echo "  --start, -b       시작 날짜 (YYYYMMDD 형식)"
    echo "  --end, -e         종료 날짜 (YYYYMMDD 형식)"
    echo "  --window, -w      최적화 창 크기 (일 단위, 기본값: 30)"
    echo "  --step, -p        창 이동 크기 (일 단위, 기본값: 7)"
    echo "  --epochs, -o      최적화 반복 횟수 (기본값: 50)"
    echo "  --spaces, -a      최적화할 공간 (쉼표로 구분, 예: buy,sell)"
    echo "  --trades, -n      최대 동시 거래 수"
    echo "  --visualize, -v   워크포워드 결과 시각화 활성화"
    echo "  --help            이 도움말 표시"
    echo ""
    echo "예시:"
    echo "  $(basename $0) walkforward --start 20230101 --end 20231231 --window 30 --step 7 --visualize"
}

# 매개변수 검증
function validate_required_param {
    if [ -z "$2" ]; then
        echo -e "${RED}오류: $1 매개변수가 필요합니다.${NC}"
        return 1
    fi
    return 0
}

# 데이터 다운로드 명령 처리
function handle_download {
    local pairs=""
    local timeframes="5m,15m,1h"
    local start_date=""
    local end_date=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --pairs|-p)
                pairs="$2"
                shift 2
                ;;
            --timeframes|-t)
                timeframes="$2"
                shift 2
                ;;
            --start|-s)
                start_date="$2"
                shift 2
                ;;
            --end|-e)
                end_date="$2"
                shift 2
                ;;
            --help)
                show_download_usage
                exit 0
                ;;
            *)
                echo -e "${RED}오류: 알 수 없는 옵션 '$1'${NC}"
                show_download_usage
                exit 1
                ;;
        esac
    done

    # 필수 매개변수 검증
    validate_required_param "pairs" "$pairs" || exit 1
    validate_required_param "start_date" "$start_date" || exit 1
    validate_required_param "end_date" "$end_date" || exit 1

    echo -e "${GREEN}데이터 다운로드 시작...${NC}"
    echo "거래쌍: $pairs"
    echo "타임프레임: $timeframes"
    echo "기간: $start_date - $end_date"

    $PYTHON $BACKTEST_SCRIPT download-data \
        --config "$CONFIG_FILE" \
        --datadir "$DATA_DIR" \
        --pairs "$pairs" \
        --timeframes "$timeframes" \
        --start-date "$start_date" \
        --end-date "$end_date"
}

# 백테스트 명령 처리
function handle_backtest {
    local strategy="NASOSv5_mod3"
    local timerange=""
    local params_file=""
    local stake_amount=""
    local max_open_trades=""
    local visualize=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --strategy|-s)
                strategy="$2"
                shift 2
                ;;
            --timerange|-t)
                timerange="$2"
                shift 2
                ;;
            --params|-p)
                params_file="$2"
                shift 2
                ;;
            --stake|-a)
                stake_amount="$2"
                shift 2
                ;;
            --trades|-n)
                max_open_trades="$2"
                shift 2
                ;;
            --visualize|-v)
                visualize="--visualize"
                shift
                ;;
            --help)
                show_backtest_usage
                exit 0
                ;;
            *)
                echo -e "${RED}오류: 알 수 없는 옵션 '$1'${NC}"
                show_backtest_usage
                exit 1
                ;;
        esac
    done

    # 필수 매개변수 검증
    validate_required_param "timerange" "$timerange" || exit 1

    echo -e "${GREEN}백테스트 실행 시작...${NC}"
    echo "전략: $strategy"
    echo "기간: $timerange"
    
    if [ ! -z "$params_file" ]; then
        echo "매개변수 파일: $params_file"
    fi

    cmd="$PYTHON $BACKTEST_SCRIPT backtest \
        --config \"$CONFIG_FILE\" \
        --datadir \"$DATA_DIR\" \
        --strategy \"$strategy\" \
        --timerange \"$timerange\""
    
    if [ ! -z "$params_file" ]; then
        cmd="$cmd --parameter-file \"$params_file\""
    fi
    
    if [ ! -z "$stake_amount" ]; then
        cmd="$cmd --stake-amount \"$stake_amount\""
    fi
    
    if [ ! -z "$max_open_trades" ]; then
        cmd="$cmd --max-open-trades \"$max_open_trades\""
    fi
    
    if [ ! -z "$visualize" ]; then
        cmd="$cmd $visualize"
    fi
    
    eval $cmd
}

# 최적화 명령 처리
function handle_optimize {
    local strategy="NASOSv5_mod3"
    local timerange=""
    local epochs="100"
    local spaces=""
    local hyperopt_loss="SharpeHyperOptLoss"
    local max_open_trades=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --strategy|-s)
                strategy="$2"
                shift 2
                ;;
            --timerange|-t)
                timerange="$2"
                shift 2
                ;;
            --epochs|-e)
                epochs="$2"
                shift 2
                ;;
            --spaces|-p)
                spaces="$2"
                shift 2
                ;;
            --loss|-l)
                hyperopt_loss="$2"
                shift 2
                ;;
            --trades|-n)
                max_open_trades="$2"
                shift 2
                ;;
            --help)
                show_optimize_usage
                exit 0
                ;;
            *)
                echo -e "${RED}오류: 알 수 없는 옵션 '$1'${NC}"
                show_optimize_usage
                exit 1
                ;;
        esac
    done

    # 필수 매개변수 검증
    validate_required_param "timerange" "$timerange" || exit 1

    echo -e "${GREEN}하이퍼파라미터 최적화 시작...${NC}"
    echo "전략: $strategy"
    echo "기간: $timerange"
    echo "에폭: $epochs"
    
    if [ ! -z "$spaces" ]; then
        echo "최적화 공간: $spaces"
    fi

    cmd="$PYTHON $BACKTEST_SCRIPT hyperopt \
        --config \"$CONFIG_FILE\" \
        --datadir \"$DATA_DIR\" \
        --strategy \"$strategy\" \
        --timerange \"$timerange\" \
        --epochs \"$epochs\" \
        --hyperopt-loss \"$hyperopt_loss\""
    
    if [ ! -z "$spaces" ]; then
        cmd="$cmd --spaces \"$spaces\""
    fi
    
    if [ ! -z "$max_open_trades" ]; then
        cmd="$cmd --max-open-trades \"$max_open_trades\""
    fi
    
    eval $cmd
}

# 워크포워드 명령 처리
function handle_walkforward {
    local strategy="NASOSv5_mod3"
    local start_date=""
    local end_date=""
    local window_size="30"
    local step_size="7"
    local optimize_epochs="50"
    local optimize_spaces=""
    local max_open_trades=""
    local visualize=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --strategy|-s)
                strategy="$2"
                shift 2
                ;;
            --start|-b)
                start_date="$2"
                shift 2
                ;;
            --end|-e)
                end_date="$2"
                shift 2
                ;;
            --window|-w)
                window_size="$2"
                shift 2
                ;;
            --step|-p)
                step_size="$2"
                shift 2
                ;;
            --epochs|-o)
                optimize_epochs="$2"
                shift 2
                ;;
            --spaces|-a)
                optimize_spaces="$2"
                shift 2
                ;;
            --trades|-n)
                max_open_trades="$2"
                shift 2
                ;;
            --visualize|-v)
                visualize="--visualize"
                shift
                ;;
            --help)
                show_walkforward_usage
                exit 0
                ;;
            *)
                echo -e "${RED}오류: 알 수 없는 옵션 '$1'${NC}"
                show_walkforward_usage
                exit 1
                ;;
        esac
    done

    # 필수 매개변수 검증
    validate_required_param "start_date" "$start_date" || exit 1
    validate_required_param "end_date" "$end_date" || exit 1

    echo -e "${GREEN}워크포워드 테스팅 시작...${NC}"
    echo "전략: $strategy"
    echo "기간: $start_date - $end_date"
    echo "창 크기: $window_size일"
    echo "이동 간격: $step_size일"
    
    cmd="$PYTHON $BACKTEST_SCRIPT walkforward \
        --config \"$CONFIG_FILE\" \
        --datadir \"$DATA_DIR\" \
        --strategy \"$strategy\" \
        --start-date \"$start_date\" \
        --end-date \"$end_date\" \
        --window-size \"$window_size\" \
        --step-size \"$step_size\" \
        --optimize-epochs \"$optimize_epochs\""
    
    if [ ! -z "$optimize_spaces" ]; then
        cmd="$cmd --optimize-spaces \"$optimize_spaces\""
    fi
    
    if [ ! -z "$max_open_trades" ]; then
        cmd="$cmd --max-open-trades \"$max_open_trades\""
    fi
    
    if [ ! -z "$visualize" ]; then
        cmd="$cmd $visualize"
    fi
    
    eval $cmd
}

# 전략 비교 명령 실행
function handle_compare {
    echo -e "${YELLOW}전략 비교 기능은 Python 스크립트를 직접 실행해야 합니다:${NC}"
    echo "$PYTHON $PROJECT_ROOT/scripts/strategy_comparison.py"
}

# 매개변수 최적화 명령 실행
function handle_params {
    echo -e "${YELLOW}매개변수 최적화 기능은 Python 스크립트를 직접 실행해야 합니다:${NC}"
    echo "$PYTHON $PROJECT_ROOT/scripts/parameter_optimization.py"
}

# 메인 로직
if [ $# -eq 0 ]; then
    show_usage
    exit 0
fi

command="$1"
shift

case "$command" in
    download)
        handle_download "$@"
        ;;
    backtest)
        handle_backtest "$@"
        ;;
    optimize)
        handle_optimize "$@"
        ;;
    walkforward)
        handle_walkforward "$@"
        ;;
    compare)
        handle_compare
        ;;
    params)
        handle_params
        ;;
    help)
        show_usage
        ;;
    *)
        echo -e "${RED}오류: 알 수 없는 명령 '$command'${NC}"
        show_usage
        exit 1
        ;;
esac

exit 0
