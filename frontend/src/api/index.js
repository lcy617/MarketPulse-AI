import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
})

// 获取股票行情
export function getStock(symbol) {
  return api.get(`/api/stock/${symbol}`)
}

// AI 分析股票
export function analyzeStock(symbol) {
  return api.post('/api/analyze', { symbol })
}

// 获取历史记录
export function getHistory() {
  return api.get('/api/history')
}
