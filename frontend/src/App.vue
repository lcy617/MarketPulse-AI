<template>
  <div class="app-container">
    <header class="app-header">
      <h1>MarketPulse AI</h1>
      <p class="subtitle">AI 驱动的股票分析面板</p>
    </header>

    <main class="app-main">
      <!-- 搜索区域 -->
      <div class="search-section">
        <el-input
          v-model="symbol"
          placeholder="输入股票代码（如 AAPL、MSFT、TSLA）"
          size="large"
          class="search-input"
          @keyup.enter="handleAnalyze"
        >
          <template #prepend>股票代码</template>
        </el-input>
        <el-button
          type="primary"
          size="large"
          :loading="loading"
          @click="handleAnalyze"
        >
          {{ loading ? 'AI 分析中...' : '开始分析' }}
        </el-button>
      </div>

      <!-- 错误提示 -->
      <el-alert
        v-if="error"
        :title="error"
        type="error"
        show-icon
        closable
        class="error-alert"
        @close="error = ''"
      />

      <!-- 分析结果 -->
      <div v-if="result" class="result-section">
        <!-- 股票基本信息 -->
        <el-card class="info-card">
          <template #header>
            <div class="card-header">
              <span class="stock-symbol">{{ result.symbol }}</span>
              <span class="stock-price">${{ result.quote.price }}</span>
              <el-tag
                :type="result.quote.change >= 0 ? 'success' : 'danger'"
                size="large"
              >
                {{ result.quote.change >= 0 ? '+' : '' }}{{ result.quote.change_percent }}
              </el-tag>
            </div>
          </template>
          <div class="stock-details">
            <div class="detail-item">
              <span class="label">开盘</span>
              <span class="value">${{ result.quote.open }}</span>
            </div>
            <div class="detail-item">
              <span class="label">最高</span>
              <span class="value">${{ result.quote.high }}</span>
            </div>
            <div class="detail-item">
              <span class="label">最低</span>
              <span class="value">${{ result.quote.low }}</span>
            </div>
            <div class="detail-item">
              <span class="label">成交量</span>
              <span class="value">{{ formatVolume(result.quote.volume) }}</span>
            </div>
          </div>
        </el-card>

        <!-- AI 分析结果 -->
        <el-card class="analysis-card">
          <template #header>
            <span>AI 分析结果</span>
          </template>
          <div class="analysis-content">
            <div class="analysis-tags">
              <el-tag
                :type="sentimentType(result.analysis.sentiment)"
                size="large"
                effect="dark"
              >
                {{ sentimentLabel(result.analysis.sentiment) }}
              </el-tag>
              <el-tag
                :type="riskType(result.analysis.risk_level)"
                size="large"
              >
                风险: {{ result.analysis.risk_level }}
              </el-tag>
            </div>
            <p class="analysis-summary">{{ result.analysis.summary }}</p>
          </div>
        </el-card>
      </div>

      <!-- 历史记录 -->
      <div class="history-section">
        <el-card>
          <template #header>
            <div class="history-header">
              <span>历史分析记录</span>
              <el-button size="small" @click="loadHistory">刷新</el-button>
            </div>
          </template>
          <el-table :data="history" stripe style="width: 100%" empty-text="暂无记录">
            <el-table-column prop="symbol" label="代码" width="100" />
            <el-table-column prop="price" label="价格" width="100">
              <template #default="{ row }">
                ${{ row.price?.toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column prop="sentiment" label="情绪" width="100">
              <template #default="{ row }">
                <el-tag :type="sentimentType(row.sentiment)" size="small">
                  {{ sentimentLabel(row.sentiment) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="risk_level" label="风险" width="80" />
            <el-table-column prop="summary" label="分析摘要" />
            <el-table-column prop="created_at" label="时间" width="180">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { analyzeStock, getHistory } from './api'

const symbol = ref('')
const loading = ref(false)
const error = ref('')
const result = ref(null)
const history = ref([])

// 执行分析
async function handleAnalyze() {
  if (!symbol.value.trim()) {
    error.value = '请输入股票代码'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const res = await analyzeStock(symbol.value.trim())
    result.value = res.data
    // 分析完刷新历史
    loadHistory()
  } catch (e) {
    error.value = e.response?.data?.detail || '分析失败，请重试'
  } finally {
    loading.value = false
  }
}

// 加载历史记录
async function loadHistory() {
  try {
    const res = await getHistory()
    history.value = res.data.records || []
  } catch (e) {
    console.error('加载历史记录失败:', e)
  }
}

// 格式化成交量
function formatVolume(vol) {
  if (vol >= 1000000) return (vol / 1000000).toFixed(1) + 'M'
  if (vol >= 1000) return (vol / 1000).toFixed(1) + 'K'
  return vol
}

// 格式化时间
function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleString('zh-CN')
}

// 情绪标签颜色
function sentimentType(sentiment) {
  const map = { Bullish: 'success', Neutral: 'info', Bearish: 'danger' }
  return map[sentiment] || 'info'
}

// 情绪标签文字
function sentimentLabel(sentiment) {
  const map = { Bullish: '看涨', Neutral: '中性', Bearish: '看跌' }
  return map[sentiment] || sentiment
}

// 风险标签颜色
function riskType(level) {
  const map = { Low: 'success', Medium: 'warning', High: 'danger' }
  return map[level] || 'info'
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.app-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}

.app-header {
  text-align: center;
  margin-bottom: 30px;
}

.app-header h1 {
  font-size: 2em;
  color: #303133;
  margin-bottom: 5px;
}

.subtitle {
  color: #909399;
  font-size: 14px;
}

.search-section {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.search-input {
  flex: 1;
}

.error-alert {
  margin-bottom: 20px;
}

.result-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stock-symbol {
  font-size: 1.4em;
  font-weight: bold;
}

.stock-price {
  font-size: 1.4em;
  color: #303133;
}

.stock-details {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.detail-item {
  text-align: center;
}

.detail-item .label {
  display: block;
  color: #909399;
  font-size: 12px;
  margin-bottom: 4px;
}

.detail-item .value {
  font-size: 16px;
  font-weight: 500;
}

.analysis-tags {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}

.analysis-summary {
  color: #606266;
  line-height: 1.6;
  font-size: 15px;
}

.history-section {
  margin-top: 10px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
