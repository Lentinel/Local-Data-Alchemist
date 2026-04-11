<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import axios from 'axios'
import {
  AlertCircle,
  BarChart3,
  CheckCircle,
  FileText,
  FolderOpen,
  Loader2,
  Sparkles,
} from 'lucide-vue-next'

const isSelectingFolder = ref(false)
const isGeneratingPlan = ref(false)
const isExecutingPlan = ref(false)
const isUndoing = ref(false)
const loadingTipIndex = ref(0)
const animatedFinancialTotal = ref(0)
const targetPath = ref(null)
const manualTargetPath = ref('C:\\Users\\Lentinel\\Desktop\\trae\\sample_messy_folder')
const files = ref([])
const analysis = ref(null)
const actionPlan = ref([])
const executionResult = ref(null)
const undoMessage = ref(null)
const error = ref(null)
const consoleRef = ref(null)
const consoleLogs = ref([])
const copyToast = ref(null)

const categoryTone = {
  logs: 'text-amber-300 bg-amber-500/10 border-amber-400/20',
  images: 'text-emerald-300 bg-emerald-500/10 border-emerald-400/20',
  documents: 'text-sky-300 bg-sky-500/10 border-sky-400/20',
  archives: 'text-fuchsia-300 bg-fuchsia-500/10 border-fuchsia-400/20',
  code: 'text-lime-300 bg-lime-500/10 border-lime-400/20',
  unknown: 'text-slate-300 bg-slate-500/10 border-slate-400/20',
}

const actionTone = {
  rename_and_move: 'text-sky-200 bg-sky-500/10 border-sky-400/30',
  move: 'text-emerald-200 bg-emerald-500/10 border-emerald-400/30',
  delete: 'text-red-200 bg-red-500/10 border-red-400/30',
  keep: 'text-slate-200 bg-slate-500/10 border-slate-400/30',
}

const actionLabel = {
  rename_and_move: '重命名并移动',
  move: '移动',
  delete: '删除',
  keep: '保留',
}

const loadingTips = [
  '正在嗅探文件结构...',
  '大模型正在进行深度特征提取...',
  '正在构建时空快照...',
  '正在提纯隐藏在噪声里的价值...',
]

let tipTimer = null
let amountAnimationFrame = null
let copyToastTimer = null

const financialTotal = computed(() => actionPlan.value.reduce((total, item) => {
  if (item.extracted_info?.type !== 'financial') {
    return total
  }

  const amount = Number(item.extracted_info.amount)
  return Number.isFinite(amount) ? total + amount : total
}, 0))

const financialRecords = computed(() => actionPlan.value
  .filter((item) => item.extracted_info?.type === 'financial')
  .map((item) => {
    const info = item.extracted_info || {}
    const amount = Number(info.amount)
    return {
      file: item.file,
      title: info.title || '',
      merchant: info.merchant || '',
      date: info.date || '',
      currency: info.currency || 'CNY',
      documentId: info.document_id || '',
      amount: Number.isFinite(amount) ? amount : null,
      summary: info.summary || '',
    }
  })
  .sort((a, b) => (b.amount || 0) - (a.amount || 0)))

const systemLogSummaries = computed(() => actionPlan.value
  .filter((item) => item.extracted_info?.type === 'system_log' && (item.extracted_info?.summary || item.extracted_info?.title))
  .map((item) => {
    const info = item.extracted_info || {}
    return {
      file: item.file,
      title: info.title || '',
      severity: info.severity || 'medium',
      errorCode: info.error_code || '',
      summary: info.summary || '',
      rootCause: info.root_cause || '',
      recommendedAction: info.recommended_action || '',
    }
  }))

const hasInsights = computed(() => financialTotal.value > 0 || systemLogSummaries.value.length > 0)

const formattedFinancialTotal = computed(() => new Intl.NumberFormat('zh-CN', {
  style: 'currency',
  currency: 'CNY',
}).format(animatedFinancialTotal.value))

const formatMoney = (amount, currency) => {
  if (!Number.isFinite(amount)) {
    return '—'
  }
  const normalizedCurrency = typeof currency === 'string' ? currency.trim().toUpperCase() : 'CNY'
  if (!/^[A-Z]{3}$/.test(normalizedCurrency)) {
    return amount.toFixed(2)
  }
  try {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: normalizedCurrency,
      maximumFractionDigits: 2,
    }).format(amount)
  } catch {
    return amount.toFixed(2)
  }
}

const severityTone = {
  low: 'text-emerald-200 bg-emerald-500/10 border-emerald-400/30',
  medium: 'text-amber-200 bg-amber-500/10 border-amber-400/30',
  high: 'text-orange-200 bg-orange-500/10 border-orange-400/30',
  critical: 'text-red-200 bg-red-500/10 border-red-400/30',
}

const severityLabel = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '致命',
}

const categoryTree = computed(() => files.value.reduce((tree, file) => {
  const category = file.category || 'unknown'
  if (!tree[category]) {
    tree[category] = []
  }
  tree[category].push(file)
  return tree
}, {}))

const addLog = (message, level = 'info') => {
  const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  consoleLogs.value.push({
    id: `${Date.now()}-${Math.random()}`,
    timestamp,
    message,
    level,
  })

  if (consoleLogs.value.length > 140) {
    consoleLogs.value.shift()
  }
}

