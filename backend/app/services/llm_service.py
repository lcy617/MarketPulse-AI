import json
from openai import AsyncOpenAI
from app.config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, LLM_MODEL


# 用 OpenAI 兼容接口调用通义千问
client = AsyncOpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url=DASHSCOPE_BASE_URL,
)

SYSTEM_PROMPT = """你是一个专业的股票分析师。根据用户提供的股票行情数据，给出简洁的分析。

你必须且只能返回一个 JSON 对象，格式如下，不要输出任何其他文字：
{
  "summary": "一段简洁的分析总结，100字以内",
  "sentiment": "Bullish 或 Neutral 或 Bearish（三选一）",
  "risk_level": "Low 或 Medium 或 High（三选一）"
}

规则：
1. summary：基于数据分析股票走势，给出核心判断
2. sentiment：Bullish=看涨，Neutral=中性，Bearish=看跌
3. risk_level：根据波动幅度和趋势判断风险
4. 只返回 JSON，不要有任何多余文字、解释或 markdown 标记"""


async def analyze_stock(symbol: str, quote: dict, daily: list) -> dict:
    """调用 LLM 分析股票数据，返回结构化 JSON"""

    # 组装给 LLM 的数据
    user_content = f"""请分析以下股票数据：

股票代码：{symbol}
当前价格：{quote['price']}
涨跌幅：{quote['change_percent']}
成交量：{quote['volume']}
开盘价：{quote['open']}
最高价：{quote['high']}
最低价：{quote['low']}

近期走势（最近5天收盘价）：
"""
    for day in daily[:5]:
        user_content += f"  {day['date']}: 收盘 {day['close']}, 成交量 {day['volume']}\n"

    # 调用 LLM
    response = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
    )

    content = response.choices[0].message.content.strip()

    # 解析 JSON（做容错处理）
    result = _parse_llm_json(content)
    return result


def _parse_llm_json(content: str) -> dict:
    """解析 LLM 返回的 JSON，带容错"""
    # 去掉可能的 markdown 代码块标记
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1])

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        # 尝试从文本中提取 JSON
        import re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            # 兜底：返回默认结构
            result = {
                "summary": "数据分析暂时不可用",
                "sentiment": "Neutral",
                "risk_level": "Medium",
            }

    # 校验字段完整性
    valid_sentiments = ["Bullish", "Neutral", "Bearish"]
    valid_risks = ["Low", "Medium", "High"]

    if result.get("sentiment") not in valid_sentiments:
        result["sentiment"] = "Neutral"
    if result.get("risk_level") not in valid_risks:
        result["risk_level"] = "Medium"
    if not result.get("summary"):
        result["summary"] = "暂无分析"

    return result
