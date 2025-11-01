import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import yfinance as yf
import pytz
import requests
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
from ta.volatility import BollingerBands

# Page configuration
st.set_page_config(
    page_title="Quotex Trading Signals Bot",
    page_icon="📈",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .signal-box {
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .buy-signal {
        background-color: #d4edda;
        border: 2px solid #28a745;
    }
    .sell-signal {
        background-color: #f8d7da;
        border: 2px solid #dc3545;
    }
    .neutral-signal {
        background-color: #fff3cd;
        border: 2px solid #ffc107;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin: 5px;
    }
</style>
""", unsafe_allow_html=True)

class TradingSignalBot:
    def __init__(self):
        self.timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        
    def fetch_data(self, symbol, period='1d', interval='1m'):
        """Fetch market data"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            return data
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            return None
    
    def calculate_indicators(self, data):
        """Calculate technical indicators"""
        # RSI
        rsi = RSIIndicator(data['Close'], window=14)
        data['RSI'] = rsi.rsi()
        
        # MACD
        macd = MACD(data['Close'])
        data['MACD'] = macd.macd()
        data['MACD_Signal'] = macd.macd_signal()
        data['MACD_Histogram'] = macd.macd_diff()
        
        # Bollinger Bands
        bb = BollingerBands(data['Close'])
        data['BB_Upper'] = bb.bollinger_hband()
        data['BB_Lower'] = bb.bollinger_lband()
        data['BB_Middle'] = bb.bollinger_mavg()
        
        # Moving Averages
        data['SMA_20'] = SMAIndicator(data['Close'], window=20).sma_indicator()
        data['SMA_50'] = SMAIndicator(data['Close'], window=50).sma_indicator()
        
        return data
    
    def generate_signal(self, data):
        """Generate trading signal based on indicators"""
        if data is None or len(data) < 50:
            return "NEUTRAL", "Insufficient data"
        
        latest = data.iloc[-1]
        
        # Initialize score
        score = 0
        reasons = []
        
        # RSI Analysis
        if latest['RSI'] < 30:
            score += 2
            reasons.append("RSI oversold")
        elif latest['RSI'] > 70:
            score -= 2
            reasons.append("RSI overbought")
        
        # MACD Analysis
        if latest['MACD'] > latest['MACD_Signal']:
            score += 2
            reasons.append("MACD bullish")
        else:
            score -= 2
            reasons.append("MACD bearish")
        
        # Bollinger Bands Analysis
        if latest['Close'] < latest['BB_Lower']:
            score += 1
            reasons.append("Price below lower BB")
        elif latest['Close'] > latest['BB_Upper']:
            score -= 1
            reasons.append("Price above upper BB")
        
        # Moving Averages Analysis
        if latest['Close'] > latest['SMA_20'] > latest['SMA_50']:
            score += 2
            reasons.append("Price above MAs")
        elif latest['Close'] < latest['SMA_20'] < latest['SMA_50']:
            score -= 2
            reasons.append("Price below MAs")
        
        # Determine signal
        if score >= 4:
            return "STRONG BUY", reasons
        elif score >= 2:
            return "BUY", reasons
        elif score <= -4:
            return "STRONG SELL", reasons
        elif score <= -2:
            return "SELL", reasons
        else:
            return "NEUTRAL", reasons
    
    def get_timezone_signals(self, symbol):
        """Generate signals for different timezones"""
        timeframes = ['1m', '5m', '15m', '1h']
        signals = {}
        
        for tf in timeframes:
            try:
                if tf == '1m':
                    data = self.fetch_data(symbol, period='1d', interval='1m')
                elif tf == '5m':
                    data = self.fetch_data(symbol, period='5d', interval='5m')
                elif tf == '15m':
                    data = self.fetch_data(symbol, period='5d', interval='15m')
                else:  # 1h
                    data = self.fetch_data(symbol, period='1mo', interval='1h')
                
                if data is not None:
                    data = self.calculate_indicators(data)
                    signal, reasons = self.generate_signal(data)
                    signals[tf] = {
                        'signal': signal,
                        'reasons': reasons,
                        'data': data
                    }
            except Exception as e:
                signals[tf] = {
                    'signal': 'ERROR',
                    'reasons': [str(e)],
                    'data': None
                }
        
        return signals

def create_chart(data, symbol):
    """Create interactive chart"""
    fig = go.Figure()
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='Price'
    ))
    
    # Bollinger Bands
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['BB_Upper'],
        line=dict(color='rgba(250, 0, 0, 0.5)'),
        name='Upper BB'
    ))
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['BB_Lower'],
        line=dict(color='rgba(250, 0, 0, 0.5)'),
        name='Lower BB'
    ))
    
    # Moving Averages
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['SMA_20'],
        line=dict(color='blue'),
        name='SMA 20'
    ))
    
    fig.update_layout(
        title=f'{symbol} Price Chart',
        yaxis_title='Price',
        xaxis_title='Time',
        template='plotly_dark'
    )
    
    return fig

