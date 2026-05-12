import asyncio
from fastapi import APIRouter, HTTPException
from app.services.stock_service import get_stock_quote, get_stock_daily
from app.config import ALPHA_VANTAGE_API_KEY

router = APIRouter()


@router.get("/debug/env")
async def debug_env():
    """调试：检查环境变量是否加载"""
    return {
        "alpha_key_loaded": bool(ALPHA_VANTAGE_API_KEY),
        "alpha_key_preview": ALPHA_VANTAGE_API_KEY[:4] + "***" if ALPHA_VANTAGE_API_KEY else None,
    }


@router.get("/stock/{symbol}")
async def fetch_stock(symbol: str):
    """获取股票行情数据"""
    symbol = symbol.upper().strip()

    quote = await get_stock_quote(symbol)
    if not quote:
        raise HTTPException(status_code=404, detail=f"未找到股票 {symbol} 的数据")

    await asyncio.sleep(1.5)
    daily = await get_stock_daily(symbol, days=20)

    return {
        "quote": quote,
        "daily": daily,
    }
