import os
import glob
import yaml
import math
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory, abort

app = Flask(__name__, static_folder="dashboard", static_url_path="")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")
RESULTS_DIR = os.path.join(BASE_DIR, "results")


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f) or {}


def discover_result_files():
    """Scan results/ and build a map of (strategy, symbol) -> {pnl, trades}."""
    pattern = os.path.join(RESULTS_DIR, "*_*_pnl.csv")
    found = {}
    for path in sorted(glob.glob(pattern)):
        fname = os.path.basename(path)           # e.g. nifty_rolling_straddle_pnl.csv
        parts = fname.replace("_pnl.csv", "").split("_", 1)  # ['nifty', 'rolling_straddle']
        if len(parts) != 2:
            continue
        symbol, strat = parts[0].upper(), parts[1]
        key = (strat, symbol)
        trades_path = path.replace("_pnl.csv", "_trades.csv")
        found[key] = {
            "pnl": path,
            "trades": trades_path if os.path.exists(trades_path) else None,
        }
    return found


def safe_float(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return 0.0
    return float(v)


def load_pnl_downsampled(path, freq="1min"):
    """Load a PnL CSV and resample to 1-minute resolution for the chart."""
    df = pd.read_csv(path, usecols=["Time", "MTM_PnL"], parse_dates=["Time"])
    df = df.dropna(subset=["Time", "MTM_PnL"])
    df = df.set_index("Time").sort_index()
    # Resample: take last value per minute (cumulative PnL)
    resampled = df["MTM_PnL"].resample(freq).last().dropna().reset_index()
    resampled.columns = ["time", "pnl"]
    # Convert to ISO strings for JSON
    resampled["time"] = resampled["time"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    return resampled


def compute_daily_pnl(path):
    """Compute per-day total PnL from the PnL CSV."""
    df = pd.read_csv(path, usecols=["Time", "MTM_PnL"], parse_dates=["Time"])
    df = df.dropna()
    df["date"] = df["Time"].dt.date
    # Last MTM value of each day is the day's total PnL
    daily = df.groupby("date")["MTM_PnL"].last().reset_index()
    daily.columns = ["date", "pnl"]
    # Compute day-over-day delta to get each day's contribution
    daily["daily_change"] = daily["pnl"].diff().fillna(daily["pnl"])
    daily["date"] = daily["date"].astype(str)
    return daily


def compute_metrics(pnl_path, trades_path):
    """Compute summary KPIs from result files."""
    if not os.path.exists(pnl_path):
        return None

    df = pd.read_csv(pnl_path, usecols=["Time", "MTM_PnL"], parse_dates=["Time"])
    df = df.dropna()
    df = df.set_index("Time").sort_index()

    total_pnl = safe_float(df["MTM_PnL"].iloc[-1]) if len(df) else 0.0

    # Max drawdown
    cummax = df["MTM_PnL"].cummax()
    drawdown = cummax - df["MTM_PnL"]
    max_dd = safe_float(drawdown.max())

    # Daily PnL
    df["date"] = df.index.date
    daily_last = df.groupby("date")["MTM_PnL"].last()
    daily_returns = daily_last.diff().fillna(daily_last.iloc[0] if len(daily_last) else 0)

    total_days = len(daily_returns)
    win_days = int((daily_returns > 0).sum())
    win_rate = (win_days / total_days * 100) if total_days > 0 else 0.0

    mean_ret = daily_returns.mean()
    std_ret = daily_returns.std()
    sharpe = safe_float((mean_ret / std_ret) * math.sqrt(252)) if std_ret and std_ret > 0 else 0.0

    num_trades = 0
    if trades_path and os.path.exists(trades_path):
        t = pd.read_csv(trades_path)
        num_trades = len(t)

    return {
        "total_pnl": round(total_pnl, 2),
        "max_dd": round(max_dd, 2),
        "win_rate": round(win_rate, 2),
        "sharpe": round(sharpe, 2),
        "win_days": win_days,
        "total_days": total_days,
        "num_trades": num_trades,
    }


# ──────────────────────────────────────────────
# API Routes
# ──────────────────────────────────────────────

@app.route("/api/strategies")
def api_strategies():
    """Return all discovered (strategy, symbol) combinations."""
    result_map = discover_result_files()
    strategies = sorted(set(k[0] for k in result_map))
    symbols = sorted(set(k[1] for k in result_map))
    combos = [{"strategy": s, "symbol": sym} for (s, sym) in sorted(result_map.keys())]
    return jsonify({
        "strategies": strategies,
        "symbols": symbols,
        "combinations": combos,
    })


@app.route("/api/pnl")
def api_pnl():
    """Return downsampled PnL time-series. ?strategy=&symbol=&freq="""
    strategy = request.args.get("strategy", "rolling_straddle").lower()
    symbol = request.args.get("symbol", "NIFTY").upper()
    freq = request.args.get("freq", "1min")

    fname = f"{symbol.lower()}_{strategy}_pnl.csv"
    path = os.path.join(RESULTS_DIR, fname)

    if not os.path.exists(path):
        abort(404, description=f"PnL file not found: {fname}")

    try:
        df = load_pnl_downsampled(path, freq=freq)
        return jsonify({
            "strategy": strategy,
            "symbol": symbol,
            "labels": df["time"].tolist(),
            "pnl": df["pnl"].tolist(),
        })
    except Exception as e:
        abort(500, description=str(e))


@app.route("/api/daily")
def api_daily():
    """Return per-day PnL breakdown. ?strategy=&symbol="""
    strategy = request.args.get("strategy", "rolling_straddle").lower()
    symbol = request.args.get("symbol", "NIFTY").upper()

    fname = f"{symbol.lower()}_{strategy}_pnl.csv"
    path = os.path.join(RESULTS_DIR, fname)

    if not os.path.exists(path):
        abort(404, description=f"PnL file not found: {fname}")

    try:
        daily = compute_daily_pnl(path)
        return jsonify({
            "strategy": strategy,
            "symbol": symbol,
            "dates": daily["date"].tolist(),
            "pnl": daily["pnl"].tolist(),
            "daily_change": daily["daily_change"].tolist(),
        })
    except Exception as e:
        abort(500, description=str(e))


@app.route("/api/trades")
def api_trades():
    """Return paginated trade log. ?strategy=&symbol=&page=&per_page="""
    strategy = request.args.get("strategy", "rolling_straddle").lower()
    symbol = request.args.get("symbol", "NIFTY").upper()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))

    fname = f"{symbol.lower()}_{strategy}_trades.csv"
    path = os.path.join(RESULTS_DIR, fname)

    if not os.path.exists(path):
        abort(404, description=f"Trades file not found: {fname}")

    try:
        df = pd.read_csv(path)
        total = len(df)
        start = (page - 1) * per_page
        end = start + per_page
        page_df = df.iloc[start:end]

        return jsonify({
            "strategy": strategy,
            "symbol": symbol,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": math.ceil(total / per_page),
            "trades": page_df.to_dict(orient="records"),
        })
    except Exception as e:
        abort(500, description=str(e))


