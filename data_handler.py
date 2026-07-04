import os
import pandas as pd
from datetime import datetime, time
import glob
import re
import warnings
import logging

# Suppress pandas FutureWarnings related to ffill
warnings.simplefilter(action='ignore', category=FutureWarning)

class DataHandler:
    def __init__(self, base_dir, symbol, date_str):
        self.base_dir = base_dir
        self.symbol = symbol
        self.date_str = date_str
        self.date = datetime.strptime(date_str, '%Y%m%d').date()
        self.day_dir = os.path.join(self.base_dir, f"NSE_{self.date_str}")
        self.futures_dir = os.path.join(self.day_dir, "Futures (Continuous)")
        self.options_dir = os.path.join(self.day_dir, "Options")
        
        self.futures_data = None
        self.options_data = {} # filename -> DataFrame (loaded dynamically)
        self.option_file_map = {} # filename -> filepath
        self.available_strikes = []
        self.expiry = None
        
        # 1-second index for the trading day
        self.time_index = pd.date_range(f"{self.date_str} 09:15:00", f"{self.date_str} 15:30:00", freq='s').time
        
    def load_data(self):
        # Load Futures
        fut_file = os.path.join(self.futures_dir, f"{self.symbol}-I.csv")
        self.futures_data = self._load_and_reindex(fut_file)
        
        # Determine closest expiry
        self.expiry = self._get_closest_expiry()
        
        # Load Options for this expiry
        opt_files = glob.glob(os.path.join(self.options_dir, f"{self.symbol}{self.expiry}*.csv"))
        strikes = set()
        for f in opt_files:
            basename = os.path.basename(f)
            # symbol + expiry + strike + type + .csv
            match = re.match(rf"{self.symbol}{self.expiry}(\d+)(CE|PE)\.csv", basename)
            if match:
                strike = int(match.group(1))
                strikes.add(strike)
                symbol_name = basename.replace('.csv', '')
                self.option_file_map[symbol_name] = f
                
        self.available_strikes = sorted(list(strikes))
        
    def _get_closest_expiry(self):
        files = glob.glob(os.path.join(self.options_dir, f"{self.symbol}*.csv"))
        expiries = set()
        for f in files:
            basename = os.path.basename(f)
            # Extract YYMMDD after symbol
            match = re.match(rf"{self.symbol}(\d{{6}}).*", basename)
            if match:
                expiry_str = match.group(1)
                # Convert YYMMDD to date object to compare
                expiry_date = datetime.strptime(expiry_str, '%y%m%d').date()
                if expiry_date >= self.date:
                    expiries.add(expiry_str)
        if not expiries:
            raise ValueError(f"No valid expiry found for {self.symbol} on {self.date_str}")
        
        # Find minimum expiry date
        closest_expiry = min(expiries, key=lambda x: datetime.strptime(x, '%y%m%d').date())
        return closest_expiry
        
    def _load_and_reindex(self, filepath):
        if not os.path.exists(filepath):
            return None
        
        parquet_filepath = filepath.replace('.csv', '.parquet')
        
        df = None
        if os.path.exists(parquet_filepath):
            try:
                df = pd.read_parquet(parquet_filepath)
            except Exception as e:
                # If parquet is corrupted or fails to read, delete it and fallback to CSV
                logging.warning(f"Error reading parquet cache {parquet_filepath}: {e}. Rebuilding from CSV.")
                try:
                    os.remove(parquet_filepath)
                except:
                    pass
                df = None
                
        if df is None:
            # Date, Time, Price, Volume, Open Interest
            df = pd.read_csv(filepath, header=None, names=['Date', 'Time', 'Price', 'Volume', 'OI'], dtype={'Time': str})
            
            # Downcast numeric columns to save memory and processing time
            df['Price'] = df['Price'].astype('float32')
            df['Volume'] = df['Volume'].astype('int32')
            df['OI'] = df['OI'].astype('int32')
            
            # Convert Time string to datetime.time
            df['Time'] = pd.to_datetime(df['Time'], format='%H:%M:%S').dt.time
            
            # Take the last traded price for each second if multiple exist
            df = df.groupby('Time').last()
            
            # Save processed data to parquet atomically using temp file and rename
            tmp_parquet = parquet_filepath + f".tmp.{os.getpid()}"
            try:
                df.to_parquet(tmp_parquet)
                os.replace(tmp_parquet, parquet_filepath)
            except Exception as e:
                logging.warning(f"Failed to cache parquet file: {e}")
                if os.path.exists(tmp_parquet):
                    try:
                        os.remove(tmp_parquet)
                    except:
                        pass
            
        # Reindex to full second-by-second timeline
        df = df.reindex(self.time_index)
        
        # Forward fill prices
        df['Price'] = df['Price'].ffill()
        
        return df

    def get_futures_price(self, time_val):
        try:
            return self.futures_data.loc[time_val, 'Price']
        except KeyError:
            return None

    def get_option_price(self, symbol_name, time_val):
        if symbol_name not in self.options_data and symbol_name in self.option_file_map:
            # Lazy load the data
            filepath = self.option_file_map[symbol_name]
            self.options_data[symbol_name] = self._load_and_reindex(filepath)

        if symbol_name in self.options_data:
            try:
                df = self.options_data[symbol_name]
                if df is not None:
                    return df.loc[time_val, 'Price']
            except KeyError:
                return None
        return None
        
    def get_closest_strike(self, price):
        if not self.available_strikes:
            return None
        # Find strike with minimum absolute difference
        closest_strike = min(self.available_strikes, key=lambda x: abs(x - price))
        return closest_strike
        
    def get_option_symbol(self, strike, opt_type):
        return f"{self.symbol}{self.expiry}{strike}{opt_type}"
