import os
import pandas as pd
from datetime import datetime
from data_handler import DataHandler
from portfolio import Portfolio
from strategy import SimpleStraddleStrategy
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class Backtester:
    def __init__(self, base_dir, symbol, start_date, end_date, strategy_cls=SimpleStraddleStrategy, strategy_params=None):
        self.base_dir = base_dir
        self.symbol = symbol
        self.strategy_cls = strategy_cls
        self.strategy_params = strategy_params or {}
        # Find all available date directories
        all_dirs = [d for d in os.listdir(base_dir) if d.startswith('NSE_') and os.path.isdir(os.path.join(base_dir, d))]
        dates = sorted([d.replace('NSE_', '') for d in all_dirs])
        # Filter by date range
        self.trading_dates = [d for d in dates if start_date <= d <= end_date]
        
        self.portfolio = Portfolio()
        
    def run(self):
        for date_str in self.trading_dates:
            logging.info(f"Starting backtest for {self.symbol} on {date_str}")
            data_handler = DataHandler(self.base_dir, self.symbol, date_str)
            try:
                data_handler.load_data()
            except ValueError as e:
                logging.warning(f"Skipping {date_str}: {e}")
                continue
                
            strategy = self.strategy_cls(self.portfolio, data_handler, params=self.strategy_params)
            strategy.on_day_start(date_str)
            
            for time_val in data_handler.time_index:
                current_dt = datetime.combine(data_handler.date, time_val)
                strategy.on_tick(time_val, timestamp=current_dt)
                # Calculate MTM at each second, save with full datetime
                self.portfolio.calculate_mtm(time_val, data_handler, timestamp=current_dt)
                
            # End of day processing
            last_time = data_handler.time_index[-1]
            last_dt = datetime.combine(data_handler.date, last_time)
            strategy.on_day_end(date_str, last_time, timestamp=last_dt)
            
        logging.info(f"Backtest for {self.symbol} completed.")
        
    def get_results(self):
        # Convert trade history and pnl history to DataFrames
        trades_df = pd.DataFrame(self.portfolio.trade_history)
        pnl_df = pd.DataFrame(self.portfolio.pnl_history)
        return trades_df, pnl_df
