import httpx
import asyncio
from app.config import ALPHA_VANTAGE_API_KEY, ALPHA_VANTAGE_BASE_URL


async def get_stock_quote(symbol: str) -> dict:
    """获取股票实时报价（Alpha Vantage 优先，yfinance 兜底）"""
    # 先试 Alpha Vantage
    quote = await _alpha_vantage_quote(symbol)
    if quote:
        return quote

    # Alpha Vantage 失败，用 yfinance 兜底
    print(f"[INFO] Alpha Vantage 失败，尝试 yfinance: {symbol}")
    return await _yfinance_quote(symbol)


async def get_stock_daily(symbol: str, days: int = 30) -> list:
    """获取股票近期日线数据（Alpha Vantage 优先，yfinance 兜底）"""
    daily = await _alpha_vantage_daily(symbol, days)
    if daily:
        return daily

    print(f"[INFO] Alpha Vantage 日线失败，尝试 yfinance: {symbol}")
    return await _yfinance_daily(symbol, days)


# ============ Alpha Vantage 实现 ============

async def _alpha_vantage_quote(symbol: str) -> dict:
    try:
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": ALPHA_VANTAGE_API_KEY,
        }
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            resp = await client.get(ALPHA_VANTAGE_BASE_URL, params=params)
            data = resp.json()

        if "Note" in data or "Information" in data:
            msg = data.get("Note") or data.get("Information", "")
            print(f"[WARN] Alpha Vantage 限流: {msg}")
            return None

        quote = data.get("Global Quote")
        if not quote or "05. price" not in quote:
            return None

        price = float(quote.get("05. price", 0))
        prev_close = float(quote.get("08. previous close", 0))
        change = float(quote.get("09. change", 0))
        change_pct = quote.get("10. change percent", "0%")

        return {
            "symbol": symbol,
            "price": round(price, 2),
            "change": round(change, 2),
            "change_percent": change_pct,
            "volume": int(quote.get("06. volume", 0)),
            "latest_trading_day": quote.get("07. latest trading day", ""),
            "previous_close": round(prev_close, 2),
            "open": round(float(quote.get("02. open", 0)), 2),
            "high": round(float(quote.get("03. high", 0)), 2),
            "low": round(float(quote.get("04. low", 0)), 2),
        }
    except Exception as e:
        print(f"[ERROR] Alpha Vantage quote failed: {e}")
        return None


async def _alpha_vantage_daily(symbol: str, days: int = 30) -> list:
    try:
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": ALPHA_VANTAGE_API_KEY,
            "outputsize": "compact",
        }
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            resp = await client.get(ALPHA_VANTAGE_BASE_URL, params=params)
            data = resp.json()

        if "Note" in data or "Information" in data:
            return None

        time_series = data.get("Time Series (Daily)")
        if not time_series:
            return None

        daily_data = []
        for date, values in sorted(time_series.items(), reverse=True)[:days]:
            daily_data.append({
                "date": date,
                "open": round(float(values["1. open"]), 2),
                "high": round(float(values["2. high"]), 2),
                "low": round(float(values["3. low"]), 2),
                "close": round(float(values["4. close"]), 2),
                "volume": int(values["5. volume"]),
            })
        return daily_data
    except Exception as e:
        print(f"[ERROR] Alpha Vantage daily failed: {e}")
        return None


# ============ yfinance 兜底实现 ============

async def _yfinance_quote(symbol: str) -> dict:
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")

        if hist.empty:
            return None

        # 用最近一天的数据
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) >= 2 else latest

        price = round(float(latest["Close"]), 2)
        prev_close = round(float(prev["Close"]), 2)
        change = round(price - prev_close, 2)
        change_pct = f"{(change / prev_close * 100):.2f}%" if prev_close else "0%"

        return {
            "symbol": symbol,
            "price": price,
            "change": change,
            "change_percent": change_pct,
            "volume": int(latest["Volume"]),
            "latest_trading_day": hist.index[-1].strftime("%Y-%m-%d"),
            "previous_close": prev_close,
            "open": round(float(latest["Open"]), 2),
            "high": round(float(latest["High"]), 2),
            "low": round(float(latest["Low"]), 2),
        }
    except Exception as e:
        print(f"[ERROR] yfinance quote failed: {e}")
        return None


async def _yfinance_daily(symbol: str, days: int = 30) -> list:
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1mo")

        if hist.empty:
            return []

        daily_data = []
        for date, row in hist.tail(days).iterrows():
            daily_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })

        return list(reversed(daily_data))
    except Exception as e:
        print(f"[ERROR] yfinance daily failed: {e}")
        return []
