import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import logging

def plot_results(nifty_pnl, bn_pnl, output_path):
    """
    Plots cumulative Mark-to-Market PnL for NIFTY and BANKNIFTY.
    """
    # Use standard styles or fallback
    try:
        plt.style.use('seaborn-v0_8-darkgrid')
    except:
        try:
            plt.style.use('seaborn-darkgrid')
        except:
            pass
            
    fig, ax = plt.subplots(figsize=(14, 7), dpi=300)
    
    # Format time for plotting
    nifty_pnl = nifty_pnl.copy()
    bn_pnl = bn_pnl.copy()
    
    # Set time index
    nifty_pnl['Time'] = pd.to_datetime(nifty_pnl['Time'])
    bn_pnl['Time'] = pd.to_datetime(bn_pnl['Time'])
    
    # Plotting NIFTY and BANKNIFTY
    ax.plot(nifty_pnl['Time'], nifty_pnl['MTM_PnL'], label='NIFTY Straddle PnL', color='#3b82f6', linewidth=1.5)
    ax.plot(bn_pnl['Time'], bn_pnl['MTM_PnL'], label='BANKNIFTY Straddle PnL', color='#10b981', linewidth=1.5)
    
    # Combine PnL for Total
    total_pnl = nifty_pnl.merge(bn_pnl, on='Time', suffixes=('_nifty', '_bn'))
    total_pnl['Total_PnL'] = total_pnl['MTM_PnL_nifty'] + total_pnl['MTM_PnL_bn']
    ax.plot(total_pnl['Time'], total_pnl['Total_PnL'], label='Total PnL (NIFTY + BANKNIFTY)', color='#f59e0b', linewidth=2, linestyle='--')

    ax.set_title('Cumulative Mark-to-Market PnL (Nov 2022)', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel('Date', fontsize=12, labelpad=10)
    ax.set_ylabel('PnL (Points/Currency Units)', fontsize=12, labelpad=10)
    
    # Formatter for X-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    fig.autofmt_xdate()
    
    ax.legend(frameon=True, facecolor='#f8fafc', edgecolor='#e2e8f0', fontsize=10)
    ax.grid(True, linestyle=':', alpha=0.6, color='#cbd5e1')
    
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    logging.info(f"Saved plot to {output_path}")

def plot_comparison(results_data, output_path):
    """
    Plots cumulative Mark-to-Market PnL comparison across strategies.
    """
    try:
        plt.style.use('seaborn-v0_8-darkgrid')
    except:
        try:
            plt.style.use('seaborn-darkgrid')
        except:
            pass
            
    fig, ax = plt.subplots(figsize=(14, 8), dpi=300)
    
    # Define colors and styles for each strategy
    styles = {
        'rolling_straddle': {
            'label_prefix': 'Rolling Straddle',
            'combined_color': '#2563eb',  # Blue
            'nifty_color': '#3b82f6',     # Light Blue
            'bn_color': '#60a5fa',        # Extra Light Blue
        },
        'buy_hold_futures': {
            'label_prefix': 'Buy & Hold Fut',
            'combined_color': '#d97706',  # Orange
            'nifty_color': '#f59e0b',     # Light Orange
            'bn_color': '#fbbf24',        # Extra Light Orange
        }
    }
    
    for strat_name, data in results_data.items():
        style = styles[strat_name]
        nifty_pnl = data['nifty_pnl_df'].copy()
        bn_pnl = data['bn_pnl_df'].copy()
        
        nifty_pnl['Time'] = pd.to_datetime(nifty_pnl['Time'])
        bn_pnl['Time'] = pd.to_datetime(bn_pnl['Time'])
        
        # Plot individual assets (dotted)
        ax.plot(nifty_pnl['Time'], nifty_pnl['MTM_PnL'], 
                label=f"{style['label_prefix']} (NIFTY)", 
                color=style['nifty_color'], linewidth=1, linestyle=':')
                
        ax.plot(bn_pnl['Time'], bn_pnl['MTM_PnL'], 
                label=f"{style['label_prefix']} (BANKNIFTY)", 
                color=style['bn_color'], linewidth=1, linestyle='-.')
        
        # Calculate and plot Combined
        merged = nifty_pnl.merge(bn_pnl, on='Time', suffixes=('_nifty', '_bn'))
        merged['Total_PnL'] = merged['MTM_PnL_nifty'] + merged['MTM_PnL_bn']
        
        ax.plot(merged['Time'], merged['Total_PnL'], 
                label=f"{style['label_prefix']} (Combined)", 
                color=style['combined_color'], linewidth=2.5, linestyle='-')

    ax.set_title('Strategy Cumulative Mark-to-Market PnL Comparison (Nov 2022)', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel('Date', fontsize=12, labelpad=10)
    ax.set_ylabel('PnL (Points/Currency Units)', fontsize=12, labelpad=10)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate()
    
    ax.legend(frameon=True, facecolor='#f8fafc', edgecolor='#e2e8f0', fontsize=9, loc='upper left', ncol=2)
    ax.grid(True, linestyle=':', alpha=0.6, color='#cbd5e1')
    
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    print(f"Saved comparison plot to {output_path}")
