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


# ============ yfinance 兜底实现（直接调 Yahoo Finance API） ============

_YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


async def _yfinance_quote(symbol: str) -> dict:
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {"interval": "1d", "range": "5d"}
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            resp = await client.get(url, params=params, headers=_YAHOO_HEADERS)

            if resp.status_code != 200:
                print(f"[WARN] Yahoo Finance HTTP {resp.status_code} for {symbol}")
                return None

            data = resp.json()

        result = data.get("chart", {}).get("result")
        if not result:
            print(f"[WARN] Yahoo Finance 未返回 {symbol} 数据: {data.get('chart', {}).get('error')}")
            return None

        meta = result[0].get("meta", {})
        indicators = result[0].get("indicators", {}).get("quote", [{}])[0]
        closes = indicators.get("close", [])
        volumes = indicators.get("volume", [])
        opens = indicators.get("open", [])
        highs = indicators.get("high", [])
        lows = indicators.get("low", [])

        # 过滤掉 None 值，取最近有效数据
        valid_closes = [c for c in closes if c is not None]
        if not valid_closes:
            return None

        price = round(valid_closes[-1], 2)
        prev_close = round(meta.get("chartPreviousClose", meta.get("previousClose", 0)), 2)
        change = round(price - prev_close, 2)
        change_pct = f"{(change / prev_close * 100):.2f}%" if prev_close else "0%"

        latest_volume = next((v for v in reversed(volumes) if v is not None), 0)
        latest_open = next((o for o in reversed(opens) if o is not None), 0)
        latest_high = next((h for h in reversed(highs) if h is not None), 0)
        latest_low = next((l for l in reversed(lows) if l is not None), 0)

        return {
            "symbol": symbol,
            "price": price,
            "change": change,
            "change_percent": change_pct,
            "volume": int(latest_volume),
            "latest_trading_day": "",
            "previous_close": prev_close,
            "open": round(latest_open, 2),
            "high": round(latest_high, 2),
            "low": round(latest_low, 2),
        }
    except Exception as e:
        print(f"[ERROR] Yahoo Finance quote failed: {e}")
        return None


async def _yfinance_daily(symbol: str, days: int = 30) -> list:
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {"interval": "1d", "range": "1mo"}
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            resp = await client.get(url, params=params, headers=_YAHOO_HEADERS)

            if resp.status_code != 200:
                print(f"[WARN] Yahoo Finance daily HTTP {resp.status_code} for {symbol}")
                return []

            data = resp.json()

        result = data.get("chart", {}).get("result")
        if not result:
            return []

        timestamps = result[0].get("timestamp", [])
        indicators = result[0].get("indicators", {}).get("quote", [{}])[0]
        opens = indicators.get("open", [])
        highs = indicators.get("high", [])
        lows = indicators.get("low", [])
        closes = indicators.get("close", [])
        volumes = indicators.get("volume", [])

        daily_data = []
        for i in range(len(timestamps)):
            if closes[i] is None:
                continue
            from datetime import datetime
            date_str = datetime.utcfromtimestamp(timestamps[i]).strftime("%Y-%m-%d")
            daily_data.append({
                "date": date_str,
                "open": round(opens[i] or 0, 2),
                "high": round(highs[i] or 0, 2),
                "low": round(lows[i] or 0, 2),
                "close": round(closes[i], 2),
                "volume": int(volumes[i] or 0),
            })

        return list(reversed(daily_data[:days]))
    except Exception as e:
        print(f"[ERROR] Yahoo Finance daily failed: {e}")
        return []
