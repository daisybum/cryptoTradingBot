#!/usr/bin/env python3
"""
백테스팅 프레임워크

이 모듈은 전략 검증 및 매개변수 최적화를 위한 포괄적인 백테스팅 프레임워크를 제공합니다.
Freqtrade의 백테스팅 모듈을 사용하여 과거 데이터에 대한 전략 성능을 평가합니다.
"""

import os
import json
import logging
import subprocess
import pandas as pd
import numpy as np
import tempfile
import re
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BacktestingFramework:
    """백테스팅 프레임워크 클래스"""
    
    def __init__(self, config_path: str, data_dir: str):
        """
        백테스팅 프레임워크 초기화
        
        Args:
            config_path: Freqtrade 설정 파일 경로
            data_dir: 백테스트 데이터 디렉토리
        """
        self.config_path = config_path
        self.data_dir = data_dir
        self.results_dir = os.path.join(os.path.dirname(data_dir), 'results')
        
        # 설정 파일이 존재하는지 확인
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")
        
        # 데이터 디렉토리가 존재하는지 확인하고 없으면 생성
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        
        # 설정 파일 로드
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        logger.info(f"백테스팅 프레임워크 초기화됨 (설정: {config_path}, 데이터: {data_dir})")
        
        # 결과 저장을 위한 최근 백테스트 결과
        self.latest_results = None
    
    def download_data(self, pairs: List[str], timeframes: List[str], 
                     start_date: str, end_date: str) -> bool:
        """
        백테스팅을 위한 과거 데이터 다운로드
        
        Args:
            pairs: 거래쌍 목록 (예: ['BTC/USDT', 'ETH/USDT'])
            timeframes: 타임프레임 목록 (예: ['5m', '1h'])
            start_date: 시작 날짜 (YYYYMMDD 형식)
            end_date: 종료 날짜 (YYYYMMDD 형식)
            
        Returns:
            bool: 다운로드 성공 여부
        """
        try:
            # Freqtrade 데이터 다운로드 명령 구성
            command = [
                'freqtrade', 'download-data',
                '--config', self.config_path,
                '--pairs', ','.join(pairs),
                '--timeframes', ','.join(timeframes),
                '--exchange', self.config.get('exchange', {}).get('name', 'binance'),
                '--datadir', self.data_dir,
                '--timerange', f'{start_date}-{end_date}'
            ]
            
            logger.info(f"데이터 다운로드 시작: {pairs}, {timeframes}, {start_date}-{end_date}")
            logger.debug(f"실행 명령: {' '.join(command)}")
            
            # 명령 실행
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            
            # 결과 로깅
            logger.info(f"데이터 다운로드 완료: {self.data_dir}")
            logger.debug(result.stdout)
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"데이터 다운로드 실패: {e}")
            logger.error(f"오류 출력: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"데이터 다운로드 중 예외 발생: {e}")
            return False
            
    def run_backtest(self, strategy: str, timerange: Optional[str] = None, 
                     parameter_file: Optional[str] = None, stake_amount: Optional[float] = None,
                     max_open_trades: Optional[int] = None) -> Dict[str, Any]:
        """
        지정된 매개변수로 백테스트 실행
        
        Args:
            strategy: 전략 이름
            timerange: 백테스트 시간 범위 (예: 20210101-20210131)
            parameter_file: 전략 매개변수 파일
            stake_amount: 거래당 주문 금액 (설정 파일 값 대신 사용)
            max_open_trades: 최대 동시 거래 수 (설정 파일 값 대신 사용)
            
        Returns:
            Dict[str, Any]: 백테스트 결과
        """
        try:
            # 기본 명령 구성
            command = [
                'freqtrade', 'backtesting',
                '--config', self.config_path,
                '--strategy', strategy,
                '--datadir', self.data_dir
            ]
            
            # 시간 범위 추가
            if timerange:
                command.extend(['--timerange', timerange])
            
            # 전략 매개변수 파일 추가
            if parameter_file:
                if not os.path.exists(parameter_file):
                    raise FileNotFoundError(f"매개변수 파일을 찾을 수 없습니다: {parameter_file}")
                command.extend(['--strategy-path', os.path.dirname(parameter_file)])
            
            # 거래당 주문 금액 추가
            if stake_amount is not None:
                command.extend(['--stake-amount', str(stake_amount)])
            
            # 최대 동시 거래 수 추가
            if max_open_trades is not None:
                command.extend(['--max-open-trades', str(max_open_trades)])
            
            # 결과 저장 활성화
            command.extend(['--export', 'trades'])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_filename = f"{strategy}_{timestamp}"
            export_filename = os.path.join(self.results_dir, result_filename)
            command.extend(['--export-filename', export_filename])
            
            logger.info(f"백테스트 시작: {strategy}, 시간 범위: {timerange or '전체'}")
            logger.debug(f"실행 명령: {' '.join(command)}")
            
            # 명령 실행
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            
            # 결과 파싱
            backtest_results = self.parse_backtest_result(result.stdout)
            
            # 결과 저장
            self.latest_results = backtest_results
            
            # 결과 로깅
            logger.info(f"백테스트 완료: {strategy}")
            logger.info(f"총 수익: {backtest_results.get('total_profit', 0):.2f}%, "
                      f"총 거래 수: {backtest_results.get('total_trades', 0)}")
            
            return backtest_results
            
        except subprocess.CalledProcessError as e:
            logger.error(f"백테스트 실패: {e}")
            logger.error(f"오류 출력: {e.stderr}")
            return {}
        except Exception as e:
            logger.error(f"백테스트 중 예외 발생: {e}")
            return {}
    
    def parse_backtest_result(self, output: str) -> Dict[str, Any]:
        """
        백테스트 결과 파싱
        
        Args:
            output: 백테스트 명령 출력
            
        Returns:
            Dict[str, Any]: 구조화된 백테스트 결과
        """
        results = {
            'total_trades': 0,
            'win_trades': 0,
            'loss_trades': 0,
            'win_pct': 0.0,
            'total_profit': 0.0,
            'profit_factor': 0.0,
            'max_drawdown': 0.0,
            'trades': [],
            'pairs': {},
            'duration': {}
        }
        
        try:
            # 총 거래 수 추출
            total_trades_match = re.search(r'Total trades: (\d+)', output)
            if total_trades_match:
                results['total_trades'] = int(total_trades_match.group(1))
            
            # 수익성 지표 추출
            profit_match = re.search(r'Total profit: ([\d.]+)([%]?)', output)
            if profit_match:
                results['total_profit'] = float(profit_match.group(1))
            
            # 승률 추출
            win_rate_match = re.search(r'Win rate: ([\d.]+)%', output)
            if win_rate_match:
                results['win_pct'] = float(win_rate_match.group(1))
                # 승류과 총 거래수로 승/패 거래 수 계산
                if results['total_trades'] > 0:
                    results['win_trades'] = int(results['total_trades'] * results['win_pct'] / 100)
                    results['loss_trades'] = results['total_trades'] - results['win_trades']
            
            # 드로다운 추출
            drawdown_match = re.search(r'Max drawdown: ([\d.]+)%', output)
            if drawdown_match:
                results['max_drawdown'] = float(drawdown_match.group(1))
            
            # 수익 요소 추출
            profit_factor_match = re.search(r'Profit factor: ([\d.]+)', output)
            if profit_factor_match:
                results['profit_factor'] = float(profit_factor_match.group(1))
            
            # 거래쌍별 성능 추출
            pair_section = re.search(r'Pair\s+count\s+wins\s+draws\s+losses\s+winrate\s+profit(.*?)\n\n', output, re.DOTALL)
            if pair_section:
                pair_lines = pair_section.group(1).strip().split('\n')
                for line in pair_lines:
                    parts = re.split(r'\s+', line.strip())
                    if len(parts) >= 7 and '/' in parts[0]:  # 유효한 거래쌍 형식인지 확인
                        pair = parts[0]
                        results['pairs'][pair] = {
                            'count': int(parts[1]),
                            'wins': int(parts[2]),
                            'draws': int(parts[3]) if len(parts) > 3 else 0,
                            'losses': int(parts[4]) if len(parts) > 4 else 0,
                            'winrate': float(parts[5].rstrip('%')) if len(parts) > 5 else 0.0,
                            'profit': float(parts[6].rstrip('%')) if len(parts) > 6 else 0.0
                        }
            
            # 거래 지속 시간별 분포 추출
            duration_section = re.search(r'Duration\s+count\s+wins\s+draws\s+losses(.*?)\n\n', output, re.DOTALL)
            if duration_section:
                duration_lines = duration_section.group(1).strip().split('\n')
                for line in duration_lines:
                    parts = re.split(r'\s+', line.strip())
                    if len(parts) >= 5:
                        duration = parts[0]
                        results['duration'][duration] = {
                            'count': int(parts[1]),
                            'wins': int(parts[2]),
                            'draws': int(parts[3]) if len(parts) > 3 else 0,
                            'losses': int(parts[4]) if len(parts) > 4 else 0
                        }
            
            return results
            
        except Exception as e:
            logger.error(f"백테스트 결과 파싱 중 오류 발생: {e}")
            return results
    
    def run_hyperopt(self, strategy: str, epochs: int = 100, spaces: Optional[List[str]] = None,
                    timerange: Optional[str] = None, hyperopt_loss: str = 'SharpeHyperOptLoss',
                    max_open_trades: Optional[int] = None) -> Dict[str, Any]:
        """
        하이퍼파라미터 최적화 실행
        
        Args:
            strategy: 전략 이름
            epochs: 최적화 반복 횟수
            spaces: 최적화할 공간 (예: 'buy', 'sell', 'roi', 'stoploss', 'trailing', 'protection')
            timerange: 백테스트 시간 범위 (예: 20210101-20210131)
            hyperopt_loss: 최적화에 사용할 손실 함수
            max_open_trades: 최대 동시 거래 수 (설정 파일 값 대신 사용)
            
        Returns:
            Dict[str, Any]: 최적화 결과
        """
        try:
            # 기본 명령 구성
            command = [
                'freqtrade', 'hyperopt',
                '--config', self.config_path,
                '--strategy', strategy,
                '--hyperopt-loss', hyperopt_loss,
                '--epochs', str(epochs),
                '--datadir', self.data_dir,
                '--job-workers', '-1'  # 사용 가능한 모든 CPU 코어 사용
            ]
            
            # 최적화 공간 추가
            if spaces:
                command.extend(['--spaces', ','.join(spaces)])
            
            # 시간 범위 추가
            if timerange:
                command.extend(['--timerange', timerange])
            
            # 최대 동시 거래 수 추가
            if max_open_trades is not None:
                command.extend(['--max-open-trades', str(max_open_trades)])
            
            # 결과 저장 활성화
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_filename = f"hyperopt_{strategy}_{timestamp}"
            export_filename = os.path.join(self.results_dir, result_filename)
            command.extend(['--hyperopt-filename', export_filename])
            
            logger.info(f"하이퍼파라미터 최적화 시작: {strategy}, 반복 횟수: {epochs}")
            logger.debug(f"실행 명령: {' '.join(command)}")
            
            # 명령 실행
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            
            # 결과 파싱
            hyperopt_results = self.parse_hyperopt_result(result.stdout)
            
            # 결과 로깅
            logger.info(f"하이퍼파라미터 최적화 완료: {strategy}")
            logger.info(f"최적 수익: {hyperopt_results.get('best_profit', 0):.2f}%, "
                      f"최적 백테스트 거래 수: {hyperopt_results.get('total_trades', 0)}")
            
            return hyperopt_results
            
        except subprocess.CalledProcessError as e:
            logger.error(f"하이퍼파라미터 최적화 실패: {e}")
            logger.error(f"오류 출력: {e.stderr}")
            return {}
        except Exception as e:
            logger.error(f"하이퍼파라미터 최적화 중 예외 발생: {e}")
            return {}
    
    def parse_hyperopt_result(self, output: str) -> Dict[str, Any]:
        """
        하이퍼파라미터 최적화 결과 파싱
        
        Args:
            output: 하이퍼파라미터 최적화 명령 출력
            
        Returns:
            Dict[str, Any]: 구조화된 최적화 결과
        """
        results = {
            'best_epoch': 0,
            'best_profit': 0.0,
            'total_trades': 0,
            'win_pct': 0.0,
            'best_params': {},
            'all_results': []
        }
        
        try:
            # 최적 에폭 추출
            best_epoch_match = re.search(r'Best result found with epoch (\d+)', output)
            if best_epoch_match:
                results['best_epoch'] = int(best_epoch_match.group(1))
            
            # 최적 수익 추출
            best_profit_match = re.search(r'Best result.*profit: ([\d.-]+)%', output)
            if best_profit_match:
                results['best_profit'] = float(best_profit_match.group(1))
            
            # 총 거래 수 추출
            total_trades_match = re.search(r'Best result.*total trades: (\d+)', output)
            if total_trades_match:
                results['total_trades'] = int(total_trades_match.group(1))
            
            # 승률 추출
            win_pct_match = re.search(r'Best result.*win %: ([\d.]+)', output)
            if win_pct_match:
                results['win_pct'] = float(win_pct_match.group(1))
            
            # 최적 매개변수 추출
            params_section = re.search(r'Parameters to use with.*?\{([^}]*)\}', output, re.DOTALL)
            if params_section:
                params_str = '{' + params_section.group(1) + '}'
                # 안전하게 파싱하기 위해 정규표현식 사용
                params_str = re.sub(r'([\w_]+)(?=:)', r'"\1"', params_str)  # 키를 따옴표로 감싸기
                params_str = re.sub(r'\'([^\']+)\'', r'"\1"', params_str)  # 단일 따옴표를 이중 따옴표로 변경
                
                try:
                    params_dict = json.loads(params_str)
                    results['best_params'] = params_dict
                except json.JSONDecodeError as e:
                    logger.error(f"최적 매개변수 파싱 오류: {e}, 원본: {params_str}")
            
            # 모든 에폭 결과 추출
            epoch_results = re.findall(r'# Epoch\s+(\d+).*?\s+([\d.-]+)%\s+\|\s+(\d+)\s+\|\s+([\d.]+)%', output)
            for epoch, profit, trades, win_rate in epoch_results:
                results['all_results'].append({
                    'epoch': int(epoch),
                    'profit': float(profit),
                    'trades': int(trades),
                    'win_rate': float(win_rate)
                })
            
            return results
            
        except Exception as e:
            logger.error(f"하이퍼파라미터 최적화 결과 파싱 중 오류 발생: {e}")
            return results
    
    def run_walk_forward(self, strategy: str, start_date: str, end_date: str, 
                       window_size_days: int = 30, step_size_days: int = 7,
                       optimize_epochs: int = 50, optimize_spaces: Optional[List[str]] = None,
                       max_open_trades: Optional[int] = None) -> Dict[str, Any]:
        """
        워크포워드 테스팅 실행
        
        워크포워드 테스팅은 시간을 여러 구간으로 나누어 각 구간에서 최적화를 수행하고 다음 구간에서 테스트하는 방식으로,
        과적합(overfitting)을 방지하는 데 도움이 됩니다.
        
        Args:
            strategy: 전략 이름
            start_date: 시작 날짜 (YYYYMMDD 형식)
            end_date: 종료 날짜 (YYYYMMDD 형식)
            window_size_days: 최적화 창 크기 (일 단위)
            step_size_days: 창 이동 크기 (일 단위)
            optimize_epochs: 최적화 반복 횟수
            optimize_spaces: 최적화할 공간 목록
            max_open_trades: 최대 동시 거래 수
            
        Returns:
            Dict[str, Any]: 워크포워드 테스팅 결과
        """
        try:
            # 날짜 객체로 변환
            start = datetime.strptime(start_date, "%Y%m%d")
            end = datetime.strptime(end_date, "%Y%m%d")
            
            # 결과 저장을 위한 객체
            results = {
                'windows': [],
                'overall_profit': 0.0,
                'total_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'max_drawdown': 0.0
            }
            
            # 테스트 창 생성
            current_start = start
            window_id = 1
            
            while current_start < end:
                # 현재 창의 종료 날짜 계산
                train_end = current_start + timedelta(days=window_size_days)
                test_start = train_end
                test_end = test_start + timedelta(days=step_size_days)
                
                # 마지막 창이 전체 기간을 벗어나지 않도록 조정
                if test_end > end:
                    test_end = end
                
                # 현재 창이 유효한지 확인
                if test_start >= end:
                    break
                
                # 날짜 형식 변환
                train_start_str = current_start.strftime("%Y%m%d")
                train_end_str = train_end.strftime("%Y%m%d")
                test_start_str = test_start.strftime("%Y%m%d")
                test_end_str = test_end.strftime("%Y%m%d")
                
                logger.info(f"\n\n워크포워드 창 {window_id}:")
                logger.info(f"\ud559습 기간: {train_start_str} - {train_end_str}")
                logger.info(f"\ud14c스트 기간: {test_start_str} - {test_end_str}")
                
                # 1. 학습 기간에 대한 최적화 수행
                train_timerange = f"{train_start_str}-{train_end_str}"
                logger.info(f"\ud559습 기간 최적화 시작...")
                
                hyperopt_results = self.run_hyperopt(
                    strategy=strategy,
                    epochs=optimize_epochs,
                    spaces=optimize_spaces,
                    timerange=train_timerange,
                    max_open_trades=max_open_trades
                )
                
                if not hyperopt_results or 'best_params' not in hyperopt_results:
                    logger.warning(f"\ucc3d {window_id} 최적화 실패, 다음 창으로 이동")
                    current_start = test_end
                    window_id += 1
                    continue
                
                # 2. 최적 매개변수로 테스트 기간에 백테스트 실행
                test_timerange = f"{test_start_str}-{test_end_str}"
                logger.info(f"\ud14c스트 기간 백테스트 시작...")
                
                # 최적 매개변수를 임시 파일로 저장
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                    json.dump(hyperopt_results['best_params'], temp_file)
                    temp_file_path = temp_file.name
                
                try:
                    # 테스트 기간에 대한 백테스트 실행
                    backtest_results = self.run_backtest(
                        strategy=strategy,
                        timerange=test_timerange,
                        parameter_file=temp_file_path,
                        max_open_trades=max_open_trades
                    )
                    
                    # 창 결과 저장
                    window_result = {
                        'window_id': window_id,
                        'train_period': f"{train_start_str}-{train_end_str}",
                        'test_period': f"{test_start_str}-{test_end_str}",
                        'train_results': hyperopt_results,
                        'test_results': backtest_results
                    }
                    
                    results['windows'].append(window_result)
                    
                    # 결과 로깅
                    logger.info(f"\ucc3d {window_id} 결과:")
                    logger.info(f"\ud559습 기간 최적 수익: {hyperopt_results.get('best_profit', 0):.2f}%")
                    logger.info(f"\ud14c스트 기간 수익: {backtest_results.get('total_profit', 0):.2f}%")
                    logger.info(f"\ud14c스트 기간 거래 수: {backtest_results.get('total_trades', 0)}")
                    
                finally:
                    # 임시 파일 삭제
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                
                # 다음 창으로 이동
                current_start = test_end
                window_id += 1
            
            # 전체 결과 집계
            if results['windows']:
                # 총 수익 계산
                total_profit = sum(w['test_results'].get('total_profit', 0) for w in results['windows'] if 'test_results' in w)
                total_trades = sum(w['test_results'].get('total_trades', 0) for w in results['windows'] if 'test_results' in w)
                
                # 평균 수익 계산
                results['overall_profit'] = total_profit / len(results['windows']) if results['windows'] else 0
                results['total_trades'] = total_trades
                
                # 승률 계산
                win_trades = sum(w['test_results'].get('win_trades', 0) for w in results['windows'] if 'test_results' in w)
                results['win_rate'] = (win_trades / total_trades * 100) if total_trades > 0 else 0
                
                # 최대 드로다운 계산
                results['max_drawdown'] = max(w['test_results'].get('max_drawdown', 0) for w in results['windows'] if 'test_results' in w)
                
                logger.info("\n\n워크포워드 테스팅 완료")
                logger.info(f"창 수: {len(results['windows'])}")
                logger.info(f"평균 수익: {results['overall_profit']:.2f}%")
                logger.info(f"총 거래 수: {results['total_trades']}")
                logger.info(f"승률: {results['win_rate']:.2f}%")
                logger.info(f"최대 드로다운: {results['max_drawdown']:.2f}%")
            
            return results
            
        except Exception as e:
            logger.error(f"워크포워드 테스팅 중 예외 발생: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {'windows': [], 'error': str(e)}
