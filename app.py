import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import io

# --- Page Configuration ---
st.set_page_config(page_title="Stock Risk Simulator", layout="wide")

st.title("📈 Stock Risk Monte Carlo Simulator")
st.markdown("""
This platform helps you understand investment risk by simulating thousands of possible future price paths based on historical volatility.
""")

# --- Sidebar Inputs ---
st.sidebar.header("Simulation Parameters")
ticker = st.sidebar.text_input("Stock Ticker (e.g., AAPL, TSLA, BTC-USD)", value="AAPL").upper()
investment = st.sidebar.number_input("Investment Amount ($)", min_value=10.0, value=1000.0, step=100.0)
time_horizon = st.sidebar.slider("Time Horizon (Days to Predict)", min_value=10, max_value=756, value=252)
iterations = st.sidebar.slider("Number of Simulations", min_value=100, max_value=5000, value=1000)

start_sim = st.sidebar.button("🚀 START SIMULATION")

# --- Simulation Logic ---
if start_sim:
    with st.spinner(f'Fetching data and running {iterations} simulations...'):
        # 1. Fetch Data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*2) # 2 years of data for better volatility estimates
        data = yf.download(ticker, start=start_date, end=end_date)
        
        if data.empty:
            st.error("Could not find data for that ticker. Please try a valid symbol (e.g., MSFT).")
        else:
            # 2. Calculate Returns and Volatility
            returns = data['Close'].pct_change().dropna()
            mu = returns.mean().values[0]
            sigma = returns.std().values[0]
            last_price = data['Close'].iloc[-1].values[0]

            # 3. Monte Carlo Simulation
            # Generate random daily returns based on historical mean and std dev
            daily_res = np.random.normal(mu, sigma, (time_horizon, iterations))
            
            # Create price paths
            price_paths = np.zeros_like(daily_res)
            price_paths[0] = last_price * (1 + daily_res[0])
            for t in range(1, time_horizon):
                price_paths[t] = price_paths[t-1] * (1 + daily_res[t])

            # Scale to investment amount
            portfolio_paths = (price_paths / last_price) * investment
            final_values = portfolio_paths[-1]

            # --- Layout: Charts & Stats ---
            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader("Simulated Price Paths")
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.plot(portfolio_paths, color='royalblue', alpha=0.03) # Faint lines for simulations
                ax.plot(np.mean(portfolio_paths, axis=1), color='red', linewidth=2, label='Average Path')
                ax.set_ylabel("Portfolio Value ($)")
                ax.set_xlabel("Days into Future")
                ax.grid(True, alpha=0.2)
                st.pyplot(fig)

            with col2:
                st.subheader("Risk Analysis")
                stats = {
                    "Metric": ["Expected Mean", "Median Outcome", "Best Case (Max)", "Worst Case (Min)", "Value at Risk (5%)"],
                    "Value": [
                        f"${np.mean(final_values):,.2f}",
                        f"${np.median(final_values):,.2f}",
                        f"${np.max(final_values):,.2f}",
                        f"${np.min(final_values):,.2f}",
                        f"${np.percentile(final_values, 5):,.2f}"
                    ]
                }
                st.table(pd.DataFrame(stats))
                
                var_5 = np.percentile(final_values, 5)
                st.warning(f"**Risk Note:** There is a 5% statistical probability that your ${investment:,.0f} investment could fall below **${var_5:,.2f}** over this period.")

            # --- Download Logic ---
            st.divider()
            st.subheader("📥 Export Results")
            
            # Prepare Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Summary Sheet
                pd.DataFrame(stats).to_excel(writer, sheet_name='Summary', index=False)
                # Raw Data Sheet (Sampling first 100 paths to keep file size reasonable)
                df_paths = pd.DataFrame(portfolio_paths[:, :100])
                df_paths.columns = [f"Simulation_{i}" for i in range(100)]
                df_paths.to_excel(writer, sheet_name='Price_Paths_Sample')
            
            st.download_button(
                label="Download Simulation Results (Excel)",
                data=output.getvalue(),
                file_name=f"{ticker}_simulation_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

else:
    st.info("Adjust the settings in the sidebar and click 'Start Simulation' to see results.")