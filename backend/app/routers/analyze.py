from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.stock_service import get_stock_quote, get_stock_daily
from app.services.llm_service import analyze_stock
from app.services.supabase_service import save_analysis, get_history

router = APIRouter()


class AnalyzeRequest(BaseModel):
    symbol: str


@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """AI 分析股票"""
    symbol = request.symbol.upper().strip()

    # 1. 获取股票数据
    quote = await get_stock_quote(symbol)
    if not quote:
        raise HTTPException(status_code=404, detail=f"未找到股票 {symbol} 的数据")

    daily = await get_stock_daily(symbol, days=20)

    # 2. 调用 LLM 分析
    analysis = await analyze_stock(symbol, quote, daily)

    # 3. 存入 Supabase
    try:
        save_analysis(symbol, quote, analysis)
    except Exception as e:
        # 存储失败不影响返回结果
        print(f"Supabase 存储失败: {e}")

    # 4. 返回结果
    return {
        "symbol": symbol,
        "quote": quote,
        "analysis": analysis,
    }


@router.get("/history")
async def history():
    """获取历史分析记录"""
    try:
        records = get_history()
        return {"records": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {e}")
