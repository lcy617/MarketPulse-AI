import httpx
from app.config import ALPHA_VANTAGE_API_KEY, ALPHA_VANTAGE_BASE_URL


async def get_stock_quote(symbol: str) -> dict:
    """获取股票实时报价"""
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(ALPHA_VANTAGE_BASE_URL, params=params)
        data = response.json()

    # 调试日志
    print(f"[DEBUG] Alpha Vantage response for {symbol}: {list(data.keys())}")
    if "Global Quote" not in data or not data["Global Quote"]:
        print(f"[DEBUG] Full response: {data}")
        return None

    quote = data["Global Quote"]
    return {
        "symbol": quote.get("01. symbol", symbol),
        "price": float(quote.get("05. price", 0)),
        "change": float(quote.get("09. change", 0)),
        "change_percent": quote.get("10. change percent", "0%"),
        "volume": int(quote.get("06. volume", 0)),
        "latest_trading_day": quote.get("07. latest trading day", ""),
        "previous_close": float(quote.get("08. previous close", 0)),
        "open": float(quote.get("02. open", 0)),
        "high": float(quote.get("03. high", 0)),
        "low": float(quote.get("04. low", 0)),
    }


async def get_stock_daily(symbol: str, days: int = 30) -> list:
    """获取股票近期日线数据"""
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY,
        "outputsize": "compact",
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(ALPHA_VANTAGE_BASE_URL, params=params)
        data = response.json()

    time_series = data.get("Time Series (Daily)", {})
    if not time_series:
        return []

    # 取最近 N 天数据
    daily_data = []
    for date, values in list(time_series.items())[:days]:
        daily_data.append({
            "date": date,
            "open": float(values["1. open"]),
            "high": float(values["2. high"]),
            "low": float(values["3. low"]),
            "close": float(values["4. close"]),
            "volume": int(values["5. volume"]),
        })

    return daily_data
