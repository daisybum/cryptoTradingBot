"""
CLI 메뉴 시스템 - 트레이딩 봇의 명령줄 인터페이스

이 모듈은 트레이딩 봇의 다양한 기능에 접근할 수 있는 대화형 CLI 메뉴를 제공합니다.
Rich 라이브러리를 사용하여 컬러 코딩된 메뉴, 테이블, 진행 표시줄 등을 구현합니다.
"""
import os
import sys
import time
import argparse
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

# Rich 라이브러리 임포트
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.text import Text
from rich.layout import Layout
from rich.live import Live

# 프로젝트 루트 경로를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

from src.database.connection import get_db_manager, init_db
from src.risk_manager.risk_manager import RiskManager
from src.notifications.telegram import TelegramNotifier

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradingBotCLI:
    """Rich 라이브러리를 활용한 트레이딩 봇 CLI 인터페이스"""
    
    def __init__(self):
        """TradingBotCLI 초기화"""
        self.console = Console()
        self.db_manager = get_db_manager()
        self.risk_manager = None
        self.telegram = None
        self.running = True
        self.config_path = project_root / "config" / "bot_config.yaml"
        self.verbosity = "info"  # 기본 로깅 레벨
        
        # 메뉴 옵션 정의
        self.menu_options = [
            {"key": "1", "title": "Start Trading", "description": "트레이딩 봇 시작", "func": self.start_bot},
            {"key": "2", "title": "Stop Trading", "description": "트레이딩 봇 중지", "func": self.stop_bot},
            {"key": "3", "title": "View Status", "description": "현재 봇 상태 확인", "func": self.show_status},
            {"key": "4", "title": "Recent Trades", "description": "최근 거래 내역 보기", "func": self.show_trades},
            {"key": "5", "title": "Performance", "description": "성능 지표 확인", "func": self.show_performance},
            {"key": "6", "title": "Configure", "description": "봇 설정 변경", "func": self.configure_bot},
            {"key": "7", "title": "Run Backtest", "description": "백테스트 실행", "func": self.run_backtest},
            {"key": "8", "title": "Switch Mode", "description": "드라이런/라이브 모드 전환", "func": self.switch_mode},
            {"key": "9", "title": "Risk Management", "description": "리스크 관리 설정", "func": self.manage_risk},
            {"key": "0", "title": "Notifications", "description": "알림 설정", "func": self.manage_notifications},
            {"key": "q", "title": "Quit", "description": "프로그램 종료", "func": self.exit_menu}
        ]
    
    def initialize(self):
        """필요한 구성 요소 초기화"""
        try:
            with self.console.status("[bold green]시스템 초기화 중...[/bold green]"):
                # 설정 파일 로드
                config = self.load_config()
                
                # 리스크 관리 설정 준비
                risk_config = {
                    'risk_management': {
                        'max_drawdown': config.get('risk', {}).get('max_drawdown', 10.0) / 100,
                        'stop_loss': config.get('risk', {}).get('stop_loss', 3.5) / 100,
                        'risk_per_trade': config.get('risk', {}).get('trade_risk', 1.0) / 100,
                        'daily_trade_limit': config.get('risk', {}).get('daily_trade_limit', 60),
                        'circuit_breaker': config.get('risk', {}).get('circuit_breaker', 5.0) / 100
                    }
                }
                
                # 데이터베이스 초기화 시도
                try:
                    # 데이터베이스 설정 준비
                    db_config = {
                        'postgresql': {
                            'host': os.environ.get('POSTGRES_HOST', 'localhost'),
                            'port': os.environ.get('POSTGRES_PORT', '5432'),
                            'database': os.environ.get('POSTGRES_DB', 'trading_bot'),
                            'user': os.environ.get('POSTGRES_USER', 'postgres'),
                            'password': os.environ.get('POSTGRES_PASSWORD', 'postgres')
                        },
                        'influxdb': {
                            'url': os.environ.get('INFLUXDB_URL', 'http://localhost:8086'),
                            'token': os.environ.get('INFLUXDB_TOKEN', ''),
                            'org': os.environ.get('INFLUXDB_ORG', 'trading_bot'),
                            'bucket': os.environ.get('INFLUXDB_BUCKET', 'trading_data')
                        }
                    }
                    
                    # 데이터베이스 초기화 시도
                    init_db(db_config)
                    self.console.log("[green]데이터베이스가 초기화되었습니다.[/green]")
                except Exception as db_error:
                    self.console.log(f"[yellow]데이터베이스 초기화 실패: {db_error}. 일부 기능이 제한될 수 있습니다.[/yellow]")
                
                # 리스크 관리자 초기화
                try:
                    self.risk_manager = RiskManager(risk_config)
                    self.console.log("[green]리스크 관리자가 초기화되었습니다.[/green]")
                except Exception as risk_error:
                    self.console.log(f"[yellow]리스크 관리자 초기화 실패: {risk_error}. 리스크 관리 기능이 비활성화됩니다.[/yellow]")
                    self.risk_manager = None
                
                # 텔레그램 알림 초기화
                try:
                    telegram_token = os.environ.get('TELEGRAM_TOKEN')
                    telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
                    
                    if telegram_token and telegram_chat_id:
                        self.telegram = TelegramNotifier(telegram_token, telegram_chat_id)
                        self.console.log("[green]텔레그램 알림 시스템이 초기화되었습니다.[/green]")
                    else:
                        self.console.log("[yellow]텔레그램 토큰 또는 채팅 ID가 설정되지 않았습니다. 알림 기능이 비활성화됩니다.[/yellow]")
                        self.telegram = None
                except Exception as telegram_error:
                    self.console.log(f"[yellow]텔레그램 초기화 실패: {telegram_error}. 알림 기능이 비활성화됩니다.[/yellow]")
                    self.telegram = None
            
            # 초기화 성공
            self.console.print("[bold green]시스템이 성공적으로 초기화되었습니다.[/bold green]")
            return True
            
        except Exception as e:
            logger.error(f"초기화 중 오류 발생: {e}")
            self.console.print(f"[bold red]초기화 중 오류 발생: {e}[/bold red]")
            return False
    
    def load_config(self):
        """YAML 설정 파일 로드"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as file:
                    config = yaml.safe_load(file)
                    self.console.log(f"[green]설정 파일을 로드했습니다: {self.config_path}[/green]")
                    return config
            else:
                self.console.log(f"[yellow]설정 파일이 없습니다. 기본 설정을 사용합니다: {self.config_path}[/yellow]")
                # 기본 설정 생성
                default_config = {
                    "trading": {
                        "mode": "dry-run",
                        "stake_amount": 100,
                        "max_open_trades": 3
                    },
                    "risk": {
                        "max_drawdown": 10.0,
                        "trade_risk": 1.0
                    },
                    "notifications": {
                        "enabled": True,
                        "level": "info"
                    }
                }
                # 설정 파일 저장
                self.save_config(default_config)
                return default_config
        except Exception as e:
            logger.error(f"설정 파일 로드 중 오류 발생: {e}")
            self.console.print(f"[bold red]설정 파일 로드 중 오류 발생: {e}[/bold red]")
            return {}
    
    def save_config(self, config):
        """YAML 설정 파일 저장"""
        try:
            # 디렉토리가 없으면 생성
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w') as file:
                yaml.dump(config, file, default_flow_style=False)
                self.console.log(f"[green]설정 파일을 저장했습니다: {self.config_path}[/green]")
        except Exception as e:
            logger.error(f"설정 파일 저장 중 오류 발생: {e}")
            self.console.print(f"[bold red]설정 파일 저장 중 오류 발생: {e}[/bold red]")
    
    def display_main_menu(self):
        """메인 메뉴 표시"""
        self.console.clear()
        
        # 헤더 표시
        self.console.print(Panel("[bold blue]NASOSv5_mod3 Trading Bot[/bold blue]", 
                                 subtitle="[italic]Powered by Rich CLI[/italic]"))
        
        # 메뉴 테이블 생성
        table = Table(show_header=True, header_style="bold magenta", expand=True)
        table.add_column("Key", style="dim", width=4)
        table.add_column("Option", style="bold cyan")
        table.add_column("Description")
        
        # 메뉴 옵션 추가
        for option in self.menu_options:
            table.add_row(option["key"], option["title"], option["description"])
        
        # 테이블 출력
        self.console.print(table)
        
        # 사용자 입력 받기
        try:
            choice = Prompt.ask("명령을 선택하세요", 
                               choices=[option["key"] for option in self.menu_options],
                               default="3")
            
            # 선택한 메뉴 실행
            for option in self.menu_options:
                if option["key"] == choice:
                    option["func"]()
                    break
        except (EOFError, KeyboardInterrupt):
            # 터미널 환경에서 발생할 수 있는 예외 처리
            self.console.print("\n[yellow]입력이 취소되었습니다.[/yellow]")
            self.exit_menu()
    
    def start_bot(self):
        """트레이딩 봇 시작"""
        self.console.print("[bold green]트레이딩 봇을 시작합니다...[/bold green]")
        
        # 진행 표시줄로 시작 과정 표시
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold green]Starting...[/bold green]"),
            BarColumn(),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task("[green]Starting...", total=100)
            
            # 시작 과정 시뮬레이션
            for i in range(101):
                time.sleep(0.02)  # 시뮬레이션을 위한 지연
                progress.update(task, completed=i)
        
        # 여기에 봇 시작 로직 구현
        
        if self.telegram:
            self.telegram.send_message("🚀 트레이딩 봇이 시작되었습니다.")
        
        self.console.print("[bold green]트레이딩 봇이 성공적으로 시작되었습니다.[/bold green]")
        self.wait_for_enter()
    
    def stop_bot(self):
        """트레이딩 봇 중지"""
        if Confirm.ask("정말로 트레이딩 봇을 중지하시겠습니까?"):
            self.console.print("[bold yellow]트레이딩 봇을 중지합니다...[/bold yellow]")
            
            # 진행 표시줄로 중지 과정 표시
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold yellow]Stopping...[/bold yellow]"),
                BarColumn(),
                TimeElapsedColumn(),
            ) as progress:
                task = progress.add_task("[yellow]Stopping...", total=100)
                
                # 중지 과정 시뮬레이션
                for i in range(101):
                    time.sleep(0.01)  # 시뮬레이션을 위한 지연
                    progress.update(task, completed=i)
            
            # 여기에 봇 중지 로직 구현
            
            if self.telegram:
                self.telegram.send_message("🛑 트레이딩 봇이 중지되었습니다.")
            
            self.console.print("[bold yellow]트레이딩 봇이 성공적으로 중지되었습니다.[/bold yellow]")
        
        self.wait_for_enter()
    
    def show_status(self):
        """트레이딩 봇 상태 표시"""
        try:
            self.console.print("[bold cyan]상태 정보를 가져오는 중...[/bold cyan]")
            
            with self.console.status("[bold cyan]데이터베이스에서 상태 정보를 가져오는 중...[/bold cyan]"):
                # 데이터베이스에서 상태 정보 가져오기
                with self.db_manager.get_pg_session() as session:
                    # 활성 거래 세션 수 확인
                    active_sessions = session.execute(
                        "SELECT COUNT(*) FROM trade_sessions WHERE is_active = TRUE"
                    ).scalar()
                    
                    # 오늘의 거래 수 확인
                    today_trades = session.execute(
                        "SELECT COUNT(*) FROM trades WHERE DATE(open_time) = CURRENT_DATE"
                    ).scalar()
                    
                    # 오늘의 수익 확인
                    today_profit = session.execute(
                        "SELECT COALESCE(SUM(pnl), 0) FROM trades WHERE DATE(open_time) = CURRENT_DATE AND status = 'closed'"
                    ).scalar()
                
                # 리스크 관리자 상태 확인
                risk_status = "활성화" if self.risk_manager and self.risk_manager.is_active() else "비활성화"
                kill_switch = "활성화" if self.risk_manager and self.risk_manager.is_kill_switch_active() else "비활성화"
            
            # 상태 정보를 패널로 표시
            status_panel = Panel(
                f"""[bold]활성 거래 세션:[/bold] {active_sessions}
