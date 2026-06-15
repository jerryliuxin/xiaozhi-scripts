import sys
import json
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

def format_ticker(ticker):
    if ticker.isdigit() and len(ticker) == 6:
        if ticker.startswith('6'):
            return ticker + '.SS'
        else:
            return ticker + '.SZ'
    return ticker

def get_stock_info(ticker_input):
    try:
        ticker = format_ticker(ticker_input)
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # fallback to history if info is missing some realtime fields
        hist = stock.history(period="5d")
        if hist.empty:
            return {"error": f"无法获取 {ticker_input} 的行情数据。"}
            
        last_close = hist.iloc[-1]['Close']
        prev_close = hist.iloc[-2]['Close'] if len(hist) > 1 else last_close
        pct_change = (last_close - prev_close) / prev_close * 100
        vol = hist.iloc[-1]['Volume']
        
        name = info.get('shortName', ticker)
        
        report = f"【行情播报】{name} ({ticker_input})\n"
        report += f"最新价格: {last_close:.2f}\n"
        report += f"今日涨跌: {pct_change:+.2f}%\n"
        report += f"成交量: {int(vol/10000)} 万股\n"
        
        if pct_change > 9:
            report += "状态: 强势涨停/大涨，多头动能极强！\n"
        elif pct_change < -9:
            report += "状态: 跌停/大跌，注意规避风险！\n"
            
        return {"report": report}
    except Exception as e:
        return {"error": f"查询出错: {str(e)}"}

def analyze_stock(ticker_input):
    try:
        ticker = format_ticker(ticker_input)
        stock = yf.Ticker(ticker)
        df = stock.history(period="6mo")
        if df.empty:
            return {"error": f"无法获取 {ticker_input} 的数据。"}
            
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()

        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        last_day = df.iloc[-1]
        prev_day = df.iloc[-2]
        
        price = last_day['Close']
        ma5 = last_day['MA5']
        
        k_score = 1.0 if price > ma5 else 0.5
        if price > prev_day['Close']: k_score += 0.5
            
        ma_bull = (last_day['MA5'] > last_day['MA10']) and (last_day['MA10'] > last_day['MA20'])
        ma_score = 1.25 if ma_bull else 0.5
        
        macd_gold = last_day['MACD'] > last_day['Signal'] and last_day['MACD'] > 0
        macd_score = 1.0 if macd_gold else 0.4
        
        vol_score = 0.75 if last_day['Volume'] > prev_day['Volume'] * 0.8 else 0.4
        chip_score = 0.45 if price > last_day['MA60'] else 0.2
        
        total_score = k_score + ma_score + macd_score + vol_score + chip_score
        rating = "强烈推荐" if total_score >= 4.5 else "持有" if total_score >= 3.5 else "观望"
        
        stop_loss = price * 0.92
        
        name = stock.info.get('shortName', ticker_input)
        
        report = f"【姚尧深度诊断】: {name} ({ticker_input})\n"
        report += f"最新价: {price:.2f} | 5日线: {ma5:.2f}\n"
        report += f"综合评分: {total_score:.1f}/5.0 (评级: {rating})\n"
        report += f"纪律: 绝对止损 {stop_loss:.2f} (-8%)，动态止盈破 {ma5:.2f} 出局。\n"
        
        return {"report": report}
    except Exception as e:
        return {"error": f"分析出错: {str(e)}"}

if __name__ == "__main__":
    action = sys.argv[1]
    ticker = sys.argv[2]
    
    if action == "info":
        res = get_stock_info(ticker)
    elif action == "analyze":
        res = analyze_stock(ticker)
    else:
        res = {"error": "Unknown action"}
        
    print(json.dumps(res, ensure_ascii=False))