const logClass = (level) => ({
  'text-emerald-300': level === 'info',
  'text-cyan-300': level === 'ai',
  'text-amber-300': level === 'action',
  'text-red-300': level === 'error',
  'text-slate-400': !['info', 'ai', 'action', 'error'].includes(level),
})

watch(consoleLogs, async () => {
  await nextTick()
  if (consoleRef.value) {
    consoleRef.value.scrollTop = consoleRef.value.scrollHeight
  }
}, { deep: true })

watch(isGeneratingPlan, (value) => {
  if (value) {
    loadingTipIndex.value = 0
    tipTimer = window.setInterval(() => {
      loadingTipIndex.value = (loadingTipIndex.value + 1) % loadingTips.length
    }, 2000)
    return
  }

  if (tipTimer) {
    window.clearInterval(tipTimer)
    tipTimer = null
  }
})

watch(financialTotal, (target) => {
  if (amountAnimationFrame) {
    window.cancelAnimationFrame(amountAnimationFrame)
  }

  const startValue = animatedFinancialTotal.value
  const startTime = performance.now()
  const duration = 900

  const tick = (now) => {
    const progress = Math.min((now - startTime) / duration, 1)
    const eased = 1 - (1 - progress) ** 3
    animatedFinancialTotal.value = startValue + (target - startValue) * eased

    if (progress < 1) {
      amountAnimationFrame = window.requestAnimationFrame(tick)
      return
    }

    animatedFinancialTotal.value = target
    amountAnimationFrame = null
  }

  amountAnimationFrame = window.requestAnimationFrame(tick)
}, { immediate: true })

onBeforeUnmount(() => {
  if (tipTimer) {
    window.clearInterval(tipTimer)
  }
  if (amountAnimationFrame) {
    window.cancelAnimationFrame(amountAnimationFrame)
  }
  if (copyToastTimer) {
    window.clearTimeout(copyToastTimer)
  }
})

