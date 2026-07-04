import os
import pandas as pd
import numpy as np
from plot import plot_comparison

def calculate_metrics(pnl_path, trades_path):
    if not os.path.exists(pnl_path) or not os.path.exists(trades_path):
        return None
        
    pnl_df = pd.read_csv(pnl_path)
    trades_df = pd.read_csv(trades_path)
    
    # Parse timestamps
    pnl_df['Time'] = pd.to_datetime(pnl_df['Time'])
    pnl_df['Date'] = pnl_df['Time'].dt.date
    
    # Calculate Daily PnL
    daily_pnl = pnl_df.groupby('Date')['MTM_PnL'].last()
    daily_returns = daily_pnl.diff().fillna(daily_pnl.iloc[0])
    
    total_pnl = pnl_df['MTM_PnL'].iloc[-1]
    num_trades = len(trades_df)
    
    # Drawdown calculation
    pnl_series = pnl_df['MTM_PnL']
    peak = pnl_series.cummax()
    drawdown = peak - pnl_series
    max_dd = drawdown.max()
    
    # Daily metrics
    profitable_days = (daily_returns > 0).sum()
    total_days = len(daily_returns)
    win_rate = profitable_days / total_days if total_days > 0 else 0
    
    mean_daily = daily_returns.mean()
    std_daily = daily_returns.std()
    sharpe = (mean_daily / std_daily) * np.sqrt(252) if std_daily > 0 else 0
    
    return {
        'total_pnl': total_pnl,
        'max_dd': max_dd,
        'num_trades': num_trades,
        'win_rate': win_rate,
        'sharpe': sharpe,
        'daily_pnl': daily_pnl,
        'pnl_df': pnl_df
    }

import yaml

def main():
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        print("Configuration file config.yaml not found!")
        return

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    bt_config = config.get('backtest', {})
    results_dir = bt_config.get('results_dir', './results')
    symbols = bt_config.get('symbols', ['NIFTY', 'BANKNIFTY'])
    strategies = [s.get('name') for s in config.get('strategies', []) if s.get('enabled', True)]
    
    rows = []
    results_data = {}
    
    for strat in strategies:
        metrics_by_symbol = {}
        
        for symbol in symbols:
            pnl_path = os.path.join(results_dir, f"{symbol.lower()}_{strat}_pnl.csv")
            tr_path = os.path.join(results_dir, f"{symbol.lower()}_{strat}_trades.csv")
            
            metrics = calculate_metrics(pnl_path, tr_path)
            if metrics is not None:
                metrics_by_symbol[symbol] = metrics
                rows.append({
                    'Strategy': strat,
                    'Asset': symbol,
                    'Total PnL': f"{metrics['total_pnl']:.2f}",
                    'Max DD': f"{metrics['max_dd']:.2f}",
                    'Win Rate': f"{metrics['win_rate']*100:.2f}%",
                    'Sharpe': f"{metrics['sharpe']:.2f}",
                    'Trades': str(metrics['num_trades'])
                })
        
        if not metrics_by_symbol:
            print(f"Results for strategy '{strat}' not found. Please run main.py first.")
            continue
            
        # Store individual asset dfs for plotting if standard NIFTY/BANKNIFTY are present
        if 'NIFTY' in metrics_by_symbol and 'BANKNIFTY' in metrics_by_symbol:
            results_data[strat] = {
                'nifty_pnl_df': metrics_by_symbol['NIFTY']['pnl_df'],
                'bn_pnl_df': metrics_by_symbol['BANKNIFTY']['pnl_df']
            }
        
        # COMBINED metrics across all symbols
        if len(metrics_by_symbol) > 1:
            merged = None
            for symbol, metrics in metrics_by_symbol.items():
                pnl_df = metrics['pnl_df'][['Time', 'MTM_PnL']].copy()
                pnl_df.columns = ['Time', f'MTM_PnL_{symbol}']
                if merged is None:
                    merged = pnl_df
                else:
                    merged = pd.merge(merged, pnl_df, on='Time')
            
            if merged is not None:
                pnl_cols = [f'MTM_PnL_{sym}' for sym in metrics_by_symbol.keys()]
                merged['Total_PnL'] = merged[pnl_cols].sum(axis=1)
                
                pnl_series = merged['Total_PnL']
                peak = pnl_series.cummax()
                drawdown = peak - pnl_series
                comb_max_dd = drawdown.max()
                
                comb_pnl = sum(metrics['daily_pnl'] for metrics in metrics_by_symbol.values())
                comb_returns = comb_pnl.diff().fillna(comb_pnl.iloc[0])
                
                comb_profitable_days = (comb_returns > 0).sum()
                comb_total_days = len(comb_returns)
                comb_win_rate = comb_profitable_days / comb_total_days if comb_total_days > 0 else 0
                
                comb_mean_daily = comb_returns.mean()
                comb_std_daily = comb_returns.std()
                comb_sharpe = (comb_mean_daily / comb_std_daily) * np.sqrt(252) if comb_std_daily > 0 else 0
                comb_trades = sum(metrics['num_trades'] for metrics in metrics_by_symbol.values())
                comb_total_pnl = sum(metrics['total_pnl'] for metrics in metrics_by_symbol.values())
                
                rows.append({
                    'Strategy': strat,
                    'Asset': 'Combined',
                    'Total PnL': f"{comb_total_pnl:.2f}",
                    'Max DD': f"{comb_max_dd:.2f}",
                    'Win Rate': f"{comb_win_rate*100:.2f}%",
                    'Sharpe': f"{comb_sharpe:.2f}",
                    'Trades': str(comb_trades)
                })

    # Print comparison table manually in markdown format
    print("\n=== Backtest Performance Comparison ===")
    print(f"{'Strategy':<18} | {'Asset':<10} | {'Total PnL':>9} | {'Max DD':>8} | {'Win Rate':>8} | {'Sharpe':>6} | {'Trades':>6}")
    print("-" * 18 + "-|-" + "-" * 10 + "-|-" + "-" * 9 + "-|-" + "-" * 8 + "-|-" + "-" * 8 + "-|-" + "-" * 6 + "-|-" + "-" * 6)
    for r in rows:
        print(f"{r['Strategy']:<18} | {r['Asset']:<10} | {r['Total PnL']:>9} | {r['Max DD']:>8} | {r['Win Rate']:>8} | {r['Sharpe']:>6} | {r['Trades']:>6}")
    print("========================================\n")

    if len(results_data) == len(strategies):
        plot_comparison(results_data, os.path.join(results_dir, "strategy_comparison.png"))

if __name__ == "__main__":
    main()
