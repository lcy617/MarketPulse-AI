# MarketPulse AI - AI 股票分析面板

## 在线访问

> **部署地址：** https://marketpulse-ai-efic.onrender.com
>
> （首次加载可能需要等待 30 秒左右，Render 免费服务有冷启动机制）

---

## 项目简介

用户输入股票代码 → 调用 Yahoo Finance 获取实时行情 → 通义千问 LLM 分析 → 返回结构化 JSON（summary / sentiment / risk_level）→ 存入 Supabase 数据库。

**技术栈：**

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus |
| 后端 | Python + FastAPI |
| LLM | 通义千问 (qwen-turbo)，OpenAI 兼容接口 |
| 数据库 | Supabase (PostgreSQL) |
| 股票数据 | Yahoo Finance (yfinance) |
| 部署 | Render.com（前后端合并部署） |

---

## Prompt 设计（如何强制 LLM 只返回 JSON）

这是本项目的核心技术点。以下是实际使用的 System Prompt（位于 `backend/app/services/llm_service.py`）：

```python
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
```

**设计思路：**

1. **角色设定**：开头明确"你是股票分析师"，让 LLM 进入专业语境
2. **输出格式硬约束**：直接给出 JSON 模板，并用"必须且只能"做强制指令
3. **枚举值约束**：sentiment 和 risk_level 用"三选一"限定取值范围，防止 LLM 自由发挥
4. **反面指令**："不要有任何多余文字、解释或 markdown 标记" 堵住 LLM 习惯性废话
5. **低温度**：`temperature=0.3`，降低随机性，让输出更稳定

**容错处理（后端兜底）：**

```python
def _parse_llm_json(content: str) -> dict:
    # 去掉可能的 markdown 代码块标记
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1])

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        # 尝试用正则从文本中提取 JSON
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            # 兜底默认值
            result = {"summary": "数据分析暂时不可用", "sentiment": "Neutral", "risk_level": "Medium"}

    # 字段校验：确保枚举值合法
    if result.get("sentiment") not in ["Bullish", "Neutral", "Bearish"]:
        result["sentiment"] = "Neutral"
    if result.get("risk_level") not in ["Low", "Medium", "High"]:
        result["risk_level"] = "Medium"

    return result
```

即使 LLM 偶尔"不听话"，这套三层容错机制也能保证接口不崩：
- 第一层：去除 markdown 代码块包裹
- 第二层：正则提取 JSON 片段
- 第三层：兜底默认值 + 枚举值校验

---

## Debug 记录：Alpha Vantage 在云服务器上被限流

**问题描述：**

项目在本地开发时一切正常——输入股票代码，Alpha Vantage API 返回完整的行情数据，LLM 分析、Supabase 存储全部跑通。但部署到 Render.com 之后，所有股票查询都返回"未找到股票数据"。

**排查过程：**

1. **第一反应：API Key 没加载？**
   在后端加了一个 `/api/debug/env` 调试接口，检查环境变量是否正确读取。访问后确认 Key 已加载（`B6W2***`），排除环境变量问题。

2. **第二反应：免费额度用完了？**
   Alpha Vantage 免费版每天 25 次请求，每次分析调 2 次 API（报价 + 日线）。换了一个新邮箱重新申请 Key，更新到 Render 环境变量——问题依旧。

3. **查看服务器日志定位根因：**
   在代码里加了 `[DEBUG]` 日志打印 Alpha Vantage 的原始返回。Render Logs 显示：
   ```
   [DEBUG] Alpha Vantage response for AAPL: ['Information']
   Full response: {"Information": "...standard API rate limit is 25 requests per day..."}
   ```
   新 Key 的第一次请求就被拒绝了。说明 Alpha Vantage 不是按 API Key 限流，而是**按 IP 地址限流**。Render 免费版使用共享 IP，该 IP 已被其他用户的请求耗尽配额。

**解决方案：**

放弃 Alpha Vantage，改用 Yahoo Finance（`yfinance` 库）：
- 不需要 API Key
- 没有请求次数限制
- 不受云服务器共享 IP 影响

```python
# 修改前（Alpha Vantage）
params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": API_KEY}
response = await client.get("https://www.alphavantage.co/query", params=params)

# 修改后（Yahoo Finance）
ticker = yf.Ticker(symbol)
info = ticker.info  # 直接获取，无需 API Key
```

**经验总结：**

免费 API 在本地跑得好好的，上了云服务器可能就不行——因为云平台的共享 IP 会被多租户共用，容易触发第三方 API 的 IP 级别限流。排查时不能只看"Key 对不对"，还要看"返回了什么"。在后端加调试日志打印原始响应，是定位这类问题最直接的方法。

---

## 本地运行

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

需要配置环境变量（创建 `.env` 文件或系统环境变量）：

```
DASHSCOPE_API_KEY=你的通义千问key
SUPABASE_URL=你的supabase项目url
SUPABASE_ANON_KEY=你的supabase匿名key
```

---

## 项目结构

```
MarketPulse_AI/
├── frontend/              # Vue 3 前端
│   ├── src/
│   │   ├── App.vue        # 主页面（搜索、结果展示、历史记录）
│   │   └── api/index.js   # 后端接口封装
│   └── vite.config.js
│
├── backend/               # FastAPI 后端
│   ├── app/
│   │   ├── main.py        # 入口 + CORS + 静态文件托管
│   │   ├── config.py      # 环境变量配置
│   │   ├── routers/
│   │   │   ├── stock.py   # GET /api/stock/{symbol}
│   │   │   └── analyze.py # POST /api/analyze + GET /api/history
│   │   └── services/
│   │       ├── stock_service.py    # Yahoo Finance 数据获取
│   │       ├── llm_service.py      # LLM 调用 + Prompt + JSON 解析
│   │       └── supabase_service.py # 数据库读写
│   └── requirements.txt
│
├── build.sh               # Render 构建脚本（前后端合并部署）
└── README.md
```
