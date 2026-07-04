import os
import yaml
import pandas as pd
from backtester import Backtester
import strategy
from plot import plot_results
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_backtest(symbol, base_dir, start_date, end_date, strategy_cls, strategy_params=None):
    logging.info(f"Running backtest for {symbol} with strategy {strategy_cls.__name__}...")
    backtester = Backtester(base_dir, symbol, start_date, end_date, strategy_cls=strategy_cls, strategy_params=strategy_params)
    backtester.run()
    trades, pnl = backtester.get_results()
    return trades, pnl

def main():
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        logging.error("Configuration file config.yaml not found!")
        return

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    bt_config = config.get('backtest', {})
    start_date = str(bt_config.get('start_date', '20221101'))
    end_date = str(bt_config.get('end_date', '20221130'))
    base_dir = bt_config.get('base_dir', './allData')
    results_dir = bt_config.get('results_dir', './results')
    symbols = bt_config.get('symbols', ['NIFTY', 'BANKNIFTY'])

    os.makedirs(results_dir, exist_ok=True)

    enabled_strategies = [s for s in config.get('strategies', []) if s.get('enabled', True)]

    for strat_cfg in enabled_strategies:
        strat_name = strat_cfg.get('name')
        class_name = strat_cfg.get('class')
        params = strat_cfg.get('parameters', {})

        logging.info(f"====== Starting Backtest for Configured Strategy: {strat_name} ======")
        
        try:
            strategy_cls = getattr(strategy, class_name)
        except AttributeError:
            logging.error(f"Strategy class {class_name} not found in strategy.py! Skipping.")
            continue

        for symbol in symbols:
            trades, pnl = run_backtest(symbol, base_dir, start_date, end_date, strategy_cls, params)
            
            # Save strategy-specific outputs
            trades_path = os.path.join(results_dir, f"{symbol.lower()}_{strat_name}_trades.csv")
            pnl_path = os.path.join(results_dir, f"{symbol.lower()}_{strat_name}_pnl.csv")
            
            trades.to_csv(trades_path, index=False)
            pnl.to_csv(pnl_path, index=False)
            logging.info(f"Saved results to {pnl_path} and {trades_path}")

            # For backwards compatibility with standard single-strategy runs
            if strat_name == "rolling_straddle":
                trades.to_csv(os.path.join(results_dir, f"{symbol.lower()}_trades.csv"), index=False)
                pnl.to_csv(os.path.join(results_dir, f"{symbol.lower()}_pnl.csv"), index=False)

    # Plot default results if they were generated
    nifty_default_pnl_path = os.path.join(results_dir, "nifty_pnl.csv")
    bn_default_pnl_path = os.path.join(results_dir, "banknifty_pnl.csv")
    if os.path.exists(nifty_default_pnl_path) and os.path.exists(bn_default_pnl_path):
        n_pnl = pd.read_csv(nifty_default_pnl_path)
        bn_pnl = pd.read_csv(bn_default_pnl_path)
        plot_results(n_pnl, bn_pnl, os.path.join(results_dir, "cumulative_pnl.png"))

if __name__ == "__main__":
    main()
