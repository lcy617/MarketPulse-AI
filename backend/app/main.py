from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import stock, analyze

app = FastAPI(title="MarketPulse AI", description="AI 股票分析面板")

# 跨域配置 - 允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(stock.router, prefix="/api", tags=["股票数据"])
app.include_router(analyze.router, prefix="/api", tags=["AI分析"])


@app.get("/")
async def root():
    return {"message": "MarketPulse AI 后端服务运行中"}