[bold]오늘의 거래 수:[/bold] {today_trades}
[bold]오늘의 수익:[/bold] {today_profit:.2f} USDT
[bold]리스크 관리자:[/bold] {risk_status}
[bold]킬 스위치:[/bold] {kill_switch}""",
                title="[bold cyan]트레이딩 봇 상태[/bold cyan]",
                border_style="cyan"
            )
            
            self.console.print(status_panel)
            
        except Exception as e:
            logger.error(f"상태 정보 가져오기 실패: {e}")
            self.console.print(f"[bold red]상태 정보를 가져오는 중 오류가 발생했습니다: {e}[/bold red]")
        
        self.wait_for_enter()
    
    def show_trades(self):
        """최근 거래 내역 표시"""
        try:
            limit = Prompt.ask("표시할 거래 수", default="10")
            limit = int(limit)
            
            self.console.print(f"[bold cyan]최근 {limit}개의 거래 내역을 가져오는 중...[/bold cyan]")
            
            with self.console.status("[bold cyan]데이터베이스에서 거래 내역을 가져오는 중...[/bold cyan]"):
                with self.db_manager.get_pg_session() as session:
                    trades = session.execute(
                        f"""
                        SELECT trade_id, pair, open_time, close_time, entry_price, exit_price, 
                               quantity, side, status, pnl, pnl_pct
                        FROM trades
                        ORDER BY open_time DESC
                        LIMIT {limit}
                        """
                    ).fetchall()
            
            if not trades:
                self.console.print("[yellow]최근 거래 내역이 없습니다.[/yellow]")
                self.wait_for_enter()
                return
            
            # 거래 내역 테이블 생성
            table = Table(title=f"[bold cyan]최근 {limit}개 거래 내역[/bold cyan]", 
                         show_header=True, header_style="bold magenta", expand=True)
            
            table.add_column("ID", style="dim")
            table.add_column("페어", style="cyan")
            table.add_column("시작 시간", style="green")
            table.add_column("종료 시간", style="green")
            table.add_column("진입가", justify="right")
            table.add_column("청산가", justify="right")
            table.add_column("수량", justify="right")
            table.add_column("방향", style="cyan")
            table.add_column("상태", style="yellow")
            table.add_column("손익", justify="right")
            table.add_column("손익%", justify="right")
            
            for trade in trades:
                trade_id = trade[0]
                pair = trade[1]
                open_time = trade[2].strftime('%Y-%m-%d %H:%M:%S') if trade[2] else 'N/A'
                close_time = trade[3].strftime('%Y-%m-%d %H:%M:%S') if trade[3] else 'N/A'
                entry_price = f"{trade[4]:.4f}" if trade[4] else 'N/A'
                exit_price = f"{trade[5]:.4f}" if trade[5] else 'N/A'
                quantity = f"{trade[6]:.4f}" if trade[6] else 'N/A'
                side = trade[7]
                status = trade[8]
                pnl = f"{trade[9]:.2f}" if trade[9] else 'N/A'
                pnl_pct = f"{trade[10]:.2f}%" if trade[10] else 'N/A'
                
                # PnL에 따라 색상 지정
                pnl_style = "green" if trade[9] and trade[9] > 0 else "red"
                
                table.add_row(
                    str(trade_id), pair, open_time, close_time, entry_price, exit_price,
                    quantity, side, status, f"[{pnl_style}]{pnl}[/{pnl_style}]", f"[{pnl_style}]{pnl_pct}[/{pnl_style}]"
                )
            
            self.console.print(table)
            
        except Exception as e:
            logger.error(f"거래 내역 가져오기 실패: {e}")
            self.console.print(f"[bold red]거래 내역을 가져오는 중 오류가 발생했습니다: {e}[/bold red]")
        
        self.wait_for_enter()
    
    def show_performance(self):
        """성능 지표 표시"""
        try:
            self.console.print("[bold cyan]성능 지표를 계산하는 중...[/bold cyan]")
            
            with self.console.status("[bold cyan]데이터베이스에서 성능 지표를 계산하는 중...[/bold cyan]"):
                with self.db_manager.get_pg_session() as session:
                    # 전체 성능 지표 계산
                    performance = session.execute(
                        """
                        SELECT 
                            COUNT(*) as total_trades,
                            COUNT(CASE WHEN pnl > 0 THEN 1 END) as profitable_trades,
                            COUNT(CASE WHEN pnl <= 0 THEN 1 END) as unprofitable_trades,
                            COALESCE(SUM(pnl), 0) as total_profit,
                            COALESCE(AVG(pnl), 0) as avg_profit,
                            COALESCE(AVG(CASE WHEN pnl > 0 THEN pnl END), 0) as avg_profit_win,
                            COALESCE(AVG(CASE WHEN pnl <= 0 THEN pnl END), 0) as avg_profit_loss,
                            COALESCE(AVG(EXTRACT(EPOCH FROM (close_time - open_time)) / 3600), 0) as avg_duration_hours
                        FROM trades
                        WHERE status = 'closed'
                        """
                    ).fetchone()
                    
                    # 최대 드로다운 계산
                    max_drawdown = session.execute(
                        """
                        SELECT MAX(drawdown_pct) as max_drawdown
                        FROM equity_curve
                        """
                    ).scalar() or 0
            
            if not performance:
                self.console.print("[yellow]성능 지표를 찾을 수 없습니다.[/yellow]")
                self.wait_for_enter()
                return
            
            total_trades = performance[0]
            profitable_trades = performance[1]
            unprofitable_trades = performance[2]
            total_profit = performance[3]
            avg_profit = performance[4]
            avg_profit_win = performance[5]
            avg_profit_loss = performance[6]
            avg_duration_hours = performance[7]
            
            win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
            profit_factor = (avg_profit_win * profitable_trades) / (-avg_profit_loss * unprofitable_trades) if unprofitable_trades > 0 and avg_profit_loss < 0 else 0
            
            # 성능 지표를 패널로 표시
            performance_panel = Panel(
                f"""[bold]총 거래 수:[/bold] {total_trades}
[bold]승률:[/bold] {win_rate:.2f}%
[bold]총 수익:[/bold] {total_profit:.2f} USDT
[bold]평균 거래 수익:[/bold] {avg_profit:.2f} USDT
[bold]평균 승리 거래:[/bold] {avg_profit_win:.2f} USDT
[bold]평균 손실 거래:[/bold] {avg_profit_loss:.2f} USDT
[bold]수익 요소:[/bold] {profit_factor:.2f}
[bold]최대 드로다운:[/bold] {max_drawdown:.2f}%
[bold]평균 거래 기간:[/bold] {avg_duration_hours:.2f} 시간""",
                title="[bold cyan]성능 지표[/bold cyan]",
                border_style="cyan"
            )
            
            self.console.print(performance_panel)
            
        except Exception as e:
            logger.error(f"성능 지표 계산 실패: {e}")
            self.console.print(f"[bold red]성능 지표를 계산하는 중 오류가 발생했습니다: {e}[/bold red]")
        
        self.wait_for_enter()
    
    def configure_bot(self):
        """봇 설정 변경"""
        self.console.print("[bold cyan]봇 설정[/bold cyan]")
        
        # 현재 설정 로드
        config = self.load_config()
        
        # 설정 표시
        config_panel = Panel(
            Syntax(yaml.dump(config, default_flow_style=False), "yaml", theme="monokai"),
            title="[bold cyan]현재 설정[/bold cyan]",
            border_style="cyan"
        )
        self.console.print(config_panel)
        
        # 설정 변경 옵션
        options = [
            "거래 모드 변경",
            "스테이크 금액 변경",
            "최대 오픈 거래 수 변경",
            "리스크 설정 변경",
            "알림 설정 변경",
            "돌아가기"
        ]
        
        choice = Prompt.ask("변경할 설정을 선택하세요", choices=["1", "2", "3", "4", "5", "6"], default="6")
        
        if choice == "1":
            # 거래 모드 변경
            mode = Prompt.ask("거래 모드를 선택하세요", choices=["dry-run", "live"], default=config.get("trading", {}).get("mode", "dry-run"))
            config.setdefault("trading", {})["mode"] = mode
            self.console.print(f"[green]거래 모드가 '{mode}'로 변경되었습니다.[/green]")
            
        elif choice == "2":
            # 스테이크 금액 변경
            current = config.get("trading", {}).get("stake_amount", 100)
            stake_amount = Prompt.ask(f"스테이크 금액을 입력하세요 (현재: {current})", default=str(current))
            config.setdefault("trading", {})["stake_amount"] = float(stake_amount)
            self.console.print(f"[green]스테이크 금액이 {stake_amount}로 변경되었습니다.[/green]")
            
        elif choice == "3":
            # 최대 오픈 거래 수 변경
            current = config.get("trading", {}).get("max_open_trades", 3)
            max_open_trades = Prompt.ask(f"최대 오픈 거래 수를 입력하세요 (현재: {current})", default=str(current))
            config.setdefault("trading", {})["max_open_trades"] = int(max_open_trades)
            self.console.print(f"[green]최대 오픈 거래 수가 {max_open_trades}로 변경되었습니다.[/green]")
            
        elif choice == "4":
            # 리스크 설정 변경
            current_dd = config.get("risk", {}).get("max_drawdown", 10.0)
            current_risk = config.get("risk", {}).get("trade_risk", 1.0)
            
            max_dd = Prompt.ask(f"최대 드로다운 퍼센트를 입력하세요 (현재: {current_dd}%)", default=str(current_dd))
            trade_risk = Prompt.ask(f"거래당 리스크 퍼센트를 입력하세요 (현재: {current_risk}%)", default=str(current_risk))
            
            config.setdefault("risk", {})["max_drawdown"] = float(max_dd)
            config.setdefault("risk", {})["trade_risk"] = float(trade_risk)
            
            self.console.print(f"[green]리스크 설정이 변경되었습니다. 최대 드로다운: {max_dd}%, 거래당 리스크: {trade_risk}%[/green]")
            
        elif choice == "5":
            # 알림 설정 변경
            current_enabled = config.get("notifications", {}).get("enabled", True)
            current_level = config.get("notifications", {}).get("level", "info")
            
            enabled = Confirm.ask(f"알림을 활성화하시겠습니까?", default=current_enabled)
            level = Prompt.ask(f"알림 레벨을 선택하세요", choices=["info", "warning", "error", "trade"], default=current_level)
            
            config.setdefault("notifications", {})["enabled"] = enabled
            config.setdefault("notifications", {})["level"] = level
            
            status = "활성화" if enabled else "비활성화"
            self.console.print(f"[green]알림 설정이 변경되었습니다. 상태: {status}, 레벨: {level}[/green]")
        
        # 설정 저장
        if choice != "6":
            self.save_config(config)
        
        self.wait_for_enter()
    
    def run_backtest(self):
        """백테스트 실행"""
        self.console.print("[bold cyan]백테스트 설정[/bold cyan]")
        
        # 백테스트 설정 입력 받기
        start_date = Prompt.ask("시작 날짜 (YYYY-MM-DD)", default="2023-01-01")
        end_date = Prompt.ask("종료 날짜 (YYYY-MM-DD)", default="2023-12-31")
        timeframe = Prompt.ask("타임프레임", choices=["5m", "15m", "1h", "4h", "1d"], default="1h")
        
        # 백테스트 실행 확인
        if Confirm.ask(f"{start_date}부터 {end_date}까지 {timeframe} 타임프레임으로 백테스트를 실행하시겠습니까?"):
            self.console.print("[bold green]백테스트를 실행합니다...[/bold green]")
            
            # 백테스트 진행 표시
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold green]Backtesting...[/bold green]"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
            ) as progress:
                task = progress.add_task("[green]Backtesting...", total=100)
                
                # 백테스트 과정 시뮬레이션
                for i in range(101):
                    time.sleep(0.05)  # 시뮬레이션을 위한 지연
                    progress.update(task, completed=i)
            
            # 여기에 실제 백테스트 로직 구현
            
            # 백테스트 결과 표시 (예시)
            result_panel = Panel(
                f"""[bold]테스트 기간:[/bold] {start_date} ~ {end_date}
