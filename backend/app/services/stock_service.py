import httpx
from app.config import ALPHA_VANTAGE_API_KEY, ALPHA_VANTAGE_BASE_URL


async def get_stock_quote(symbol: str) -> dict:
    """获取股票实时报价（使用 Alpha Vantage）"""
    try:
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": ALPHA_VANTAGE_API_KEY,
        }
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            resp = await client.get(ALPHA_VANTAGE_BASE_URL, params=params)
            data = resp.json()

        # 检查是否触发了 API 限流
        if "Note" in data or "Information" in data:
            msg = data.get("Note") or data.get("Information", "")
            print(f"[WARN] Alpha Vantage 限流: {msg}")
            return None

        quote = data.get("Global Quote")
        if not quote or "05. price" not in quote:
            print(f"[WARN] Alpha Vantage 未返回 {symbol} 的报价数据, 响应: {data}")
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
        print(f"[ERROR] get_stock_quote failed: {e}")
        return None


async def get_stock_daily(symbol: str, days: int = 30) -> list:
    """获取股票近期日线数据（使用 Alpha Vantage）"""
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

        # 检查限流
        if "Note" in data or "Information" in data:
            msg = data.get("Note") or data.get("Information", "")
            print(f"[WARN] Alpha Vantage 限流: {msg}")
            return []

        time_series = data.get("Time Series (Daily)")
        if not time_series:
            print(f"[WARN] Alpha Vantage 未返回 {symbol} 的日线数据")
            return []

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
        print(f"[ERROR] get_stock_daily failed: {e}")
        return []