@app.route("/api/metrics")
def api_metrics():
    """Return KPI summary. ?strategy=&symbol="""
    strategy = request.args.get("strategy", "rolling_straddle").lower()
    symbol = request.args.get("symbol", "NIFTY").upper()

    pnl_fname = f"{symbol.lower()}_{strategy}_pnl.csv"
    trades_fname = f"{symbol.lower()}_{strategy}_trades.csv"
    pnl_path = os.path.join(RESULTS_DIR, pnl_fname)
    trades_path = os.path.join(RESULTS_DIR, trades_fname)

    metrics = compute_metrics(pnl_path, trades_path)
    if metrics is None:
        abort(404, description=f"No results found for {strategy}/{symbol}")

    metrics["strategy"] = strategy
    metrics["symbol"] = symbol
    return jsonify(metrics)


@app.route("/api/compare")
def api_compare():
    """Return metrics for all strategies/symbols for comparison table."""
    result_map = discover_result_files()
    rows = []
    for (strat, symbol), paths in sorted(result_map.items()):
        m = compute_metrics(paths["pnl"], paths["trades"])
        if m:
            m["strategy"] = strat
            m["symbol"] = symbol
            rows.append(m)
    return jsonify(rows)


@app.route("/api/config")
def api_config():
    """Return the parsed config.yaml."""
    cfg = load_config()
    return jsonify(cfg)


# ──────────────────────────────────────────────
# Static frontend serving
# ──────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("dashboard", "index.html")


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": str(e)}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("🚀 Backtesting Dashboard running at http://localhost:5000")
    #app.run(debug=True, port=5000)
    app.run(host='0.0.0.0', port=5000, debug=True)