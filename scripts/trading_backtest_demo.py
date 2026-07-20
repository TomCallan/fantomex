import sys
import math
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[1]))

from fantomex.client import FantomexClient

# A helper to generate a mock Plotly chart spec for the equity curve
def generate_equity_curve_spec(steps, equity_values, prices):
    return {
        "data": [
            {
                "x": list(range(steps)),
                "y": equity_values,
                "type": "scatter",
                "mode": "lines",
                "name": "Portfolio Value ($)",
                "marker": { "color": "rgb(16, 185, 129)" }
            },
            {
                "x": list(range(steps)),
                "y": [p * (equity_values[0] / prices[0]) for p in prices],
                "type": "scatter",
                "mode": "lines",
                "name": "Benchmark (Buy & Hold)",
                "line": { "dash": "dash" },
                "marker": { "color": "rgb(156, 163, 175)" }
            }
        ],
        "layout": {
            "title": "Backtest Equity Curve vs Benchmark",
            "xaxis": { "title": "Trading Steps" },
            "yaxis": { "title": "Value ($)" }
        }
    }

# A helper to generate a mock Plotly chart spec for the orderbook depth
def generate_orderbook_depth_spec(bids, asks):
    # Sort bids descending, asks ascending
    bids = sorted(bids, key=lambda x: x[0], reverse=True)
    asks = sorted(asks, key=lambda x: x[0])
    
    # Calculate cumulative volumes
    cum_bid_vol = []
    running_bid = 0.0
    for price, size in bids:
        running_bid += size
        cum_bid_vol.append((price, running_bid))
        
    cum_ask_vol = []
    running_ask = 0.0
    for price, size in asks:
        running_ask += size
        cum_ask_vol.append((price, running_ask))
        
    # Reverse bids for left-to-right display (ascending price)
    cum_bid_vol = cum_bid_vol[::-1]
    
    bid_prices = [x[0] for x in cum_bid_vol]
    bid_vols = [x[1] for x in cum_bid_vol]
    
    ask_prices = [x[0] for x in cum_ask_vol]
    ask_vols = [x[1] for x in cum_ask_vol]
    
    return {
        "data": [
            {
                "x": bid_prices,
                "y": bid_vols,
                "type": "scatter",
                "mode": "lines",
                "fill": "tozeroy",
                "name": "Bids (Buy Orders)",
                "line": { "color": "rgb(16, 185, 129)" },
                "fillcolor": "rgba(16, 185, 129, 0.2)"
            },
            {
                "x": ask_prices,
                "y": ask_vols,
                "type": "scatter",
                "mode": "lines",
                "fill": "tozeroy",
                "name": "Asks (Sell Orders)",
                "line": { "color": "rgb(239, 68, 68)" },
                "fillcolor": "rgba(239, 68, 68, 0.2)"
            }
        ],
        "layout": {
            "title": "Orderbook Market Depth Chart",
            "xaxis": { "title": "Price ($)", "range": [min(bid_prices) - 5, max(ask_prices) + 5] },
            "yaxis": { "title": "Cumulative Volume" }
        }
    }


