from fastapi import APIRouter, HTTPException
from app.services.stock_service import get_stock_quote, get_stock_daily

router = APIRouter()


@router.get("/stock/{symbol}")
async def fetch_stock(symbol: str):
    """获取股票行情数据"""
    symbol = symbol.upper().strip()

    quote = await get_stock_quote(symbol)
    if not quote:
        raise HTTPException(status_code=404, detail=f"未找到股票 {symbol} 的数据")

    daily = await get_stock_daily(symbol, days=20)

    return {
        "quote": quote,
        "daily": daily,
    }
