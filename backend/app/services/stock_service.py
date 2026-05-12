import yfinance as yf


async def get_stock_quote(symbol: str) -> dict:
    """获取股票实时报价（使用 Yahoo Finance）"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        if not info or "regularMarketPrice" not in info:
            # 尝试从 fast_info 获取
            fast = ticker.fast_info
            if not fast:
                return None
            return {
                "symbol": symbol,
                "price": round(fast.get("lastPrice", 0), 2),
                "change": round(fast.get("lastPrice", 0) - fast.get("previousClose", 0), 2),
                "change_percent": f"{((fast.get('lastPrice', 0) - fast.get('previousClose', 0)) / fast.get('previousClose', 1) * 100):.2f}%",
                "volume": int(fast.get("lastVolume", 0)),
                "latest_trading_day": "",
                "previous_close": round(fast.get("previousClose", 0), 2),
                "open": round(fast.get("open", 0), 2),
                "high": round(fast.get("dayHigh", 0), 2),
                "low": round(fast.get("dayLow", 0), 2),
            }

        price = info.get("regularMarketPrice", 0)
        prev_close = info.get("previousClose", 0)
        change = round(price - prev_close, 2)
        change_pct = f"{(change / prev_close * 100):.2f}%" if prev_close else "0%"

        return {
            "symbol": symbol,
            "price": round(price, 2),
            "change": change,
            "change_percent": change_pct,
            "volume": int(info.get("regularMarketVolume", 0)),
            "latest_trading_day": "",
            "previous_close": round(prev_close, 2),
            "open": round(info.get("regularMarketOpen", 0), 2),
            "high": round(info.get("regularMarketDayHigh", 0), 2),
            "low": round(info.get("regularMarketDayLow", 0), 2),
        }
    except Exception as e:
        print(f"[ERROR] get_stock_quote failed: {e}")
        return None


async def get_stock_daily(symbol: str, days: int = 30) -> list:
    """获取股票近期日线数据"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1mo")

        if hist.empty:
            return []

        daily_data = []
        for date, row in hist.tail(days).iterrows():
            daily_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"]),
            })

        return list(reversed(daily_data))
    except Exception as e:
        print(f"[ERROR] get_stock_daily failed: {e}")
        return []