def run_backtest_simulation():
    print("Simulating a Moving Average Crossover strategy on BTC/USDT...")
    
    # Generate mock BTC/USDT price path
    steps = 100
    base_price = 60000.0
    prices = []
    current_price = base_price
    for i in range(steps):
        # random walk with trend
        change = (i * 0.1) + math.sin(i * 0.2) * 500.0 + (math.cos(i * 0.05) * 300.0)
        prices.append(current_price + change)
        
    # Moving Average calculations
    fast_period = 10
    slow_period = 30
    
    equity = 10000.0
    position = 0.0
    equity_curve = []
    trade_log = []
    
    # Backtest Loop
    for step in range(steps):
        price = prices[step]
        
        # Calculate MAs
        fast_ma = sum(prices[max(0, step - fast_period + 1):step + 1]) / min(step + 1, fast_period)
        slow_ma = sum(prices[max(0, step - slow_period + 1):step + 1]) / min(step + 1, slow_period)
        
        # Simple signal crossover
        if step > slow_period:
            prev_fast_ma = sum(prices[max(0, step - fast_period):step]) / fast_period
            prev_slow_ma = sum(prices[max(0, step - slow_period):step]) / slow_period
            
            # Golden Cross: Buy signal
            if prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma and position == 0:
                # Buy all-in
                position = equity / price
                equity = 0.0
                trade_log.append(f"Step-{step},BUY,{price:.2f},{position:.4f},0.00")
            
            # Death Cross: Sell signal
            elif prev_fast_ma >= prev_slow_ma and fast_ma < slow_ma and position > 0:
                # Sell all-in
                equity = position * price
                position = 0.0
                pnl = equity - 10000.0  # simplified
                trade_log.append(f"Step-{step},SELL,{price:.2f},{position:.4f},{pnl:.2f}")
                
        # Record portfolio value
        current_val = equity + (position * price)
        equity_curve.append(current_val)
        
    final_val = equity + (position * prices[-1])
    print(f"Simulation completed. Initial Capital: $10,000 | Final Value: ${final_val:.2f}")
    
    return prices, equity_curve, trade_log


def generate_mock_orderbook():
    mid_price = 61250.0
    # Bids (price, size) below mid
    bids = [(mid_price - 0.5 * i, 1.2 * i + math.sin(i) * 0.5) for i in range(1, 15)]
    # Asks (price, size) above mid
    asks = [(mid_price + 0.5 * i, 0.9 * i + math.cos(i) * 0.4) for i in range(1, 15)]
    return bids, asks


def main():
    # 1. Run Strategy Backtest
    prices, equity_curve, trade_log = run_backtest_simulation()
    
    # 2. Generate Orderbook Ladder
    bids, asks = generate_mock_orderbook()
    
    print("\nConnecting to Fantomex server...")
    with FantomexClient(base_url="http://127.0.0.1:8000") as client:
        with client.run(
            project_name="trading-strategies",
            run_name="ma-crossover-btc",
            params={
                "symbol": "BTC/USDT",
                "strategy": "MA_Crossover",
                "fast_period": 10,
                "slow_period": 30,
                "initial_capital": 10000.0
            },
            tags=["backtest", "sim", "crypto"]
        ) as run:
            
            # Log step-by-step portfolio values
            print("Logging step metrics (equity & returns)...")
            for step, val in enumerate(equity_curve):
                pnl_pct = ((val - 10000.0) / 10000.0) * 100.0
                run.log({"portfolio_value": val, "returns_pct": pnl_pct}, step=step)
                
            # Create and log trade log CSV
            print("Logging Trade Ledger CSV...")
            csv_path = Path("trade_ledger.csv")
            csv_content = "step,action,price,amount,cumulative_pnl\n" + "\n".join(trade_log)
            csv_path.write_text(csv_content)
            run.log_file(str(csv_path), type="trade_log")
            if csv_path.exists():
                csv_path.unlink()
                
            # Create and log orderbook JSON data
            print("Logging Orderbook L2 Snapshot...")
            orderbook_path = Path("orderbook_snapshot.json")
            orderbook_data = []
            for p, s in bids:
                orderbook_data.append({"side": "BID", "price": round(p, 2), "size": round(s, 4)})
            for p, s in asks:
                orderbook_data.append({"side": "ASK", "price": round(p, 2), "size": round(s, 4)})
                
            import json
            orderbook_path.write_text(json.dumps(orderbook_data, indent=2))
            run.log_file(str(orderbook_path), type="orderbook")
            if orderbook_path.exists():
                orderbook_path.unlink()
                
            # Create and log Equity Curve Plotly Chart
            print("Logging Equity Curve Chart...")
            equity_spec = generate_equity_curve_spec(len(prices), equity_curve, prices)
            run.log_plotly(equity_spec, name="equity_curve")
            
            # Create and log Orderbook Depth Chart
            print("Logging Orderbook Market Depth Chart...")
            depth_spec = generate_orderbook_depth_spec(bids, asks)
            run.log_plotly(depth_spec, name="orderbook_depth")
            
            print("\nSuccessfully logged quantitative trading runs and orderbook snapshot!")


if __name__ == "__main__":
    main()