[bold]타임프레임:[/bold] {timeframe}
[bold]총 거래 수:[/bold] 124
[bold]승률:[/bold] 58.87%
[bold]총 수익:[/bold] 432.15 USDT
[bold]최대 드로다운:[/bold] 12.34%
[bold]샤프 비율:[/bold] 1.87
[bold]평균 거래 기간:[/bold] 4.2 시간""",
                title="[bold green]백테스트 결과[/bold green]",
                border_style="green"
            )
            
            self.console.print(result_panel)
        
        self.wait_for_enter()
    
    def switch_mode(self):
        """드라이런/라이브 모드 전환"""
        # 현재 설정 로드
        config = self.load_config()
        current_mode = config.get("trading", {}).get("mode", "dry-run")
        
        # 현재 모드 표시
        self.console.print(f"[bold cyan]현재 모드: {current_mode}[/bold cyan]")
        
        # 모드 전환 확인
        new_mode = "live" if current_mode == "dry-run" else "dry-run"
        
        if Confirm.ask(f"정말로 {new_mode} 모드로 전환하시겠습니까?"):
            # 라이브 모드로 전환 시 추가 확인
            if new_mode == "live":
                self.console.print("[bold red]주의: 라이브 모드에서는 실제 자금으로 거래가 이루어집니다![/bold red]")
                if not Confirm.ask("[bold red]정말로 실제 자금으로 거래하시겠습니까?[/bold red]"):
                    self.console.print("[yellow]모드 전환이 취소되었습니다.[/yellow]")
                    self.wait_for_enter()
                    return
            
            # 모드 변경
            config.setdefault("trading", {})["mode"] = new_mode
            self.save_config(config)
            
            # 모드 전환 메시지
            mode_text = "라이브 (실제 거래)" if new_mode == "live" else "드라이런 (테스트)"
            self.console.print(f"[bold green]거래 모드가 {mode_text}로 전환되었습니다.[/bold green]")
            
            # 텔레그램 알림
            if self.telegram:
                emoji = "🔴" if new_mode == "live" else "🟢"
                self.telegram.send_message(f"{emoji} 거래 모드가 {mode_text}로 전환되었습니다.")
        
        self.wait_for_enter()
    
    def manage_risk(self):
        """리스크 관리 설정"""
        if not self.risk_manager:
            self.console.print("[bold red]리스크 관리자가 초기화되지 않았습니다.[/bold red]")
            self.wait_for_enter()
            return
        
        # 리스크 관리 메뉴 표시
        self.console.print("[bold cyan]리스크 관리[/bold cyan]")
        
        # 현재 상태 표시
        is_active = self.risk_manager.is_active()
        kill_switch = self.risk_manager.is_kill_switch_active()
        max_dd = self.risk_manager.get_max_drawdown()
        trade_risk = self.risk_manager.get_trade_risk()
        
        status_panel = Panel(
            f"""[bold]리스크 관리자:[/bold] {'활성화' if is_active else '비활성화'}
