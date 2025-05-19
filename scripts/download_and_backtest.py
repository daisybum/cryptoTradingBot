#!/usr/bin/env python3
"""
Script to download historical data and run backtests for multiple cryptocurrency pairs.
"""
import os
import sys
import json
import subprocess
import pandas as pd
from datetime import datetime
from pathlib import Path

# Ensure we're in the project root directory
project_root = Path(__file__).parent.parent.absolute()
os.chdir(project_root)

# Load backtest configuration
config_path = os.path.join(project_root, 'config', 'backtest_config.json')
with open(config_path, 'r') as f:
    config = json.load(f)

# Extract pairs from config
pairs = [pair.replace('/', '_') for pair in config['exchange']['pair_whitelist']]
timeframes = ['5m', '15m', '1h']  # Required timeframes for the NASOS strategy

def download_data():
    """Download historical data for all pairs and timeframes."""
    print("Downloading historical data for 2024...")
    
    # Create data directory if it doesn't exist
    data_dir = os.path.join(project_root, 'user_data', 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Set start and end dates for 2024
    start_date = "20240101"
    end_date = "20241231"  # We'll get data up to the current date
    
    # Download data for each pair and timeframe
    for pair in pairs:
        for timeframe in timeframes:
            print(f"Downloading {pair} {timeframe} data...")
            cmd = [
                "freqtrade", "download-data",
                "--exchange", "binance",
                "--pairs", pair.replace('_', '/'),
                "--timeframes", timeframe,
                "--timerange", f"{start_date}-{end_date}",
                "--datadir", os.path.join(project_root, 'user_data', 'data')
            ]
            
            try:
                subprocess.run(cmd, check=True)
                print(f"Successfully downloaded {pair} {timeframe} data")
            except subprocess.CalledProcessError as e:
                print(f"Error downloading {pair} {timeframe} data: {e}")

def run_backtest():
    """Run backtests for all pairs."""
    print("Running backtests for 2024...")
    
    # Set timerange for 2024
    timerange = "20240101-"
    
    # Run backtest
    cmd = [
        "freqtrade", "backtesting",
        "--config", config_path,
        "--strategy", "NASOSv5_mod3",
        "--timerange", timerange,
        "--timeframe", "5m",
        "--export", "trades",
        "--export-filename", os.path.join(project_root, 'user_data', 'backtest_results', 'backtest_2024.json')
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("Backtest completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error running backtest: {e}")

def analyze_results():
    """Analyze backtest results and generate comprehensive metrics."""
    print("Analyzing backtest results...")
    
    # Load backtest results
    results_path = os.path.join(project_root, 'user_data', 'backtest_results', 'backtest_2024.json')
    
    if not os.path.exists(results_path):
        print(f"Error: Backtest results file not found at {results_path}")
        return
    
    with open(results_path, 'r') as f:
        results = json.load(f)
    
    # Extract trades
    trades = results.get('trades', [])
    
    if not trades:
        print("No trades found in backtest results")
        return
    
    # Convert to DataFrame
    trades_df = pd.DataFrame(trades)
    
    # Group by pair
    pair_metrics = {}
    
    for pair, group in trades_df.groupby('pair'):
        # Calculate metrics
        total_trades = len(group)
        winning_trades = len(group[group['profit_ratio'] > 0])
        losing_trades = len(group[group['profit_ratio'] <= 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Calculate average profit and loss
        avg_profit = group[group['profit_ratio'] > 0]['profit_ratio'].mean() if winning_trades > 0 else 0
        avg_loss = group[group['profit_ratio'] <= 0]['profit_ratio'].mean() if losing_trades > 0 else 0
        
        # Calculate total profit
        total_profit = group['profit_ratio'].sum()
        
        # Calculate max drawdown
        cumulative_returns = (1 + group['profit_ratio']).cumprod()
        max_return = cumulative_returns.cummax()
        drawdown = (cumulative_returns / max_return - 1)
        max_drawdown = drawdown.min() if not drawdown.empty else 0
        
        # Calculate Sharpe ratio (simplified)
        returns = group['profit_ratio']
        sharpe_ratio = returns.mean() / returns.std() if returns.std() > 0 else 0
        
        # Store metrics
        pair_metrics[pair] = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'total_profit': total_profit,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio
        }
    
    # Calculate overall metrics
    total_trades = len(trades_df)
    winning_trades = len(trades_df[trades_df['profit_ratio'] > 0])
    losing_trades = len(trades_df[trades_df['profit_ratio'] <= 0])
    win_rate = winning_trades / total_trades if total_trades > 0 else 0
    
    avg_profit = trades_df[trades_df['profit_ratio'] > 0]['profit_ratio'].mean() if winning_trades > 0 else 0
    avg_loss = trades_df[trades_df['profit_ratio'] <= 0]['profit_ratio'].mean() if losing_trades > 0 else 0
    
    total_profit = trades_df['profit_ratio'].sum()
    
    # Calculate max drawdown for overall portfolio
    cumulative_returns = (1 + trades_df['profit_ratio']).cumprod()
    max_return = cumulative_returns.cummax()
    drawdown = (cumulative_returns / max_return - 1)
    max_drawdown = drawdown.min() if not drawdown.empty else 0
    
    # Calculate Sharpe ratio (simplified)
    returns = trades_df['profit_ratio']
    sharpe_ratio = returns.mean() / returns.std() if returns.std() > 0 else 0
    
    # Generate report
    report = {
        'overall': {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'total_profit': total_profit,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio
        },
        'pairs': pair_metrics
    }
    
    # Save report
    report_path = os.path.join(project_root, 'user_data', 'backtest_results', 'backtest_2024_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=4)
    
    print(f"Backtest analysis report saved to {report_path}")
    
    # Print summary
    print("\n=== BACKTEST SUMMARY ===")
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2%}")
    print(f"Total Profit: {total_profit:.2%}")
    print(f"Max Drawdown: {max_drawdown:.2%}")
    print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
    print("\nTop 5 Performing Pairs:")
    
    # Sort pairs by total profit
    sorted_pairs = sorted(pair_metrics.items(), key=lambda x: x[1]['total_profit'], reverse=True)
    
    for pair, metrics in sorted_pairs[:5]:
        print(f"{pair}: {metrics['total_profit']:.2%} profit, {metrics['win_rate']:.2%} win rate, {metrics['total_trades']} trades")
    
    print("\nBottom 5 Performing Pairs:")
    for pair, metrics in sorted_pairs[-5:]:
        print(f"{pair}: {metrics['total_profit']:.2%} profit, {metrics['win_rate']:.2%} win rate, {metrics['total_trades']} trades")

def main():
    """Main function to run the download and backtest process."""
    print("Starting download and backtest process...")
    
    # Download data
    download_data()
    
    # Run backtest
    run_backtest()
    
    # Analyze results
    analyze_results()
    
    print("Process completed.")

if __name__ == "__main__":
    main()
