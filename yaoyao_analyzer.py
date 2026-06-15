import sys
import json
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

def analyze_stock(ticker):
    try:
        # Handle simple symbol logic
        if ticker.isdigit() and len(ticker) == 6:
            if ticker.startswith('6'):
                ticker += '.SS'
            else:
                ticker += '.SZ'
                
        stock = yf.Ticker(ticker)
        df = stock.history(period="6mo")
        if df.empty:
            return {"error": f"无法获取 {ticker} 的数据，请检查股票代码是否正确（如 300308 或 601127）"}
            
        # 1. 均线系统
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()

        # 2. MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['Hist'] = df['MACD'] - df['Signal']
        
        last_day = df.iloc[-1]
        prev_day = df.iloc[-2]
        
        # 计算各项指标
        price = last_day['Close']
        ma5 = last_day['MA5']
        
        # K线组合得分 (简化逻辑: 站上5日线得1分，今日收涨加0.5分)
        k_score = 1.0 if price > ma5 else 0.5
        if price > prev_day['Close']:
            k_score += 0.5
            
        # 均线得分 (多头排列)
        ma_bull = (last_day['MA5'] > last_day['MA10']) and (last_day['MA10'] > last_day['MA20'])
        ma_score = 1.25 if ma_bull else 0.5
        
        # MACD得分
        macd_gold = last_day['MACD'] > last_day['Signal'] and last_day['MACD'] > 0
        macd_score = 1.0 if macd_gold else 0.4
        
        # 量价得分 (缩量上涨也是强势表现，这里简单看成交量表现)
        vol_score = 0.75 if last_day['Volume'] > prev_day['Volume'] * 0.8 else 0.4
        
        # 筹码分布得分 (假设在60日线上方代表获利盘大)
        chip_score = 0.45 if price > last_day['MA60'] else 0.2
        
        total_score = k_score + ma_score + macd_score + vol_score + chip_score
        rating = "强烈推荐" if total_score >= 4.5 else "持有" if total_score >= 3.5 else "观望"
        
        stop_loss = price * 0.92
        
        report = f"""【姚尧形态学诊断报告】: {ticker}
最新价: {price:.2f} | 5日均线: {ma5:.2f}

1. K线组合得分: {k_score}/1.5
2. 均线系统得分: {ma_score}/1.25 (多头排列: {'是' if ma_bull else '否'})
3. MACD指标得分: {macd_score}/1.0 (水上金叉: {'是' if macd_gold else '否'})
4. 量价关系得分: {vol_score}/0.75
5. 筹码分布得分: {chip_score}/0.5

🏆 综合评分: {total_score:.1f}/5.0 (评级: {rating})
纪律建议: 绝对止损位 {stop_loss:.2f} (-8%)，动态止盈看 {ma5:.2f} (破5日均线出局)。
"""
        return {"report": report}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    ticker = sys.argv[1]
    res = analyze_stock(ticker)
    print(json.dumps(res, ensure_ascii=False))