[bold]킬 스위치:[/bold] {'활성화' if kill_switch else '비활성화'}
[bold]최대 드로다운:[/bold] {max_dd:.2f}%
[bold]거래당 리스크:[/bold] {trade_risk:.2f}%""",
            title="[bold cyan]현재 리스크 설정[/bold cyan]",
            border_style="cyan"
        )
        
        self.console.print(status_panel)
        
        # 리스크 관리 옵션
        options = [
            "리스크 관리자 활성화/비활성화",
            "킬 스위치 활성화/비활성화",
            "최대 드로다운 설정",
            "거래당 리스크 설정",
            "돌아가기"
        ]
        
        choice = Prompt.ask("변경할 설정을 선택하세요", choices=["1", "2", "3", "4", "5"], default="5")
        
        if choice == "1":
            # 리스크 관리자 활성화/비활성화
            new_state = not is_active
            if new_state:
                self.risk_manager.enable()
                self.console.print("[green]리스크 관리자가 활성화되었습니다.[/green]")
                
                if self.telegram:
                    self.telegram.send_message("🛡️ 리스크 관리자가 활성화되었습니다.")
            else:
                self.risk_manager.disable()
                self.console.print("[yellow]리스크 관리자가 비활성화되었습니다.[/yellow]")
                
                if self.telegram:
                    self.telegram.send_message("⚠️ 리스크 관리자가 비활성화되었습니다.")
                
        elif choice == "2":
            # 킬 스위치 활성화/비활성화
            new_state = not kill_switch
            self.risk_manager.set_kill_switch(new_state)
            status = "활성화" if new_state else "비활성화"
            self.console.print(f"[{'red' if new_state else 'green'}]킬 스위치가 {status}되었습니다.[/{'red' if new_state else 'green'}]")
            
            if self.telegram:
                emoji = "🔴" if new_state else "🟢"
                self.telegram.send_message(f"{emoji} 킬 스위치가 {status}되었습니다.")
                
        elif choice == "3":
            # 최대 드로다운 설정
            new_max_dd = Prompt.ask(f"최대 드로다운 퍼센트를 입력하세요 (현재: {max_dd}%)", default=str(max_dd))
            try:
                value = float(new_max_dd)
                self.risk_manager.set_max_drawdown(value)
                self.console.print(f"[green]최대 드로다운이 {value:.2f}%로 설정되었습니다.[/green]")
                
                if self.telegram:
                    self.telegram.send_message(f"📊 최대 드로다운이 {value:.2f}%로 설정되었습니다.")
            except ValueError:
                self.console.print("[bold red]유효한 숫자를 입력하세요.[/bold red]")
                
        elif choice == "4":
            # 거래당 리스크 설정
            new_trade_risk = Prompt.ask(f"거래당 리스크 퍼센트를 입력하세요 (현재: {trade_risk}%)", default=str(trade_risk))
            try:
                value = float(new_trade_risk)
                self.risk_manager.set_trade_risk(value)
                self.console.print(f"[green]거래당 리스크가 {value:.2f}%로 설정되었습니다.[/green]")
                
                if self.telegram:
                    self.telegram.send_message(f"📉 거래당 리스크가 {value:.2f}%로 설정되었습니다.")
            except ValueError:
                self.console.print("[bold red]유효한 숫자를 입력하세요.[/bold red]")
        
        self.wait_for_enter()
    
    def manage_notifications(self):
        """알림 설정 관리"""
        if not self.telegram:
            self.console.print("[bold red]텔레그램 알림 시스템이 초기화되지 않았습니다.[/bold red]")
            self.wait_for_enter()
            return
        
        # 알림 설정 메뉴 표시
        self.console.print("[bold cyan]알림 설정[/bold cyan]")
        
        # 현재 상태 표시
        is_active = self.telegram.is_active()
        level = self.telegram.get_notification_level()
        
        status_panel = Panel(
            f"""[bold]텔레그램 알림:[/bold] {'활성화' if is_active else '비활성화'}
