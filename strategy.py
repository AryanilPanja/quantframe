import math
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    def __init__(self, portfolio, data_handler, params=None):
        self.portfolio = portfolio
        self.data_handler = data_handler
        self.params = params or {}

    @abstractmethod
    def on_tick(self, time_val):
        pass

    def on_day_start(self, date_str):
        pass

    def on_day_end(self, date_str, time_val):
        pass

class SimpleStraddleStrategy(BaseStrategy):
    def __init__(self, portfolio, data_handler, params=None):
        super().__init__(portfolio, data_handler, params)
        self.current_strike = None
        self.held_ce = None
        self.held_pe = None
        self.qty = self.params.get('qty', 1)

    def on_tick(self, time_val, timestamp=None):
        fut_price = self.data_handler.get_futures_price(time_val)
        if fut_price is None or math.isnan(fut_price):
            return

        target_strike = self.data_handler.get_closest_strike(fut_price)
        if target_strike is None:
            return

        if self.current_strike != target_strike:
            # Roll position
            # 1. Close existing positions
            if self.held_ce is not None:
                ce_price = self.data_handler.get_option_price(self.held_ce, time_val)
                self.portfolio.sell(time_val, self.held_ce, self.qty, ce_price, timestamp=timestamp)
            if self.held_pe is not None:
                pe_price = self.data_handler.get_option_price(self.held_pe, time_val)
                self.portfolio.sell(time_val, self.held_pe, self.qty, pe_price, timestamp=timestamp)

            # 2. Open new positions
            target_ce = self.data_handler.get_option_symbol(target_strike, 'CE')
            target_pe = self.data_handler.get_option_symbol(target_strike, 'PE')

            ce_price = self.data_handler.get_option_price(target_ce, time_val)
            pe_price = self.data_handler.get_option_price(target_pe, time_val)

            # We will only record the position if the price is valid
            if ce_price is not None and not math.isnan(ce_price):
                self.portfolio.buy(time_val, target_ce, self.qty, ce_price, timestamp=timestamp)
                self.held_ce = target_ce
            else:
                self.held_ce = None
                
            if pe_price is not None and not math.isnan(pe_price):
                self.portfolio.buy(time_val, target_pe, self.qty, pe_price, timestamp=timestamp)
                self.held_pe = target_pe
            else:
                self.held_pe = None

            self.current_strike = target_strike

    def on_day_end(self, date_str, time_val, timestamp=None):
        # Close all positions
        self.portfolio.close_all_positions(time_val, self.data_handler, timestamp=timestamp)
        self.current_strike = None
        self.held_ce = None
        self.held_pe = None

class BuyAndHoldFuturesStrategy(BaseStrategy):
    def __init__(self, portfolio, data_handler, params=None):
        super().__init__(portfolio, data_handler, params)
        self.fut_symbol = f"{self.data_handler.symbol}-I"
        self.entered = False
        self.qty = self.params.get('qty', 1)

    def on_tick(self, time_val, timestamp=None):
        if self.entered:
            return
        
        fut_price = self.data_handler.get_futures_price(time_val)
        if fut_price is None or math.isnan(fut_price):
            return

        # Buy Future contract once at the start of the day
        self.portfolio.buy(time_val, self.fut_symbol, self.qty, fut_price, timestamp=timestamp)
        self.entered = True

    def on_day_end(self, date_str, time_val, timestamp=None):
        self.portfolio.close_all_positions(time_val, self.data_handler, timestamp=timestamp)
        self.entered = False