const formatBytes = (bytes) => {
  if (!bytes) return '0 B'

  const units = ['B', 'KB', 'MB', 'GB']
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const value = bytes / 1024 ** index
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`
}

const openNativeFolderDialog = async () => {
  addLog('[系统] 请求系统原生目录选择器...', 'info')
  error.value = null
  undoMessage.value = null
  targetPath.value = null
  files.value = []
  analysis.value = null
  actionPlan.value = []
  executionResult.value = null
  isSelectingFolder.value = true

  try {
    const response = await axios.get('/api/select_folder')
    if (response.data.status === 'cancelled' || !response.data.target_path) {
      addLog('[系统] 目录选择已取消', 'info')
      return
    }

    targetPath.value = response.data.target_path
    files.value = response.data.files
    analysis.value = response.data.analysis
    addLog(`[系统] 跨维锁定本地路径: ${targetPath.value}`, 'info')
    addLog(`[系统] 本地扫描完成，发现 ${files.value.length} 个候选文件`, 'info')
    addLog(`[AI] 准备提交 ${files.value.length} 个文件摘要给大模型`, 'ai')
    await generateAlchemyPlan()
  } catch (err) {
    error.value = err.response?.data?.detail || '本地目录选择失败，请稍后再试'
    addLog(`[错误] 本地目录锁定失败: ${error.value}`, 'error')
    console.error('Select folder error:', err)
  } finally {
    isSelectingFolder.value = false
  }
}

const lockManualTarget = async () => {
  const path = manualTargetPath.value.trim()
  if (!path) {
    error.value = '请输入本地目标目录路径'
    addLog('[错误] 手动路径为空', 'error')
    return
  }

  error.value = null
  undoMessage.value = null
  targetPath.value = null
  files.value = []
  analysis.value = null
  actionPlan.value = []
  executionResult.value = null
  isSelectingFolder.value = true

  try {
    addLog(`[系统] 正在校验本地路径: ${path}`, 'info')
    const response = await axios.post('/api/lock_folder', {
      target_path: path,
    })
    targetPath.value = response.data.target_path
    files.value = response.data.files
    analysis.value = response.data.analysis
    addLog(`[系统] 跨维锁定本地路径: ${targetPath.value}`, 'info')
    addLog(`[系统] 本地扫描完成，发现 ${files.value.length} 个候选文件`, 'info')
    addLog('[AI] 准备对手动路径进行本地嗅探与计划生成', 'ai')
    await generateAlchemyPlan()
  } catch (err) {
    error.value = err.response?.data?.detail || '本地路径校验失败，请检查目录是否存在'
    addLog(`[错误] 本地路径校验失败: ${error.value}`, 'error')
    console.error('Lock folder error:', err)
  } finally {
    isSelectingFolder.value = false
  }
}

const generateAlchemyPlan = async () => {
  if (!targetPath.value) {
    return
  }

  error.value = null
  executionResult.value = null
  undoMessage.value = null
  isGeneratingPlan.value = true
  addLog('[AI] 正在嗅探文件内容并生成炼金计划...', 'ai')

  try {
    const response = await axios.post('/api/generate_plan', {
      target_path: targetPath.value,
    })
    files.value = response.data.file_inventory || files.value
    analysis.value = response.data.analysis || analysis.value
    actionPlan.value = response.data.plan
    response.data.reasoning_trace?.forEach((trace) => addLog(`[AI] ${trace}`, 'ai'))
    if (response.data.llm_error) {
      addLog(`[错误] LLM 不可用，已启用本地兜底计划: ${response.data.llm_error}`, 'error')
    }
    addLog(`[AI] 计划生成完成，共 ${actionPlan.value.length} 条 Action`, 'ai')
    actionPlan.value.forEach((item) => {
      if (item.extracted_info?.type === 'financial') {
        addLog(`[AI] 发现高价值财务特征: ${item.file} amount=${item.extracted_info.amount}`, 'ai')
      }
      if (item.extracted_info?.type === 'system_log') {
        addLog(`[AI] 提取系统日志摘要: ${item.file}`, 'ai')
      }
    })
  } catch (err) {
    error.value = err.response?.data?.detail || 'AI 炼金计划生成失败，请稍后再试'
    addLog(`[错误] LLM 计划生成失败: ${error.value}`, 'error')
    console.error('Generate plan error:', err)
  } finally {
    isGeneratingPlan.value = false
  }
}

const approveAndExecute = async () => {
  if (!targetPath.value || actionPlan.value.length === 0) {
    return
  }

  error.value = null
  executionResult.value = null
  undoMessage.value = null
  isExecutingPlan.value = true
  addLog('[执行] 审批通过，开始执行文件炼金计划', 'action')

  try {
    const response = await axios.post('/api/execute_plan', {
      target_path: targetPath.value,
      plan: actionPlan.value,
    })
    executionResult.value = response.data
    response.data.results?.forEach((result) => {
      if (result.action === 'keep') {
        addLog(`[执行] 保留文件: ${result.original_path}`, 'action')
        return
      }
      addLog(`[执行] 执行 ${result.action}: ${result.original_path} -> ${result.new_path || result.target_path || 'null'}`, 'action')
    })
    addLog(`[系统] 快照已写入: ${response.data.snapshot_path || response.data.snapshot}`, 'info')
  } catch (err) {
    error.value = err.response?.data?.detail || '执行炼金计划失败，请检查计划内容'
    addLog(`[错误] 执行炼金计划失败: ${error.value}`, 'error')
    console.error('Execute plan error:', err)
  } finally {
    isExecutingPlan.value = false
  }
}

const undoPlan = async () => {
  if (!targetPath.value) {
    return
  }

  error.value = null
  undoMessage.value = null
  isUndoing.value = true
  addLog('[执行] 启动时光倒流协议，读取 snapshot.json', 'action')

  try {
    const response = await axios.post('/api/undo_plan', {
      target_path: targetPath.value,
    })
    response.data.results?.forEach((result) => {
      addLog(`[执行] 回滚: ${result.restored_from} -> ${result.original_path || result.file}`, 'action')
    })
    targetPath.value = null
    files.value = []
    analysis.value = null
    actionPlan.value = []
    executionResult.value = null
    undoMessage.value = response.data.message || '已恢复到炼金前状态'
    addLog(`[系统] ${undoMessage.value}`, 'info')
  } catch (err) {
    error.value = err.response?.data?.detail || '时光倒流失败，请检查 snapshot 状态'
    addLog(`[错误] 时光倒流失败: ${error.value}`, 'error')
    console.error('Undo plan error:', err)
  } finally {
    isUndoing.value = false
  }
}

const copyText = async (text) => {
  if (!text) {
    return
  }

  const setToast = (message) => {
    copyToast.value = message
    if (copyToastTimer) {
      window.clearTimeout(copyToastTimer)
    }
    copyToastTimer = window.setTimeout(() => {
      copyToast.value = null
      copyToastTimer = null
    }, 1600)
  }

  try {
    await navigator.clipboard.writeText(text)
    setToast('已复制路径')
    return
  } catch {
    try {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.left = '-9999px'
      textarea.style.top = '0'
      document.body.appendChild(textarea)
      textarea.focus()
      textarea.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(textarea)
      setToast(ok ? '已复制路径' : '复制失败')
    } catch {
      setToast('复制失败')
    }
  }
}

const buildReport = () => {
  const generatedAt = new Date().toLocaleString('zh-CN', { hour12: false })
  const lines = [
    '# 本地炼金炉 · 结案报告',
    '',
    `生成时间：${generatedAt}`,
    `目标目录：${targetPath.value || 'N/A'}`,
    '',
    '## 文件清单',
  ]

  Object.entries(categoryTree.value).forEach(([category, categoryFiles]) => {
    lines.push(`- ${category}`)
    categoryFiles.forEach((file) => {
      lines.push(`  - ${file.path} (${file.extension || 'unknown'}, ${formatBytes(file.size)})`)
    })
  })

  lines.push('', '## AI 炼金计划')
  actionPlan.value.forEach((item, index) => {
    lines.push(`${index + 1}. ${item.file}`)
    lines.push(`   操作: ${item.action}`)
    lines.push(`   目标: ${item.target_path || 'null'}`)
    lines.push(`   理由: ${item.reason}`)
    if (item.extracted_info) {
      lines.push(`   提取信息: ${JSON.stringify(item.extracted_info, null, 0)}`)
    }
  })

  lines.push('', '## 提纯看板')
  lines.push(`金额汇总: ${formattedFinancialTotal.value}`)
  if (systemLogSummaries.value.length > 0) {
    systemLogSummaries.value.forEach((item) => {
      lines.push(`- ${item.file}: ${item.title || item.summary}`)
    })
  } else {
    lines.push('- 暂无系统日志洞察')
  }

  lines.push('', '## 执行结果')
  if (executionResult.value?.results?.length) {
    executionResult.value.results.forEach((result) => {
      lines.push(`- ${result.action}: ${result.original_path || result.file} -> ${result.new_path || result.target_path || 'null'} [${result.status}]`)
    })
  } else {
    lines.push('- 尚未执行')
  }

  lines.push('', '## 控制台日志')
  consoleLogs.value.forEach((log) => {
    lines.push(`[${log.timestamp}] ${log.message}`)
  })

  return lines.join('\n')
}

const exportReport = () => {
  const report = buildReport()
  const dateToken = new Date().toISOString().slice(0, 10)
  const blob = new Blob([report], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `炼金报告_${dateToken}.txt`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  addLog(`[系统] 导出结案报告: ${link.download}`, 'info')
}
</script>

<template>
  <div class="min-h-screen p-6 md:p-8 flex flex-col items-center justify-start gap-10 max-w-6xl mx-auto">
    <header class="text-center space-y-4 animate-in fade-in slide-in-from-top-4 duration-1000">
      <p class="text-sm font-semibold text-emerald-300 uppercase">本地炼金炉</p>
      <h1 class="text-4xl md:text-5xl font-black alchemist-gradient bg-clip-text text-transparent">
        本地炼金炉
      </h1>
      <p class="text-slate-400 text-lg font-medium">
        将杂乱的本地目录转化为可执行的结构化炼金计划
      </p>
    </header>

    <main class="w-full space-y-10">
      <section v-if="!isGeneratingPlan" class="relative min-h-80 rounded-lg overflow-hidden glass-strong border border-emerald-300/20 flex flex-col items-center justify-center gap-6 p-8 text-center">
        <div class="absolute inset-0 scan-field opacity-40"></div>
        <div class="relative p-5 rounded-lg bg-emerald-300/10 text-emerald-200 border border-emerald-300/20">
          <FolderOpen v-if="!isSelectingFolder" :size="56" />
          <Loader2 v-else :size="56" class="animate-spin" />
        </div>

        <div class="relative space-y-3">
          <h2 class="text-3xl font-black text-slate-50">
            {{ isSelectingFolder ? '正在锁定本地目标...' : '选择本地目标目录' }}
          </h2>
          <p class="text-slate-400">锁定一个本地目录，炼金炉将在其中直接嗅探、规划、执行和回滚。</p>
        </div>

        <button
          type="button"
          class="relative approve-button rounded-lg px-8 py-4 font-black text-lg text-slate-950 active:scale-[0.99] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="isSelectingFolder || isGeneratingPlan || isExecutingPlan"
          @click="lockManualTarget"
        >
          {{ isSelectingFolder ? '正在锁定...' : '锁定目标目录并开始炼金' }}
        </button>

        <div class="relative w-full max-w-4xl rounded-lg border border-white/10 bg-slate-950/70 p-4 text-left space-y-3">
          <p class="text-xs text-slate-400 font-mono uppercase">本地路径锁定</p>
          <div class="flex flex-col md:flex-row gap-3">
            <input
              v-model="manualTargetPath"
              type="text"
              class="flex-1 rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-emerald-100 outline-none focus:border-emerald-300 font-mono"
              placeholder="C:\Users\...\Messy_Folder"
            >
            <button
              type="button"
              class="rounded-lg border border-emerald-300/30 px-4 py-2 text-emerald-100 bg-emerald-500/10 hover:bg-emerald-500/20 transition-colors disabled:opacity-50"
              :disabled="isSelectingFolder || isGeneratingPlan || isExecutingPlan"
              @click="lockManualTarget"
            >
              使用此路径
            </button>
          </div>
          <p class="text-xs text-slate-500">
            浏览器无法安全读取真实绝对路径，这里直接交给本地后端校验和扫描。默认路径是安全测试目录。
          </p>
          <button
            type="button"
            class="rounded-lg border border-slate-400/20 px-3 py-1.5 text-xs text-slate-300 bg-white/5 hover:bg-white/10 transition-colors disabled:opacity-50"
            :disabled="isSelectingFolder || isGeneratingPlan || isExecutingPlan"
            @click="openNativeFolderDialog"
          >
            打开系统选择窗口
          </button>
        </div>

        <div v-if="targetPath" class="relative w-full max-w-4xl rounded-lg border border-emerald-300/20 bg-slate-950/70 p-4 text-left">
          <p class="text-xs text-emerald-300 font-mono uppercase">目标目录</p>
          <p class="mt-2 text-emerald-100 font-mono break-all">{{ targetPath }}</p>
        </div>
      </section>

      <section v-else class="relative min-h-96 rounded-lg overflow-hidden glass-strong border border-cyan-300/20 flex flex-col items-center justify-center p-8">
        <div class="absolute inset-0 scan-field opacity-70"></div>
        <div class="absolute inset-x-0 top-0 h-px bg-cyan-200/70 scan-line"></div>

        <div class="relative w-40 h-40 flex items-center justify-center">
          <div class="absolute inset-0 rounded-full loading-ring"></div>
          <div class="absolute inset-5 rounded-full loading-ring-reverse"></div>
          <div class="absolute inset-12 rounded-full bg-cyan-300/10 blur-xl"></div>
          <Sparkles class="relative text-cyan-200" :size="42" />
        </div>

        <div class="relative mt-8 text-center space-y-3">
          <p class="text-sm text-cyan-200 font-mono uppercase">大模型深度提取</p>
          <h2 class="text-3xl font-black text-slate-50">炼金大脑正在运行</h2>
          <Transition name="tip-fade" mode="out-in">
            <p :key="loadingTipIndex" class="text-slate-300 text-lg min-h-7">
              {{ loadingTips[loadingTipIndex] }}
            </p>
          </Transition>
        </div>

        <div class="relative mt-8 w-full max-w-2xl rounded-lg bg-slate-950/70 border border-white/10 p-4 font-mono text-sm text-cyan-100/80 overflow-hidden">
          <div class="code-stream">
            <p>&gt; 扫描 --递归 "{{ targetPath || '等待目标目录' }}"</p>
            <p>&gt; 摘要提取 --语义模式 --最大字节 512</p>
            <p>&gt; 生成计划 --仅 JSON --需要审批</p>
            <p>&gt; 快照 --准备时光倒流</p>
          </div>
        </div>
      </section>

      <div v-if="error" class="flex items-center gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 animate-in fade-in slide-in-from-bottom-2">
        <AlertCircle :size="20" />
        <p class="font-medium">{{ error }}</p>
      </div>

      <div v-if="undoMessage" class="flex items-center gap-3 p-4 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-200 animate-in fade-in slide-in-from-bottom-2">
        <CheckCircle :size="20" />
        <p class="font-medium">{{ undoMessage }}</p>
      </div>

      <section v-if="analysis" class="space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
          <div>
            <p class="text-sm text-emerald-300 font-semibold uppercase">Phase 2 Preview</p>
            <h2 class="text-2xl font-bold flex items-center gap-3">
              <Sparkles class="text-emerald-400" />
              本地分析摘要
            </h2>
          </div>
          <p class="text-sm text-slate-500 font-mono">{{ analysis.mode }}</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="p-5 rounded-lg glass">
            <p class="text-sm text-slate-400">文件总数</p>
            <p class="text-4xl font-black text-slate-100 mt-2">{{ analysis.total_files }}</p>
          </div>

          <div class="md:col-span-2 p-5 rounded-lg glass space-y-3">
            <p class="text-sm text-slate-400 flex items-center gap-2">
              <BarChart3 :size="16" />
              类型分布
            </p>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="category in analysis.categories"
                :key="category.key"
                :class="[
                  'px-3 py-1 rounded-lg border text-sm font-semibold',
                  categoryTone[category.key] || categoryTone.unknown
                ]"
              >
                {{ category.label }} · {{ category.count }}
              </span>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div class="p-5 rounded-lg glass space-y-3">
            <h3 class="font-bold text-slate-100">炼金建议</h3>
            <ul class="space-y-2 text-slate-300">
              <li
                v-for="recommendation in analysis.recommendations"
                :key="recommendation"
                class="flex gap-2"
              >
                <CheckCircle class="mt-0.5 text-emerald-400 shrink-0" :size="16" />
                <span>{{ recommendation }}</span>
              </li>
            </ul>
          </div>

          <div class="p-5 rounded-lg glass space-y-3">
            <h3 class="font-bold text-slate-100">扩展名统计</h3>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="extension in analysis.extensions"
                :key="extension.extension"
                class="px-3 py-1 rounded-lg bg-slate-800 text-slate-300 text-sm font-mono"
              >
                {{ extension.extension }} × {{ extension.count }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <section v-if="actionPlan.length > 0" class="space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
          <div>
            <p class="text-sm text-amber-300 font-semibold uppercase">Alchemist Insights</p>
            <h2 class="text-2xl font-bold flex items-center gap-3">
              <Sparkles class="text-amber-300" />
              提纯看板
            </h2>
          </div>
          <button
            type="button"
            class="px-4 py-2 rounded-lg border border-amber-300/30 text-amber-100 bg-amber-500/10 hover:bg-amber-500/20 transition-colors"
            @click="exportReport"
          >
            导出结案报告
          </button>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div class="p-5 rounded-lg glass border border-amber-300/20">
            <p class="text-sm text-amber-200">本次炼金提取总金额</p>
            <p class="text-4xl font-black text-amber-100 mt-3 value-glow">{{ formattedFinancialTotal }}</p>
            <p class="mt-3 text-xs text-slate-400 leading-relaxed">
              说明：来自本次 AI 计划中 financial 条目的 amount 求和，基于文件片段推断，不代表账户余额或真实结算金额。
            </p>
          </div>

          <div class="lg:col-span-2 p-5 rounded-lg glass space-y-4">
            <div class="flex items-center justify-between gap-3">
              <h3 class="font-bold text-slate-100">财务条目</h3>
              <p class="text-xs text-slate-500 font-mono">财务条目={{ financialRecords.length }}</p>
            </div>
            <div v-if="financialRecords.length > 0" class="rounded-lg border border-white/10 overflow-hidden">
              <div class="grid grid-cols-12 gap-3 px-4 py-3 text-xs uppercase text-slate-500 bg-slate-950/60">
                <span class="col-span-12 md:col-span-5">文件</span>
                <span class="col-span-6 md:col-span-2">日期</span>
                <span class="col-span-6 md:col-span-2">商户</span>
                <span class="col-span-12 md:col-span-3 text-right">金额</span>
              </div>
              <div
                v-for="record in financialRecords"
                :key="`${record.file}-${record.documentId}-${record.amount}`"
                class="grid grid-cols-12 gap-3 px-4 py-3 border-t border-white/10 bg-slate-950/30"
              >
                <div class="col-span-12 md:col-span-5 min-w-0">
                  <p class="text-slate-100 font-medium truncate">{{ record.file }}</p>
                  <p v-if="record.title || record.documentId" class="text-xs text-slate-500 mt-1 truncate">
                    <span v-if="record.title">{{ record.title }}</span>
                    <span v-if="record.title && record.documentId"> · </span>
                    <span v-if="record.documentId">ID {{ record.documentId }}</span>
                  </p>
                </div>
                <div class="col-span-6 md:col-span-2 text-sm text-slate-300 font-mono truncate">
                  {{ record.date || '—' }}
                </div>
                <div class="col-span-6 md:col-span-2 text-sm text-slate-300 truncate">
                  {{ record.merchant || '—' }}
                </div>
                <div class="col-span-12 md:col-span-3 text-right text-sm text-amber-100 font-black">
                  {{ formatMoney(record.amount, record.currency) }}
                </div>
              </div>
            </div>
            <p v-else class="text-slate-500">暂未提取到财务结构化条目</p>
          </div>
        </div>

        <div class="p-5 rounded-lg glass space-y-3">
          <div class="flex items-center justify-between gap-3">
            <h3 class="font-bold text-slate-100">系统日志洞察</h3>
            <p class="text-xs text-slate-500 font-mono">日志条目={{ systemLogSummaries.length }}</p>
          </div>
          <div v-if="systemLogSummaries.length > 0" class="space-y-3">
            <div
              v-for="item in systemLogSummaries"
              :key="`${item.file}-${item.title || item.summary}`"
              class="p-4 rounded-lg bg-slate-950/70 border border-white/10 space-y-2"
            >
              <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                <p class="text-sm text-sky-200 font-mono truncate">{{ item.file }}</p>
                <span
                  :class="[
                    'inline-flex px-2 py-0.5 rounded-lg border text-xs font-mono uppercase w-fit',
                    severityTone[item.severity] || severityTone.medium,
                  ]"
                >
                  {{ severityLabel[item.severity] || item.severity }}
                </span>
              </div>
              <p v-if="item.title" class="text-slate-100 font-semibold">{{ item.title }}</p>
              <p v-if="item.summary" class="text-slate-300">{{ item.summary }}</p>
              <p v-if="item.errorCode" class="text-xs text-slate-500 font-mono">错误码: {{ item.errorCode }}</p>
              <div v-if="item.recommendedAction" class="mt-2 p-3 rounded-lg border border-emerald-400/20 bg-emerald-500/10 text-emerald-100">
                <p class="text-xs text-emerald-200 font-mono uppercase">建议动作</p>
                <p class="mt-1 text-sm">{{ item.recommendedAction }}</p>
              </div>
            </div>
          </div>
          <p v-else class="text-slate-500">暂未提取到系统日志摘要</p>
        </div>

        <p v-if="!hasInsights" class="text-sm text-slate-500">
          这批文件暂未提取到金额或日志摘要，计划仍可继续审批执行。
        </p>
      </section>

      <section v-if="analysis" class="space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
          <div>
            <p class="text-sm text-sky-300 font-semibold uppercase">AI Approval Flow</p>
            <h2 class="text-2xl font-bold flex items-center gap-3">
              <Sparkles class="text-sky-300" />
              AI 炼金计划审批面板
            </h2>
          </div>
          <button
            type="button"
            class="px-4 py-2 rounded-lg border border-sky-400/30 text-sky-100 bg-sky-500/10 hover:bg-sky-500/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="isGeneratingPlan || isExecutingPlan || !targetPath"
            @click="generateAlchemyPlan"
          >
            {{ isGeneratingPlan ? '正在召唤计划...' : '重新生成 AI 计划' }}
          </button>
        </div>

        <div class="rounded-lg glass overflow-hidden border border-white/10">
          <div class="grid grid-cols-12 gap-3 px-4 py-3 text-xs uppercase text-slate-500 bg-slate-950/60">
            <span class="col-span-12 md:col-span-3">原文件</span>
            <span class="col-span-12 md:col-span-2">操作</span>
            <span class="col-span-12 md:col-span-3">目标路径</span>
            <span class="col-span-12 md:col-span-4">AI 理由</span>
          </div>

          <div v-if="isGeneratingPlan" class="flex items-center justify-center gap-3 p-8 text-slate-300">
            <Loader2 :size="22" class="animate-spin text-sky-300" />
            <span>正在生成可审批 Action Plan</span>
          </div>

          <div v-else-if="actionPlan.length === 0" class="p-8 text-center text-slate-400">
            上传文件后，AI 炼金计划会出现在这里
          </div>

          <TransitionGroup
            v-else
            name="plan-row"
            tag="div"
          >
            <div
              v-for="(item, index) in actionPlan"
              :key="`${item.file}-${index}`"
              class="grid grid-cols-12 gap-3 px-4 py-4 border-t border-white/10 items-center hover:bg-white/5 transition-colors plan-row-item"
              :style="{ transitionDelay: `${index * 75}ms` }"
            >
              <div class="col-span-12 md:col-span-3 min-w-0">
                <p class="text-slate-100 font-medium truncate">{{ item.file }}</p>
                <p class="text-xs text-slate-500 font-mono">#{{ index + 1 }}</p>
              </div>

              <div class="col-span-12 md:col-span-2">
                <select
                  v-model="item.action"
                  class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-400"
                >
                  <option value="rename_and_move">重命名并移动</option>
                  <option value="move">移动</option>
                  <option value="delete">删除</option>
                  <option value="keep">保留</option>
                </select>
                <span :class="[
                  'inline-flex mt-2 px-2 py-0.5 rounded-lg border text-xs',
                  actionTone[item.action] || actionTone.keep
                ]">
                  {{ actionLabel[item.action] || item.action }}
                </span>
              </div>

              <div class="col-span-12 md:col-span-3">
                <input
                  v-model="item.target_path"
                  type="text"
                  :placeholder="item.action === 'delete' || item.action === 'keep' ? '无需目标路径' : 'logs/example.log'"
                  class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-400 disabled:opacity-50"
                  :disabled="item.action === 'delete' || item.action === 'keep'"
                >
              </div>

              <div class="col-span-12 md:col-span-4">
                <textarea
                  v-model="item.reason"
                  rows="2"
                  class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-400 resize-none"
                ></textarea>
              </div>
            </div>
          </TransitionGroup>
        </div>

        <div class="space-y-4">
          <button
            type="button"
            class="approve-button w-full rounded-lg px-6 py-5 font-black text-lg text-slate-950 active:scale-[0.99] transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
            :disabled="isGeneratingPlan || isExecutingPlan || actionPlan.length === 0"
            @click="approveAndExecute"
          >
            <span v-if="isExecutingPlan" class="inline-flex items-center gap-3">
              <Loader2 :size="22" class="animate-spin" />
              正在执行炼金...
            </span>
            <span v-else>批准并执行炼金</span>
          </button>

          <div v-if="executionResult" class="p-4 rounded-lg border border-emerald-400/20 bg-emerald-500/10 text-emerald-100">
            <p class="font-bold">炼金执行完成：{{ executionResult.executed }} 条操作已处理</p>
            <p class="text-sm text-emerald-200/80 mt-1">
              文件已在目标目录中完成移动、重命名、删除或保留。
            </p>
            <div v-if="targetPath" class="mt-3 rounded-lg border border-emerald-400/20 bg-slate-950/40 p-3">
              <p class="text-xs text-emerald-200 font-mono uppercase">organized_at</p>
              <div class="mt-2 flex flex-col md:flex-row md:items-center gap-3">
                <p class="flex-1 text-emerald-100 font-mono break-all">{{ targetPath }}</p>
                <button
                  type="button"
                  class="rounded-lg border border-emerald-300/30 px-3 py-2 text-emerald-100 bg-emerald-500/10 hover:bg-emerald-500/20 transition-colors"
                  @click="copyText(targetPath)"
                >
                  复制路径
                </button>
              </div>
              <p v-if="copyToast" class="mt-2 text-xs text-emerald-200/80">{{ copyToast }}</p>
            </div>
          </div>

          <button
            v-if="executionResult"
            type="button"
            class="w-full rounded-lg px-6 py-4 font-black text-lg text-cyan-950 bg-cyan-200 hover:bg-cyan-100 active:scale-[0.99] transition-all undo-pulse disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="isUndoing"
            @click="undoPlan"
          >
            <span v-if="isUndoing" class="inline-flex items-center gap-3">
              <Loader2 :size="22" class="animate-spin" />
              正在时光倒流...
            </span>
            <span v-else>时光倒流</span>
          </button>
        </div>
      </section>

      <section v-if="files.length > 0" class="space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <div class="flex items-center justify-between">
          <h2 class="text-2xl font-bold flex items-center gap-3">
            <CheckCircle class="text-emerald-500" />
            发现待炼化物质 ({{ files.length }})
          </h2>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            v-for="(file, index) in files"
            :key="`${file.path}-${index}`"
            class="flex items-center gap-4 p-4 rounded-lg glass hover:bg-white/10 transition-colors group"
          >
            <div class="p-3 rounded-lg bg-slate-800 text-slate-400 group-hover:bg-slate-700 group-hover:text-slate-200 transition-colors">
              <FileText :size="24" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <p class="font-medium text-slate-200 truncate">{{ file.name }}</p>
                <span :class="[
                  'px-2 py-0.5 rounded-lg border text-xs shrink-0',
                  categoryTone[file.category] || categoryTone.unknown
                ]">
                  {{ file.category }}
                </span>
              </div>
              <p class="text-xs text-slate-500 font-mono truncate">{{ file.path }}</p>
              <p class="text-xs text-slate-500 font-mono uppercase">{{ file.extension || 'UNKNOWN' }} · {{ formatBytes(file.size) }}</p>
            </div>
          </div>
        </div>
      </section>

      <section class="space-y-4 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-emerald-300 font-semibold uppercase">控制台</p>
            <h2 class="text-2xl font-bold text-slate-100">炼金控制台</h2>
          </div>
          <p class="text-xs text-slate-500 font-mono">{{ consoleLogs.length }} lines</p>
        </div>

        <div ref="consoleRef" class="console-panel h-64 rounded-lg border border-emerald-400/20 bg-slate-950/90 p-4 overflow-y-auto font-mono text-sm">
          <p v-if="consoleLogs.length === 0" class="text-emerald-500/60">
            [启动] 控制台已就绪，等待日志流...
          </p>
          <div
            v-for="log in consoleLogs"
            :key="log.id"
            class="console-line"
            :class="logClass(log.level)"
          >
            <span class="text-emerald-600">[{{ log.timestamp }}]</span>
            <span>{{ log.message }}</span>
          </div>
        </div>
      </section>
    </main>

    <footer class="mt-auto py-8 text-slate-600 text-sm"></footer>
  </div>
</template>

<style scoped>
.animate-in {
  animation-fill-mode: forwards;
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slide-in-from-top-4 {
  from { transform: translateY(-1rem); }
  to { transform: translateY(0); }
}

@keyframes slide-in-from-bottom-2 {
  from { transform: translateY(0.5rem); }
  to { transform: translateY(0); }
}

@keyframes slide-in-from-bottom-8 {
  from { transform: translateY(2rem); }
  to { transform: translateY(0); }
}

@keyframes undo-pulse {
  0%, 100% { box-shadow: 0 0 25px rgba(103, 232, 249, 0.2); }
  50% { box-shadow: 0 0 48px rgba(103, 232, 249, 0.45); }
}

@keyframes loading-spin {
  to { transform: rotate(360deg); }
}

@keyframes loading-spin-reverse {
  to { transform: rotate(-360deg); }
}

@keyframes scan-line {
  0% { transform: translateY(0); opacity: 0; }
  12% { opacity: 1; }
  100% { transform: translateY(24rem); opacity: 0; }
}

@keyframes code-stream {
  0%, 100% { transform: translateY(0); opacity: 0.75; }
  50% { transform: translateY(-0.75rem); opacity: 1; }
}

@keyframes approve-breathe {
  0%, 100% { box-shadow: 0 0 22px rgba(52, 211, 153, 0.25); filter: saturate(1); }
  50% { box-shadow: 0 0 52px rgba(14, 165, 233, 0.45); filter: saturate(1.35); }
}

@keyframes console-scan {
  0% { transform: translateY(-100%); opacity: 0; }
  20% { opacity: 0.55; }
  100% { transform: translateY(100%); opacity: 0; }
}

.glass-strong {
  background: rgba(15, 23, 42, 0.56);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.scan-field {
  background:
    radial-gradient(circle at 50% 42%, rgba(34, 211, 238, 0.22), transparent 28%),
    linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  background-size: auto, 28px 28px, 28px 28px;
}

.scan-line {
  animation: scan-line 2.4s linear infinite;
}

.loading-ring,
.loading-ring-reverse {
  border: 1px solid rgba(103, 232, 249, 0.22);
  box-shadow: inset 0 0 22px rgba(34, 211, 238, 0.18), 0 0 28px rgba(34, 211, 238, 0.22);
}

.loading-ring::before,
.loading-ring-reverse::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: inherit;
  border-top: 2px solid rgba(103, 232, 249, 0.95);
  border-right: 2px solid transparent;
}

.loading-ring {
  animation: loading-spin 4.5s linear infinite;
}

.loading-ring-reverse {
  animation: loading-spin-reverse 3.2s linear infinite;
}

.code-stream {
  animation: code-stream 2.8s ease-in-out infinite;
}

.tip-fade-enter-active,
.tip-fade-leave-active {
  transition: opacity 0.35s ease, transform 0.35s ease;
}

.tip-fade-enter-from,
.tip-fade-leave-to {
  opacity: 0;
  transform: translateY(0.4rem);
}

.plan-row-enter-active,
.plan-row-leave-active {
  transition: opacity 0.5s ease, transform 0.5s ease;
}

.plan-row-enter-from,
.plan-row-leave-to {
  opacity: 0;
  transform: translateY(1rem);
}

.plan-row-move {
  transition: transform 0.45s ease;
}

.value-glow {
  text-shadow: 0 0 24px rgba(251, 191, 36, 0.45);
}

.approve-button {
  background: linear-gradient(135deg, #6ee7b7 0%, #67e8f9 48%, #fcd34d 100%);
  animation: approve-breathe 2.5s ease-in-out infinite;
}

.console-panel {
  position: relative;
  box-shadow: inset 0 0 28px rgba(16, 185, 129, 0.1), 0 18px 60px rgba(0, 0, 0, 0.32);
}

.console-panel::before {
  content: '';
  position: sticky;
  display: block;
  top: -1rem;
  height: 4rem;
  margin: -1rem -1rem 0;
  pointer-events: none;
  background: linear-gradient(to bottom, transparent, rgba(52, 211, 153, 0.12), transparent);
  animation: console-scan 3.2s linear infinite;
}

.console-panel::after {
  content: '';
  position: sticky;
  display: block;
  bottom: -1rem;
  height: 0;
  pointer-events: none;
  box-shadow: 0 -14rem 0 14rem rgba(2, 6, 23, 0.02);
}

.console-line {
  display: flex;
  gap: 0.6rem;
  line-height: 1.7;
  text-shadow: 0 0 10px rgba(52, 211, 153, 0.22);
}

.fade-in { animation: fade-in 0.5s ease-out; }
.slide-in-from-top-4 { animation: slide-in-from-top-4 0.5s ease-out; }
.slide-in-from-bottom-2 { animation: slide-in-from-bottom-2 0.5s ease-out; }
.slide-in-from-bottom-8 { animation: slide-in-from-bottom-8 0.5s ease-out; }
.undo-pulse { animation: undo-pulse 2.2s ease-in-out infinite; }
</style>
