import math
from collections import defaultdict

class Portfolio:
    def __init__(self):
        self.positions = defaultdict(int) # symbol -> qty
        self.cash = 0.0
        self.trade_history = []
        self.pnl_history = [] # list of dicts: {'Time': time, 'MTM_PnL': pnl}

    def buy(self, time_val, symbol, qty, price, timestamp=None):
        if price is None or math.isnan(price):
            return
        self.positions[symbol] += qty
        cost = qty * price
        self.cash -= cost
        ts = timestamp if timestamp else time_val
        self.trade_history.append({'Time': ts, 'Action': 'BUY', 'Symbol': symbol, 'Qty': qty, 'Price': price})

    def sell(self, time_val, symbol, qty, price, timestamp=None):
        if price is None or math.isnan(price):
            return
        self.positions[symbol] -= qty
        revenue = qty * price
        self.cash += revenue
        ts = timestamp if timestamp else time_val
        self.trade_history.append({'Time': ts, 'Action': 'SELL', 'Symbol': symbol, 'Qty': qty, 'Price': price})
        
    def get_position(self, symbol):
        return self.positions.get(symbol, 0)
        
    def get_all_positions(self):
        return {k: v for k, v in self.positions.items() if v != 0}

    def close_all_positions(self, time_val, data_handler, timestamp=None):
        positions_to_close = self.get_all_positions()
        for symbol, qty in positions_to_close.items():
            if symbol.endswith('-I'):
                price = data_handler.get_futures_price(time_val)
            else:
                price = data_handler.get_option_price(symbol, time_val)
            if price is not None and not math.isnan(price):
                if qty > 0:
                    self.sell(time_val, symbol, qty, price, timestamp=timestamp)
                elif qty < 0:
                    self.buy(time_val, symbol, -qty, price, timestamp=timestamp)

    def calculate_mtm(self, time_val, data_handler, timestamp=None):
        mtm_value = self.cash
        for symbol, qty in self.positions.items():
            if qty == 0:
                continue
            if symbol.endswith('-I'):
                price = data_handler.get_futures_price(time_val)
            else:
                price = data_handler.get_option_price(symbol, time_val)
            if price is not None and not math.isnan(price):
                mtm_value += qty * price
                
        ts = timestamp if timestamp else time_val
        self.pnl_history.append({
            'Time': ts, 
            'MTM_PnL': mtm_value, 
            'Holdings': str(self.get_all_positions())
        })
        return mtm_value
