from supabase import create_client
from app.config import SUPABASE_URL, SUPABASE_ANON_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def save_analysis(symbol: str, quote: dict, analysis: dict) -> dict:
    """保存分析结果到 Supabase"""
    record = {
        "symbol": symbol,
        "price": quote.get("price"),
        "change_percent": quote.get("change_percent"),
        "summary": analysis.get("summary"),
        "sentiment": analysis.get("sentiment"),
        "risk_level": analysis.get("risk_level"),
        "raw_stock_data": quote,
    }

    result = supabase.table("stock_analyses").insert(record).execute()
    return result.data[0] if result.data else record


def get_history(limit: int = 20) -> list:
    """获取历史分析记录"""
    result = (
        supabase.table("stock_analyses")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []
