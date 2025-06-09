"""
Strategy manager for loading and managing trading strategies.
This module handles the loading, configuration, and management of trading strategies.
"""
import logging
import importlib
import inspect
import os
import sys
import json
from typing import Dict, List, Optional, Any, Type, Union
from pathlib import Path
import pandas as pd

from src.strategy_engine.strategy_evaluator import StrategyEvaluator
from src.strategy_engine.nasos_strategy import NASOSStrategy

logger = logging.getLogger(__name__)


class StrategyManager:
    """
    Strategy manager for loading and managing trading strategies.
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the strategy manager.
        
        :param config_path: Path to the configuration file
        """
        self.config = {}
        self.strategies = {}
        self.active_strategy = None
        self.evaluator = None
        self.nasos_strategy = None
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> Dict:
        """
        Load configuration from a JSON file.
        
        :param config_path: Path to the configuration file
        :return: Configuration dictionary
        """
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            
            logger.info(f"Loaded configuration from {config_path}")
            
            # Initialize strategy evaluator with config
            self.evaluator = StrategyEvaluator(self.config)
            
            # Initialize NASOS strategy
            self.nasos_strategy = NASOSStrategy(self.config)
            
            # Load strategy if specified in config
            if 'strategy' in self.config:
                self.load_strategy(self.config['strategy'])
            
            return self.config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {}
    
    def load_strategy(self, strategy_name: str) -> bool:
        """
        Load a strategy by name.
        
        :param strategy_name: Name of the strategy to load
        :return: True if successful, False otherwise
        """
        try:
            # First try to load from user_data/strategies
            user_strategy_path = Path(os.getcwd()) / 'user_data' / 'strategies'
            sys.path.insert(0, str(user_strategy_path.parent))
            
            try:
                module = importlib.import_module(f"strategies.{strategy_name}")
                
                # Find the strategy class in the module
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and name == strategy_name:
                        self.strategies[strategy_name] = obj
                        self.active_strategy = strategy_name
                        logger.info(f"Loaded strategy {strategy_name} from user_data/strategies")
                        return True
            except ImportError:
                logger.warning(f"Strategy {strategy_name} not found in user_data/strategies")
            
            # If not found, try to load from built-in strategies
            try:
                module = importlib.import_module(f"src.strategies.{strategy_name}")
                
                # Find the strategy class in the module
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and name == strategy_name:
                        self.strategies[strategy_name] = obj
                        self.active_strategy = strategy_name
                        logger.info(f"Loaded strategy {strategy_name} from built-in strategies")
                        return True
            except ImportError:
                logger.error(f"Strategy {strategy_name} not found in built-in strategies")
            
            logger.error(f"Strategy {strategy_name} not found")
            return False
        except Exception as e:
            logger.error(f"Error loading strategy {strategy_name}: {e}")
            return False
    
    def get_strategy_parameters(self, strategy_name: str = None) -> Dict:
        """
        Get parameters for a specific strategy.
        
        :param strategy_name: Name of the strategy (default: active strategy)
        :return: Dictionary of strategy parameters
        """
        if strategy_name is None:
            strategy_name = self.active_strategy
        
        if strategy_name is None:
            logger.error("No active strategy")
            return {}
        
        # Check if parameters are in config
        if 'strategy_parameters' in self.config:
            return self.config.get('strategy_parameters', {})
        
        # Otherwise, use default parameters from strategy class
        if strategy_name in self.strategies:
            strategy_class = self.strategies[strategy_name]
            
            # Check if strategy has buy_params and sell_params
            params = {}
            if hasattr(strategy_class, 'buy_params'):
                params.update(strategy_class.buy_params)
            if hasattr(strategy_class, 'sell_params'):
                params.update(strategy_class.sell_params)
            
            return params
        
        return {}
    
# DEAD CODE:     def evaluate_strategy(self, dataframes: Dict[str, pd.DataFrame], strategy_name: str = None) -> Dict[str, Dict[str, Any]]:
        """
        Evaluate a strategy on the given dataframes.
        
        :param dataframes: Dictionary of dataframes for different timeframes
        :param strategy_name: Name of the strategy to evaluate (default: active strategy)
        :return: Dictionary with evaluation results
        """
        if strategy_name is None:
            strategy_name = self.active_strategy
        
        if strategy_name is None:
            logger.error("No active strategy")
            return {}
        
        if self.evaluator is None:
            logger.error("Strategy evaluator not initialized")
            return {}
        
        # Prepare dataframes with indicators
        prepared_dataframes = self.evaluator.prepare_dataframes(dataframes)
        
        # Get strategy parameters
        params = self.get_strategy_parameters(strategy_name)
        
        # Evaluate strategy
        if strategy_name == 'NASOSv5_mod3':
            if self.nasos_strategy is None:
                self.nasos_strategy = NASOSStrategy(self.config)
            return self.nasos_strategy.analyze_multi_timeframe(prepared_dataframes)
        else:
            logger.error(f"Evaluation for strategy {strategy_name} not implemented")
            return {}
    
    def check_slippage(self, symbol: str, current_price: float, signal_price: float) -> bool:
        """
        Check if the current price has excessive slippage compared to the signal price.
        
        :param symbol: Trading symbol
        :param current_price: Current price
        :param signal_price: Price at signal generation
        :return: True if trade is allowed, False otherwise
        """
        if self.evaluator is None:
            logger.error("Strategy evaluator not initialized")
            return False
        
        # Get slippage parameters from config
        slippage_config = self.config.get('slippage_protection', {})
        max_slippage = slippage_config.get('max_slippage', 0.05)
        max_retries = slippage_config.get('retries', 3)
        
        # Check slippage
        allow_trade, _ = self.evaluator.check_slippage(
            symbol, current_price, signal_price, max_slippage, max_retries
        )
        
        return allow_trade
    
    def list_available_strategies(self) -> List[str]:
        """
        List all available strategies.
        
        :return: List of strategy names
        """
        strategies = []
        
        # Check user_data/strategies directory
        user_strategy_path = Path(os.getcwd()) / 'user_data' / 'strategies'
        if user_strategy_path.exists():
            for file in user_strategy_path.glob('*.py'):
                if file.stem != '__init__':
                    strategies.append(file.stem)
        
        # Check built-in strategies
        builtin_strategy_path = Path(os.getcwd()) / 'src' / 'strategies'
        if builtin_strategy_path.exists():
            for file in builtin_strategy_path.glob('*.py'):
                if file.stem != '__init__' and file.stem not in strategies:
                    strategies.append(file.stem)
        
        return strategies
