#!/usr/bin/env python3
"""
백테스트 실행 모듈

이 모듈은 백테스팅 프레임워크의 주요 진입점입니다.
명령줄 인터페이스를 통해 백테스트 및 최적화를 실행할 수 있습니다.
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime

# 프로젝트 루트 경로 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.strategy_engine.backtesting import BacktestingFramework
from src.strategy_engine.visualization import BacktestVisualizer

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """명령줄 인수 파싱"""
    parser = argparse.ArgumentParser(description='NASOSv5_mod3 백테스팅 프레임워크')
    
    # 기본 인수
    parser.add_argument('--config', type=str, default=os.path.join(project_root, 'config', 'freqtrade.json'),
                      help='Freqtrade 설정 파일 경로')
    parser.add_argument('--datadir', type=str, default=os.path.join(project_root, 'data'),
                      help='백테스트 데이터 디렉토리')
    parser.add_argument('--strategy', type=str, default='NASOSv5_mod3',
                      help='백테스트할 전략 이름')
    
    # 서브 파서 생성
    subparsers = parser.add_subparsers(dest='command', help='실행할 명령')
    
    # 데이터 다운로드 명령
    download_parser = subparsers.add_parser('download-data', help='백테스트용 데이터 다운로드')
    download_parser.add_argument('--pairs', type=str, required=True,
                               help='다운로드할 거래쌍 (쉼표로 구분)')
    download_parser.add_argument('--timeframes', type=str, default='5m,15m,1h',
                               help='다운로드할 타임프레임 (쉼표로 구분)')
    download_parser.add_argument('--start-date', type=str, required=True,
                               help='시작 날짜 (YYYYMMDD 형식)')
    download_parser.add_argument('--end-date', type=str, required=True,
                               help='종료 날짜 (YYYYMMDD 형식)')
    
    # 백테스트 명령
    backtest_parser = subparsers.add_parser('backtest', help='백테스트 실행')
    backtest_parser.add_argument('--timerange', type=str,
                               help='백테스트 시간 범위 (YYYYMMDD-YYYYMMDD 형식)')
    backtest_parser.add_argument('--parameter-file', type=str,
                               help='전략 매개변수 파일')
    backtest_parser.add_argument('--stake-amount', type=float,
                               help='거래당 주문 금액')
    backtest_parser.add_argument('--max-open-trades', type=int,
                               help='최대 동시 거래 수')
    backtest_parser.add_argument('--visualize', action='store_true',
                               help='백테스트 결과 시각화')
    
    # 최적화 명령
    hyperopt_parser = subparsers.add_parser('hyperopt', help='하이퍼파라미터 최적화 실행')
    hyperopt_parser.add_argument('--timerange', type=str,
                               help='최적화 시간 범위 (YYYYMMDD-YYYYMMDD 형식)')
    hyperopt_parser.add_argument('--epochs', type=int, default=100,
                               help='최적화 반복 횟수')
    hyperopt_parser.add_argument('--spaces', type=str,
                               help='최적화할 공간 (쉼표로 구분)')
    hyperopt_parser.add_argument('--hyperopt-loss', type=str, default='SharpeHyperOptLoss',
                               help='최적화에 사용할 손실 함수')
    hyperopt_parser.add_argument('--max-open-trades', type=int,
                               help='최대 동시 거래 수')
    
    # 워크포워드 테스팅 명령
    walkforward_parser = subparsers.add_parser('walkforward', help='워크포워드 테스팅 실행')
    walkforward_parser.add_argument('--start-date', type=str, required=True,
                                  help='시작 날짜 (YYYYMMDD 형식)')
    walkforward_parser.add_argument('--end-date', type=str, required=True,
                                  help='종료 날짜 (YYYYMMDD 형식)')
    walkforward_parser.add_argument('--window-size', type=int, default=30,
                                  help='최적화 창 크기 (일 단위)')
    walkforward_parser.add_argument('--step-size', type=int, default=7,
                                  help='창 이동 크기 (일 단위)')
    walkforward_parser.add_argument('--optimize-epochs', type=int, default=50,
                                  help='최적화 반복 횟수')
    walkforward_parser.add_argument('--optimize-spaces', type=str,
                                  help='최적화할 공간 (쉼표로 구분)')
    walkforward_parser.add_argument('--max-open-trades', type=int,
                                  help='최대 동시 거래 수')
    walkforward_parser.add_argument('--visualize', action='store_true',
                                  help='워크포워드 결과 시각화')
    
    return parser.parse_args()

def run_download_data(args, backtesting_framework):
    """데이터 다운로드 실행"""
    pairs = args.pairs.split(',')
    timeframes = args.timeframes.split(',')
    
    logger.info(f"데이터 다운로드 시작: {pairs}, {timeframes}, {args.start_date}-{args.end_date}")
    
    success = backtesting_framework.download_data(
        pairs=pairs,
        timeframes=timeframes,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    if success:
        logger.info("데이터 다운로드 완료")
    else:
        logger.error("데이터 다운로드 실패")
        sys.exit(1)

def run_backtest(args, backtesting_framework):
    """백테스트 실행"""
    logger.info(f"백테스트 시작: {args.strategy}")
    
    backtest_results = backtesting_framework.run_backtest(
        strategy=args.strategy,
        timerange=args.timerange,
        parameter_file=args.parameter_file,
        stake_amount=args.stake_amount,
        max_open_trades=args.max_open_trades
    )
    
    if not backtest_results:
        logger.error("백테스트 실패")
        sys.exit(1)
    
    # 결과 요약 출력
    logger.info("백테스트 결과 요약:")
    logger.info(f"총 거래 수: {backtest_results.get('total_trades', 0)}")
    logger.info(f"승률: {backtest_results.get('win_pct', 0):.2f}%")
    logger.info(f"총 수익: {backtest_results.get('total_profit', 0):.2f}%")
    logger.info(f"최대 드로다운: {backtest_results.get('max_drawdown', 0):.2f}%")
    
    # 시각화 실행
    if args.visualize:
        visualizer = BacktestVisualizer(os.path.join(project_root, 'results'))
        report_dir = visualizer.create_performance_report(backtest_results, args.strategy)
        logger.info(f"백테스트 보고서 생성 완료: {report_dir}")
    
    return backtest_results

def run_hyperopt(args, backtesting_framework):
    """하이퍼파라미터 최적화 실행"""
    logger.info(f"하이퍼파라미터 최적화 시작: {args.strategy}, 에폭: {args.epochs}")
    
    spaces = args.spaces.split(',') if args.spaces else None
    
    hyperopt_results = backtesting_framework.run_hyperopt(
        strategy=args.strategy,
        epochs=args.epochs,
        spaces=spaces,
        timerange=args.timerange,
        hyperopt_loss=args.hyperopt_loss,
        max_open_trades=args.max_open_trades
    )
    
    if not hyperopt_results:
        logger.error("하이퍼파라미터 최적화 실패")
        sys.exit(1)
    
    # 결과 요약 출력
    logger.info("하이퍼파라미터 최적화 결과 요약:")
    logger.info(f"최적 에폭: {hyperopt_results.get('best_epoch', 0)}")
    logger.info(f"최적 수익: {hyperopt_results.get('best_profit', 0):.2f}%")
    logger.info(f"총 거래 수: {hyperopt_results.get('total_trades', 0)}")
    logger.info(f"승률: {hyperopt_results.get('win_pct', 0):.2f}%")
    
    # 최적 매개변수 출력
    best_params = hyperopt_results.get('best_params', {})
    if best_params:
        logger.info("최적 매개변수:")
        for key, value in best_params.items():
            logger.info(f"  {key}: {value}")
    
    # 매개변수 파일 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    params_dir = os.path.join(project_root, 'results', 'hyperopt')
    os.makedirs(params_dir, exist_ok=True)
    
    params_file = os.path.join(params_dir, f"{args.strategy}_params_{timestamp}.json")
    with open(params_file, 'w') as f:
        json.dump(best_params, f, indent=4)
    
    logger.info(f"최적 매개변수 저장됨: {params_file}")
    
    return hyperopt_results

def run_walkforward(args, backtesting_framework):
    """워크포워드 테스팅 실행"""
    logger.info(f"워크포워드 테스팅 시작: {args.strategy}")
    
    spaces = args.optimize_spaces.split(',') if args.optimize_spaces else None
    
    walkforward_results = backtesting_framework.run_walk_forward(
        strategy=args.strategy,
        start_date=args.start_date,
        end_date=args.end_date,
        window_size_days=args.window_size,
        step_size_days=args.step_size,
        optimize_epochs=args.optimize_epochs,
        optimize_spaces=spaces,
        max_open_trades=args.max_open_trades
    )
    
    if not walkforward_results or 'error' in walkforward_results:
        logger.error(f"워크포워드 테스팅 실패: {walkforward_results.get('error', '')}")
        sys.exit(1)
    
    # 결과 요약 출력
    logger.info("워크포워드 테스팅 결과 요약:")
    logger.info(f"테스트 창 수: {len(walkforward_results.get('windows', []))}")
    logger.info(f"평균 수익: {walkforward_results.get('overall_profit', 0):.2f}%")
    logger.info(f"총 거래 수: {walkforward_results.get('total_trades', 0)}")
    logger.info(f"승률: {walkforward_results.get('win_rate', 0):.2f}%")
    logger.info(f"최대 드로다운: {walkforward_results.get('max_drawdown', 0):.2f}%")
    
    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = os.path.join(project_root, 'results', 'walkforward')
    os.makedirs(results_dir, exist_ok=True)
    
    results_file = os.path.join(results_dir, f"{args.strategy}_walkforward_{timestamp}.json")
    with open(results_file, 'w') as f:
        json.dump(walkforward_results, f, indent=4)
    
    logger.info(f"워크포워드 결과 저장됨: {results_file}")
    
    # 시각화 실행 (각 창별 결과)
    if args.visualize and 'windows' in walkforward_results:
        visualizer = BacktestVisualizer(os.path.join(project_root, 'results'))
        
        # 각 창별 테스트 결과 시각화
        for window in walkforward_results['windows']:
            if 'test_results' in window:
                window_id = window['window_id']
                test_period = window['test_period']
                
                report_dir = visualizer.create_performance_report(
                    window['test_results'],
                    f"{args.strategy}_Window{window_id}_{test_period}",
                    os.path.join(results_dir, f"window_{window_id}")
                )
                logger.info(f"창 {window_id} 보고서 생성 완료: {report_dir}")
    
    return walkforward_results

def main():
    """메인 함수"""
    args = parse_arguments()
    
    # 백테스팅 프레임워크 초기화
    backtesting_framework = BacktestingFramework(
        config_path=args.config,
        data_dir=args.datadir
    )
    
    # 명령에 따라 실행
    if args.command == 'download-data':
        run_download_data(args, backtesting_framework)
    elif args.command == 'backtest':
        run_backtest(args, backtesting_framework)
    elif args.command == 'hyperopt':
        run_hyperopt(args, backtesting_framework)
    elif args.command == 'walkforward':
        run_walkforward(args, backtesting_framework)
    else:
        logger.error(f"알 수 없는 명령: {args.command}")
        sys.exit(1)
    
    logger.info("실행 완료")

if __name__ == "__main__":
    main()