def main():
    st.title("🤖 Quotex Trading Signals Bot")
    st.markdown("### AI-Powered Trading Signal Generator")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Symbol selection
        symbol = st.text_input("Trading Symbol", value="EURUSD=X", 
                              help="Use Yahoo Finance format (e.g., EURUSD=X, GBPUSD=X, BTC-USD)")
        
        # Timezone selection
        timezone = st.selectbox(
            "Select Timezone",
            options=['UTC', 'EST', 'PST', 'GMT', 'CET', 'JST'],
            index=0
        )
        
        # Auto-refresh
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=True)
        
        # Risk level
        risk_level = st.select_slider(
            "Risk Level",
            options=['Conservative', 'Moderate', 'Aggressive'],
            value='Moderate'
        )
    
    # Initialize bot
    bot = TradingSignalBot()
    
    # Main content
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.metric("Selected Symbol", symbol)
    
    with col2:
        current_time = datetime.now(pytz.UTC)
        st.metric("Current Time (UTC)", current_time.strftime('%Y-%m-%d %H:%M:%S'))
    
    with col3:
        st.metric("Selected Timezone", timezone)
    
    # Generate signals
    with st.spinner("Generating trading signals..."):
        signals = bot.get_timezone_signals(symbol)
    
    # Display signals
    st.header("📊 Trading Signals")
    
    for tf, info in signals.items():
        signal = info['signal']
        reasons = info['reasons']
        
        if 'BUY' in signal:
            signal_class = 'buy-signal'
            icon = '🟢'
        elif 'SELL' in signal:
            signal_class = 'sell-signal'
            icon = '🔴'
        else:
            signal_class = 'neutral-signal'
            icon = '🟡'
        
        with st.container():
            st.markdown(f"""
            <div class="signal-box {signal_class}">
                <h3>{icon} {tf.upper()} Timeframe - {signal}</h3>
                <p><strong>Analysis:</strong></p>
                <ul>
            """, unsafe_allow_html=True)
            
            for reason in reasons:
                st.markdown(f"<li>{reason}</li>", unsafe_allow_html=True)
            
            st.markdown("</ul></div>", unsafe_allow_html=True)
    
    # Display charts
    st.header("📈 Technical Analysis Charts")
    
    for tf, info in signals.items():
        if info['data'] is not None and len(info['data']) > 0:
            st.subheader(f"{tf.upper()} Chart")
            fig = create_chart(info['data'], symbol)
            st.plotly_chart(fig, use_container_width=True)
    
    # Trading recommendations
    st.header("💡 Trading Recommendations")
    
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="metric-card">
                <h4>🎯 Entry Points</h4>
                <ul>
                    <li>Wait for signal confirmation across multiple timeframes</li>
                    <li>Enter on pullbacks to support/resistance</li>
                    <li>Use proper risk management</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="metric-card">
                <h4>⚠️ Risk Management</h4>
                <ul>
                    <li>Never risk more than 2% per trade</li>
                    <li>Always use stop-loss orders</li>
                    <li>Take profits at logical levels</li>
                </ul>
            </div>
           