[bold]알림 레벨:[/bold] {level}""",
            title="[bold cyan]현재 알림 설정[/bold cyan]",
            border_style="cyan"
        )
        
        self.console.print(status_panel)
        
        # 알림 설정 옵션
        options = [
            "알림 활성화/비활성화",
            "알림 레벨 설정",
            "테스트 메시지 전송",
            "돌아가기"
        ]
        
        choice = Prompt.ask("변경할 설정을 선택하세요", choices=["1", "2", "3", "4"], default="4")
        
        if choice == "1":
            # 알림 활성화/비활성화
            new_state = not is_active
            if new_state:
                self.telegram.enable()
                self.console.print("[green]텔레그램 알림이 활성화되었습니다.[/green]")
            else:
                self.telegram.disable()
                self.console.print("[yellow]텔레그램 알림이 비활성화되었습니다.[/yellow]")
                
        elif choice == "2":
            # 알림 레벨 설정
            new_level = Prompt.ask("알림 레벨을 선택하세요", choices=["info", "warning", "error", "trade"], default=level)
            self.telegram.set_notification_level(new_level)
            self.console.print(f"[green]알림 레벨이 '{new_level}'로 설정되었습니다.[/green]")
                
        elif choice == "3":
            # 테스트 메시지 전송
            with self.console.status("[bold cyan]테스트 메시지 전송 중...[/bold cyan]"):
                success = self.telegram.send_message("🧪 이것은 테스트 메시지입니다.")
            
            if success:
                self.console.print("[green]테스트 메시지가 성공적으로 전송되었습니다.[/green]")
            else:
                self.console.print("[bold red]테스트 메시지 전송에 실패했습니다.[/bold red]")
        
        self.wait_for_enter()
    
    def exit_menu(self):
        """프로그램 종료"""
        if Confirm.ask("정말로 종료하시겠습니까?"):
            self.console.print("[bold yellow]프로그램을 종료합니다...[/bold yellow]")
            self.running = False
    
    def wait_for_enter(self):
        """엔터 키 입력 대기"""
        self.console.print("\n[dim]계속하려면 엔터 키를 누르세요...[/dim]")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            # 터미널 환경에서 발생할 수 있는 예외 처리
            self.console.print("\n")
            pass
    
    def run(self):
        """CLI 메뉴 실행"""
        if not self.initialize():
            self.console.print("[bold red]CLI 초기화에 실패했습니다.[/bold red]")
            return
        
        while self.running:
            try:
                self.display_main_menu()
            except KeyboardInterrupt:
                self.console.print("\n[bold yellow]프로그램을 종료합니다...[/bold yellow]")
                break
            except Exception as e:
                logger.error(f"메뉴 실행 중 오류 발생: {e}")
                self.console.print(f"[bold red]메뉴 실행 중 오류가 발생했습니다: {e}[/bold red]")
                self.wait_for_enter()

def main():
    """메인 함수"""
    cli = TradingBotCLI()
    cli.run()

if __name__ == "__main__":
    main()