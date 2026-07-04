# Options & Futures Backtesting Engine & Web Dashboard

This repository contains a modular, high-frequency backtesting engine in Python designed to simulate options and futures trading strategies on historical data (1-second intervals). It features a **Config-Driven Architecture** (here `config.yaml`) and an interactive, real-time **Web Dashboard** to explore results.

---

## 1. Quick Start: Local Python Setup


### Prerequisites
Make sure you have **Python 3.8 to 3.12** installed on your system.

### Step 1. Initialize Virtual Environment
Create and activate a python virtual environment, and install dependencies:
```bash
# Create the virtual environment
python -m venv .venv

# Activate it (Linux/MacOS)
source .venv/bin/activate

# Install the required packages
pip install -r requirements.txt
```

### Step 2. Download the Dataset
Download the historical options and futures tick data from the Google Drive folder:
**[Download allData Dataset (Google Drive)](https://drive.google.com/file/d/1RvvX4jacGmhDNZ26LRjLqnhtIgkZowgq/view?usp=sharing)**

Once downloaded, extract/place the `allData/` folder directly in the root directory of this repository:
```text
mock_quantframe/
├── allData/
│   ├── NSE_20221101/
│   ├── NSE_20221102/
│   └── ...
├── app.py
├── config.yaml
└── ...
```

---

## 2. Running Simulations & Analyzing Results

You can configure date ranges, assets, and active strategies by editing `config.yaml`.

### Running Backtests (`main.py`)
To run backtests for all configured symbols and active strategies:
```bash
python main.py
```
* **What happens**: The engine loops second-by-second (09:15:00 to 15:30:00) through historical dates in `allData/`, simulates trades, tracks cash balance, handles rollover parameters, and saves results in `./results/`.
* **Output files created**:
  * `{symbol}_rolling_straddle_pnl.csv` / `{symbol}_rolling_straddle_trades.csv`
  * `{symbol}_buy_hold_futures_pnl.csv` / `{symbol}_buy_hold_futures_trades.csv`
  * `cumulative_pnl.png` (Static matplotlib overview plot)

### Analyzing Performance Table (`analyze.py`)
Once backtests are complete, calculate side-by-side performance metrics (Sharpe, Drawdowns, Win Rates) in the terminal:
```bash
python analyze.py
```
* **Expected Result**: Outputs a structured Markdown table comparing strategies and symbols, and saves `results/strategy_comparison.png` comparing the cumulative performance of all runs.

### Launching the Dashboard Website (`app.py`)
To start the interactive web application:
```bash
python app.py
```
* **Expected Result**: Starts a local Flask web server at **http://localhost:5000**.
* Open your browser and navigate to `http://localhost:5000` to view:
  * Interactive Cumulative PnL curves (zoom/pan enabled)
  * Daily profit breakdown and drawdown charts
  * Paginated, searchable trade logs
  * Multi-strategy performance overlays

---

## 3. Running with Docker

If you prefer to run inside a containerized environment (without installing python packages locally), you can use the provided Docker config.

### Running with Docker Compose (Recommended)
Make sure you have Docker and Docker Compose installed, then run:
```bash
docker compose up --build
```
* **What this does**: Builds the image using `Dockerfile`, mounts your local `allData/` and `results/` folders, and starts the Flask dashboard on **http://localhost:5000** immediately. The backtests (`main.py` and `analyze.py`) run in the background concurrently. New results will be loaded onto the website once the background simulation finishes.

### Running with Raw Docker CLI
Alternatively, you can build and run using raw docker commands:
```bash
# Build the docker image
docker build -t quantframe-backtester .

# Run the container (mounting allData and results, exposing port 5000)
docker run -p 5000:5000 \
  -v "$(pwd)/allData:/app/allData" \
  -v "$(pwd)/results:/app/results" \
  quantframe-backtester
```
Again, the website will start immediately at `http://localhost:5000`, while the simulation runs in the background.

### Optimizations and out-of-the-box ideas
* Using Arrow format for backtest results to speed up loading times for large datasets.
* Lazy loading of data.
* Config-driven engine for easier parameter changes and testing different strategies.

### Declaration
* The backtesting engine is designed to be modular and can be extended to support more strategies and assets.
* The app.py and the visualization code is ai-generated for faster development and prototyping.
* The ideas and optimization of the main engine in backtracking is mine but the code is ai-generated.


