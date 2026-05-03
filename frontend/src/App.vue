<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import axios from 'axios'
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Check,
  CheckCircle,
  FileText,
  FolderOpen,
  HardDrive,
  Loader2,
  Shield,
  Sparkles,
  Eye,
  X,
  Search,
  Filter,
  ChevronDown,
  Star,
  Clock,
  Copy,
  Settings,
  Trash2,
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

// 文件预览功能
const isPreviewingFile = ref(false)
const previewingFile = ref(null)
const previewContent = ref(null)
const previewError = ref(null)

// 操作历史记录功能
const isShowingHistory = ref(false)
const isLoadingHistory = ref(false)
const historyList = ref([])
const selectedHistory = ref(null)
const historyError = ref(null)

// 文件搜索和过滤功能
const searchQuery = ref('')
const selectedCategory = ref('all')
const isShowingFilters = ref(false)

// 文件时间线视图和收藏功能
const viewMode = ref('list') // 'list' 或 'timeline'
const favoriteFiles = ref(new Set())
const showFavoritesOnly = ref(false)
const isLoadingFavorites = ref(false)

// 文件去重功能
const isDetectingDuplicates = ref(false)
const isShowingDuplicates = ref(false)
const isProcessingDuplicates = ref(false)
const duplicateGroups = ref([])
const selectedKeepFiles = ref({})
const duplicateError = ref(null)
const duplicateResult = ref(null)

// 规则模板系统
const isShowingTemplates = ref(false)
const isLoadingTemplates = ref(false)
const isApplyingTemplate = ref(false)
const templates = ref([])
const selectedTemplate = ref(null)
const templateError = ref(null)
const templateResult = ref(null)

// 模板编辑相关
const isEditingTemplate = ref(false)
const editingTemplate = ref(null)
const editingRule = ref(null)

// 智能批量重命名工具
const isShowingRenamer = ref(false)
const isLoadingRenamePreview = ref(false)
const isExecutingRename = ref(false)
const renameSelectedFiles = ref([])
const renameRules = ref([])
const renamePreviews = ref([])
const renameConflicts = ref([])
const renameHasConflicts = ref(false)
const renameError = ref(null)
const renameResult = ref(null)
const activeRenameRuleType = ref('prefix')

const RENAME_RULE_TYPES = [
  { value: 'prefix', label: '添加前缀', icon: '➕' },
  { value: 'suffix', label: '添加后缀', icon: '➕' },
  { value: 'find_replace', label: '查找替换', icon: '🔄' },
  { value: 'regex', label: '正则替换', icon: '🔍' },
  { value: 'numbering', label: '批量编号', icon: '🔢' },
  { value: 'date_prefix', label: '日期前缀', icon: '📅' },
  { value: 'date_suffix', label: '日期后缀', icon: '📅' },
]

// 数据可视化仪表盘
const isShowingDashboard = ref(false)
const isLoadingDashboard = ref(false)
const dashboardStats = ref(null)
const dashboardError = ref(null)

// 多目录批量处理
const isShowingMultiTargets = ref(false)
const isMultiScanning = ref(false)
const isMultiGeneratingPlan = ref(false)
const multiTargets = ref([])
const multiScanResults = ref([])
const multiPlanResults = ref([])
const multiError = ref(null)
const newMultiTargetPath = ref('')
const isMultiMode = ref(false)

// 计划预览和二次确认
const isShowingPlanPreview = ref(false)
const isLoadingPreview = ref(false)
const planPreviewData = ref(null)
const planPreviewError = ref(null)
const needFinalConfirmation = ref(false)
const finalConfirmChecked = ref(false)

const CATEGORY_COLORS = {
  images: '#10b981',
  documents: '#3b82f6',
  archives: '#a855f7',
  code: '#84cc16',
  logs: '#f59e0b',
  unknown: '#64748b',
}

const CATEGORY_LABELS = {
  images: '图片',
  documents: '文档',
  archives: '压缩包',
  code: '代码',
  logs: '日志',
  unknown: '其他',
}

const SIZE_BUCKET_LABELS = {
  tiny: '< 100KB',
  small: '100KB - 1MB',
  medium: '1MB - 10MB',
  large: '10MB - 100MB',
  huge: '> 100MB',
}

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

// 文件搜索和过滤的计算属性
const filteredFiles = computed(() => {
  let result = [...files.value]
  
  // 搜索过滤
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.trim().toLowerCase()
    result = result.filter(file => 
      file.name.toLowerCase().includes(query) || 
      file.path.toLowerCase().includes(query) ||
      (file.extension && file.extension.toLowerCase().includes(query))
    )
  }
  
  // 分类过滤
  if (selectedCategory.value !== 'all') {
    result = result.filter(file => file.category === selectedCategory.value)
  }
  
  // 收藏过滤
  if (showFavoritesOnly.value) {
    result = result.filter(file => favoriteFiles.value.has(file.path))
  }
  
  return result
})

// 计算不同分类的文件数量，用于过滤选项
const categoryStats = computed(() => {
  const stats = {}
  files.value.forEach(file => {
    const cat = file.category || 'unknown'
    stats[cat] = (stats[cat] || 0) + 1
  })
  return stats
})

// 时间线视图的分组文件（按扩展名或目录分组）
const timelineGroups = computed(() => {
  const groups = {}
  
  filteredFiles.value.forEach(file => {
    // 按扩展名分组
    const ext = file.extension || 'unknown'
    if (!groups[ext]) {
      groups[ext] = {
        name: ext.toUpperCase(),
        files: [],
        totalSize: 0,
        count: 0
      }
    }
    groups[ext].files.push(file)
    groups[ext].totalSize += file.size || 0
    groups[ext].count++
  })
  
  // 转换为数组并排序
  return Object.values(groups).sort((a, b) => b.count - a.count)
})

// 文件夹大小分析
const folderAnalysis = computed(() => {
  const totalFiles = files.value.length
  const totalSize = files.value.reduce((sum, file) => sum + (file.size || 0), 0)
  
  // 按分类统计大小
  const categorySizes = {}
  files.value.forEach(file => {
    const cat = file.category || 'unknown'
    if (!categorySizes[cat]) {
      categorySizes[cat] = 0
    }
    categorySizes[cat] += file.size || 0
  })
  
  // 找出最大的文件
  const largestFiles = [...files.value]
    .sort((a, b) => (b.size || 0) - (a.size || 0))
    .slice(0, 10)
  
  return {
    totalFiles,
    totalSize,
    categorySizes,
    largestFiles
  }
})

// 分类标签映射
const categoryLabels = {
  logs: '日志文件',
  images: '图片',
  documents: '文档',
  archives: '压缩包',
  code: '代码文件',
  unknown: '未知类型'
}

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

const extractErrorMessage = (error) => {
  if (!error) {
    return '未知错误'
  }

  if (error.response) {
    if (error.response.data && error.response.data.detail) {
      return error.response.data.detail
    }
    
    const status = error.response.status
    switch (status) {
      case 400:
        return '请求参数错误，请检查输入'
      case 404:
        return '请求的资源不存在'
      case 409:
        return error.response.data?.detail || '操作冲突，请重试'
      case 500:
        return '服务器内部错误，请稍后再试'
      case 502:
      case 503:
      case 504:
        return '服务器暂时不可用，请稍后再试'
      default:
        return `请求失败 (状态码: ${status})`
    }
  }

  if (error.request) {
    if (error.code === 'ECONNABORTED') {
      return '请求超时，请检查网络连接后重试'
    }
    if (error.code === 'ERR_NETWORK' || error.message?.includes('Network Error')) {
      return '网络连接失败，请检查后端服务是否启动'
    }
    return '无法连接到服务器，请检查网络连接'
  }

  if (error.message) {
    return error.message
  }

  return '未知错误'
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
    error.value = extractErrorMessage(err)
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
    error.value = extractErrorMessage(err)
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
    error.value = extractErrorMessage(err)
    addLog(`[错误] LLM 计划生成失败: ${error.value}`, 'error')
    console.error('Generate plan error:', err)
  } finally {
    isGeneratingPlan.value = false
  }
}

const loadPlanPreview = async () => {
  if (!targetPath.value || !actionPlan.value || actionPlan.value.length === 0) {
    return false
  }

  isLoadingPreview.value = true
  planPreviewError.value = null

  try {
    addLog('[安全] 正在执行计划预检查...', 'info')

    const response = await axios.post('/api/preview_plan', {
      target_path: targetPath.value,
      plan: actionPlan.value,
    })

    planPreviewData.value = response.data
    isShowingPlanPreview.value = true

    const safetyLevel = response.data.safety_level
    const safetyReasons = response.data.safety_reasons || []

    if (safetyLevel === 'danger') {
      addLog(`[安全警告] 检测到危险操作: ${safetyReasons.join(', ')}`, 'warning')
      needFinalConfirmation.value = true
    } else if (safetyLevel === 'warning') {
      addLog(`[安全提示] ${safetyReasons.join(', ')}`, 'info')
      needFinalConfirmation.value = response.data.delete_count > 0
    } else {
      needFinalConfirmation.value = false
    }

    return true
  } catch (err) {
    planPreviewError.value = extractErrorMessage(err)
    addLog(`[错误] 计划预检查失败: ${planPreviewError.value}`, 'error')
    console.error('Preview plan error:', err)
    return false
  } finally {
    isLoadingPreview.value = false
  }
}

const approveAndExecute = async () => {
  if (!targetPath.value || actionPlan.value.length === 0) {
    return
  }

  const previewSuccess = await loadPlanPreview()
  
  if (!previewSuccess) {
    addLog('[安全] 计划预检查失败，中止执行', 'error')
    return
  }
}

const executePlanDirectly = async () => {
  if (!targetPath.value || actionPlan.value.length === 0) {
    return
  }

  if (needFinalConfirmation.value && !finalConfirmChecked.value) {
    addLog('[安全] 请确认已知晓操作风险后再执行', 'warning')
    return
  }

  isShowingPlanPreview.value = false
  finalConfirmChecked.value = false

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
    error.value = extractErrorMessage(err)
    addLog(`[错误] 执行炼金计划失败: ${error.value}`, 'error')
    console.error('Execute plan error:', err)
  } finally {
    isExecutingPlan.value = false
    planPreviewData.value = null
    needFinalConfirmation.value = false
  }
}

const cancelPlanPreview = () => {
  isShowingPlanPreview.value = false
  planPreviewData.value = null
  planPreviewError.value = null
  needFinalConfirmation.value = false
  finalConfirmChecked.value = false
}

const getSafetyLevelClass = (level) => {
  switch (level) {
    case 'danger':
      return 'text-red-400 bg-red-500/10 border-red-400/20'
    case 'warning':
      return 'text-amber-400 bg-amber-500/10 border-amber-400/20'
    default:
      return 'text-emerald-400 bg-emerald-500/10 border-emerald-400/20'
  }
}

const getSafetyLevelLabel = (level) => {
  switch (level) {
    case 'danger':
      return '高风险'
    case 'warning':
      return '中风险'
    default:
      return '安全'
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
    error.value = extractErrorMessage(err)
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

// 文件预览功能
const previewFile = async (file) => {
  if (!targetPath.value || !file.path) {
    error.value = '无法预览文件：缺少目标目录或文件路径'
    return
  }

  isPreviewingFile.value = true
  previewingFile.value = file
  previewContent.value = null
  previewError.value = null

  try {
    addLog(`[系统] 正在预览文件: ${file.name}`, 'info')
    const response = await axios.post('/api/preview_file', {
      target_path: targetPath.value,
      file_path: file.path,
    })

    if (response.data.status === 'success') {
      previewContent.value = response.data.preview
      addLog(`[系统] 文件预览成功: ${file.name}`, 'info')
    } else {
      previewError.value = '预览失败：服务器返回错误状态'
      addLog(`[错误] 文件预览失败: ${previewError.value}`, 'error')
    }
  } catch (err) {
    previewError.value = extractErrorMessage(err)
    addLog(`[错误] 文件预览失败: ${previewError.value}`, 'error')
    console.error('Preview file error:', err)
  }
}

const closePreview = () => {
  isPreviewingFile.value = false
  previewingFile.value = null
  previewContent.value = null
  previewError.value = null
}

// 操作历史记录功能
const loadHistory = async () => {
  if (!targetPath.value) {
    historyError.value = '无法加载历史记录：缺少目标目录'
    return
  }

  isLoadingHistory.value = true
  historyError.value = null

  try {
    addLog('[系统] 正在加载操作历史记录...', 'info')
    const response = await axios.post('/api/list_history', {
      target_path: targetPath.value,
    })

    if (response.data.status === 'success') {
      historyList.value = response.data.history || []
      addLog(`[系统] 历史记录加载完成，共 ${historyList.value.length} 条记录`, 'info')
    } else {
      historyError.value = '加载历史记录失败：服务器返回错误状态'
      addLog(`[错误] 历史记录加载失败: ${historyError.value}`, 'error')
    }
  } catch (err) {
    historyError.value = extractErrorMessage(err)
    addLog(`[错误] 历史记录加载失败: ${historyError.value}`, 'error')
    console.error('Load history error:', err)
  } finally {
    isLoadingHistory.value = false
  }
}

const showHistory = async () => {
  isShowingHistory.value = true
  selectedHistory.value = null
  historyError.value = null
  await loadHistory()
}

const hideHistory = () => {
  isShowingHistory.value = false
  selectedHistory.value = null
  historyError.value = null
}

const viewHistoryDetail = async (historyItem) => {
  if (!targetPath.value || !historyItem.id) {
    historyError.value = '无法查看历史记录详情：缺少目标目录或历史记录ID'
    return
  }

  try {
    addLog(`[系统] 正在查看历史记录详情: ${historyItem.id}`, 'info')
    const response = await axios.post('/api/get_history', {
      target_path: targetPath.value,
      history_id: historyItem.id,
    })

    if (response.data.status === 'success') {
      selectedHistory.value = response.data.history
      addLog(`[系统] 历史记录详情加载成功`, 'info')
    } else {
      historyError.value = '加载历史记录详情失败：服务器返回错误状态'
      addLog(`[错误] 历史记录详情加载失败: ${historyError.value}`, 'error')
    }
  } catch (err) {
    historyError.value = extractErrorMessage(err)
    addLog(`[错误] 历史记录详情加载失败: ${historyError.value}`, 'error')
    console.error('Load history detail error:', err)
  }
}

const closeHistoryDetail = () => {
  selectedHistory.value = null
}

// 格式化日期时间
const formatDateTime = (dateTimeStr) => {
  if (!dateTimeStr) return '—'
  try {
    const date = new Date(dateTimeStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
  } catch {
    return dateTimeStr
  }
}

// 文件收藏功能
const toggleFavorite = (file) => {
  if (favoriteFiles.value.has(file.path)) {
    favoriteFiles.value.delete(file.path)
    addLog(`[系统] 已取消收藏: ${file.name}`, 'info')
  } else {
    favoriteFiles.value.add(file.path)
    addLog(`[系统] 已添加收藏: ${file.name}`, 'info')
  }
}

// 清除搜索和过滤
const clearFilters = () => {
  searchQuery.value = ''
  selectedCategory.value = 'all'
  showFavoritesOnly.value = false
  addLog('[系统] 已清除所有搜索和过滤条件', 'info')
}

// 切换视图模式
const toggleViewMode = () => {
  viewMode.value = viewMode.value === 'list' ? 'timeline' : 'list'
  addLog(`[系统] 已切换到${viewMode.value === 'list' ? '列表视图' : '时间线视图'}`, 'info')
}

// 文件去重功能计算属性
const hasDuplicates = computed(() => duplicateGroups.value.length > 0)

const totalDuplicateSize = computed(() => {
  return duplicateGroups.value.reduce((total, group) => {
    return total + (group.size * (group.files.length - 1))
  }, 0)
})

const totalDuplicateCount = computed(() => {
  return duplicateGroups.value.reduce((total, group) => {
    return total + (group.files.length - 1)
  }, 0)
})

// 文件去重功能方法
const detectDuplicates = async () => {
  if (!targetPath.value) {
    duplicateError.value = '无法检测重复文件：缺少目标目录'
    return
  }

  isDetectingDuplicates.value = true
  duplicateError.value = null
  duplicateGroups.value = []
  selectedKeepFiles.value = {}

  try {
    addLog('[系统] 正在检测重复文件...', 'info')
    const response = await axios.post('/api/detect_duplicates', {
      target_path: targetPath.value,
      fast_mode: true
    })

    if (response.data.status === 'success') {
      duplicateGroups.value = response.data.duplicate_groups || []
      
      duplicateGroups.value.forEach((group, index) => {
        if (group.files && group.files.length > 0) {
          selectedKeepFiles.value[index] = group.files[0].path
        }
      })

      if (duplicateGroups.value.length > 0) {
        addLog(`[系统] 检测完成，发现 ${duplicateGroups.value.length} 组重复文件，共 ${totalDuplicateCount.value} 个冗余文件`, 'info')
        addLog(`[系统] 可释放空间：${formatBytes(totalDuplicateSize.value)}`, 'info')
      } else {
        addLog('[系统] 检测完成，未发现重复文件', 'info')
      }
    } else {
      duplicateError.value = '检测重复文件失败：服务器返回错误状态'
      addLog(`[错误] 重复文件检测失败: ${duplicateError.value}`, 'error')
    }
  } catch (err) {
    duplicateError.value = extractErrorMessage(err)
    addLog(`[错误] 重复文件检测失败: ${duplicateError.value}`, 'error')
    console.error('Detect duplicates error:', err)
  } finally {
    isDetectingDuplicates.value = false
  }
}

const showDuplicates = async () => {
  isShowingDuplicates.value = true
  duplicateError.value = null
  duplicateResult.value = null
  await detectDuplicates()
}

const hideDuplicates = () => {
  isShowingDuplicates.value = false
  duplicateError.value = null
  duplicateResult.value = null
}

const selectKeepFile = (groupIndex, filePath) => {
  selectedKeepFiles.value[groupIndex] = filePath
}

const processKeepSelected = async (groupIndex) => {
  if (!targetPath.value) {
    duplicateError.value = '无法处理：缺少目标目录'
    return
  }

  const group = duplicateGroups.value[groupIndex]
  if (!group || !group.files) {
    return
  }

  const keepFile = selectedKeepFiles.value[groupIndex]
  if (!keepFile) {
    duplicateError.value = '请先选择要保留的文件'
    return
  }

  const duplicateFiles = group.files
    .filter(f => f.path !== keepFile)
    .map(f => f.path)

  if (duplicateFiles.length === 0) {
    return
  }

  isProcessingDuplicates.value = true
  duplicateError.value = null

  try {
    addLog(`[系统] 正在处理重复文件：保留 ${keepFile}，删除 ${duplicateFiles.length} 个副本...`, 'info')
    
    const response = await axios.post('/api/keep_duplicate', {
      target_path: targetPath.value,
      keep_file: keepFile,
      duplicate_files: duplicateFiles
    })

    if (response.data.status === 'success') {
      duplicateResult.value = response.data
      addLog(`[系统] 处理完成：已删除 ${response.data.deleted_count} 个重复文件`, 'info')
      
      duplicateGroups.value = duplicateGroups.value.filter((_, idx) => idx !== groupIndex)
      delete selectedKeepFiles.value[groupIndex]
      
      files.value = files.value.filter(f => f.path !== keepFile || !duplicateFiles.includes(f.path))
    } else {
      duplicateError.value = '处理重复文件失败：服务器返回错误状态'
      addLog(`[错误] 处理重复文件失败: ${duplicateError.value}`, 'error')
    }
  } catch (err) {
    duplicateError.value = extractErrorMessage(err)
    addLog(`[错误] 处理重复文件失败: ${duplicateError.value}`, 'error')
    console.error('Keep duplicate error:', err)
  } finally {
    isProcessingDuplicates.value = false
  }
}

const processAllDuplicates = async () => {
  if (!hasDuplicates.value) {
    return
  }

  for (let i = duplicateGroups.value.length - 1; i >= 0; i--) {
    if (selectedKeepFiles.value[i]) {
      await processKeepSelected(i)
    }
  }
}

// 规则模板系统方法
const loadTemplates = async () => {
  isLoadingTemplates.value = true
  templateError.value = null

  try {
    const response = await axios.get('/api/list_templates')

    if (response.data.status === 'success') {
      templates.value = response.data.templates || []
      addLog(`[系统] 已加载 ${templates.value.length} 个模板`, 'info')
    } else {
      templateError.value = '加载模板列表失败：服务器返回错误状态'
      addLog(`[错误] 加载模板列表失败: ${templateError.value}`, 'error')
    }
  } catch (err) {
    templateError.value = extractErrorMessage(err)
    addLog(`[错误] 加载模板列表失败: ${templateError.value}`, 'error')
    console.error('Load templates error:', err)
  } finally {
    isLoadingTemplates.value = false
  }
}

const showTemplates = async () => {
  isShowingTemplates.value = true
  isEditingTemplate.value = false
  templateError.value = null
  templateResult.value = null
  await loadTemplates()
}

const hideTemplates = () => {
  isShowingTemplates.value = false
  isEditingTemplate.value = false
  editingTemplate.value = null
  editingRule.value = null
  templateError.value = null
  templateResult.value = null
}

const applyTemplate = async (template) => {
  if (!targetPath.value) {
    templateError.value = '无法应用模板：缺少目标目录'
    return
  }

  isApplyingTemplate.value = true
  templateError.value = null

  try {
    addLog(`[系统] 正在应用模板：${template.name}...`, 'info')

    const response = await axios.post('/api/apply_template', {
      target_path: targetPath.value,
      template_id: template.id
    })

    if (response.data.status === 'success') {
      const data = response.data

      mode.value = data.mode || 'execute'
      analysis.value = data.analysis || null
      files.value = data.files || []
      fileInventory.value = data.file_inventory || []
      actionPlan.value = data.plan || []
      reasoningTrace.value = data.reasoning_trace || []
      templateResult.value = data

      addLog(`[系统] 模板应用成功，生成 ${actionPlan.value.length} 条整理计划`, 'info')

      hideTemplates()
    } else {
      templateError.value = '应用模板失败：服务器返回错误状态'
      addLog(`[错误] 应用模板失败: ${templateError.value}`, 'error')
    }
  } catch (err) {
    templateError.value = extractErrorMessage(err)
    addLog(`[错误] 应用模板失败: ${templateError.value}`, 'error')
    console.error('Apply template error:', err)
  } finally {
    isApplyingTemplate.value = false
  }
}

const createNewTemplate = () => {
  editingTemplate.value = {
    id: '',
    name: '新建模板',
    description: '描述这个模板的用途...',
    icon: '📁',
    rules: []
  }
  isEditingTemplate.value = true
  editingRule.value = null
}

const editTemplate = (template) => {
  if (template.is_builtin) {
    addLog('[提示] 内置模板不可编辑，但可以复制', 'info')
    return
  }

  editingTemplate.value = JSON.parse(JSON.stringify(template))
  isEditingTemplate.value = true
  editingRule.value = null
}

const saveTemplate = async () => {
  if (!editingTemplate.value) {
    return
  }

  if (!editingTemplate.value.name.trim()) {
    templateError.value = '模板名称不能为空'
    return
  }

  try {
    const response = await axios.post('/api/save_template', {
      template: editingTemplate.value
    })

    if (response.data.status === 'success') {
      addLog(`[系统] 模板 "${editingTemplate.value.name}" 保存成功`, 'info')
      isEditingTemplate.value = false
      editingTemplate.value = null
      editingRule.value = null
      await loadTemplates()
    } else {
      templateError.value = '保存模板失败：服务器返回错误状态'
      addLog(`[错误] 保存模板失败: ${templateError.value}`, 'error')
    }
  } catch (err) {
    templateError.value = extractErrorMessage(err)
    addLog(`[错误] 保存模板失败: ${templateError.value}`, 'error')
    console.error('Save template error:', err)
  }
}

const deleteTemplate = async (template) => {
  if (template.is_builtin) {
    templateError.value = '内置模板不可删除'
    return
  }

  if (!confirm(`确定要删除模板 "${template.name}" 吗？此操作不可恢复。`)) {
    return
  }

  try {
    const response = await axios.post('/api/delete_template', {
      template_id: template.id
    })

    if (response.data.status === 'success') {
      addLog(`[系统] 模板 "${template.name}" 已删除`, 'info')
      await loadTemplates()
    } else {
      templateError.value = '删除模板失败：服务器返回错误状态'
      addLog(`[错误] 删除模板失败: ${templateError.value}`, 'error')
    }
  } catch (err) {
    templateError.value = extractErrorMessage(err)
    addLog(`[错误] 删除模板失败: ${templateError.value}`, 'error')
    console.error('Delete template error:', err)
  }
}

const addNewRule = () => {
  if (!editingTemplate.value) {
    return
  }

  const newRule = {
    rule_id: `rule-${Date.now()}`,
    name: '新规则',
    match_extensions: [],
    match_pattern: '',
    match_category: '',
    action: 'move',
    target_path: '',
    reason: '',
    priority: 0
  }

  editingTemplate.value.rules.push(newRule)
  editingRule.value = newRule
}

const editRule = (rule) => {
  editingRule.value = rule
}

const deleteRule = (rule) => {
  if (!editingTemplate.value) {
    return
  }

  const index = editingTemplate.value.rules.indexOf(rule)
  if (index > -1) {
    editingTemplate.value.rules.splice(index, 1)
    if (editingRule.value === rule) {
      editingRule.value = null
    }
  }
}

const duplicateTemplate = (template) => {
  editingTemplate.value = {
    id: '',
    name: `${template.name} (副本)`,
    description: template.description || '',
    icon: template.icon || '📁',
    rules: JSON.parse(JSON.stringify(template.rules || []))
  }
  isEditingTemplate.value = true
  editingRule.value = null
}

const cancelEditTemplate = () => {
  isEditingTemplate.value = false
  editingTemplate.value = null
  editingRule.value = null
}

// 智能批量重命名工具方法
const showRenamer = () => {
  if (!files.value || files.value.length === 0) {
    addLog('[提示] 请先选择目标目录并扫描文件', 'info')
    return
  }

  isShowingRenamer.value = true
  renameSelectedFiles.value = []
  renameRules.value = []
  renamePreviews.value = []
  renameConflicts.value = []
  renameHasConflicts.value = false
  renameError.value = null
  renameResult.value = null
  activeRenameRuleType.value = 'prefix'
}

const hideRenamer = () => {
  isShowingRenamer.value = false
  renameSelectedFiles.value = []
  renameRules.value = []
  renamePreviews.value = []
  renameConflicts.value = []
  renameHasConflicts.value = false
  renameError.value = null
  renameResult.value = null
}

const toggleRenameFileSelection = (filePath) => {
  const index = renameSelectedFiles.value.indexOf(filePath)
  if (index > -1) {
    renameSelectedFiles.value.splice(index, 1)
  } else {
    renameSelectedFiles.value.push(filePath)
  }
}

const selectAllRenameFiles = () => {
  if (files.value) {
    renameSelectedFiles.value = files.value.map(f => f.path)
  }
}

const clearRenameSelection = () => {
  renameSelectedFiles.value = []
  renamePreviews.value = []
  renameConflicts.value = []
  renameHasConflicts.value = false
}

const addRenameRule = () => {
  const newRule = {
    rule_type: activeRenameRuleType.value,
    prefix: '',
    suffix: '',
    find_text: '',
    replace_text: '',
    regex_pattern: '',
    regex_replacement: '',
    start_number: 1,
    number_padding: 3,
    number_separator: '_',
    number_position: 'prefix'
  }
  renameRules.value.push(newRule)
}

const removeRenameRule = (index) => {
  renameRules.value.splice(index, 1)
}

const clearRenameRules = () => {
  renameRules.value = []
  renamePreviews.value = []
  renameConflicts.value = []
  renameHasConflicts.value = false
}

const generateRenamePreview = async () => {
  if (!targetPath.value) {
    renameError.value = '缺少目标目录'
    return
  }

  if (renameSelectedFiles.value.length === 0) {
    renameError.value = '请先选择要重命名的文件'
    return
  }

  if (renameRules.value.length === 0) {
    renameError.value = '请添加至少一条重命名规则'
    return
  }

  isLoadingRenamePreview.value = true
  renameError.value = null

  try {
    addLog('[系统] 正在生成重命名预览...', 'info')

    const response = await axios.post('/api/rename_preview', {
      target_path: targetPath.value,
      selected_files: renameSelectedFiles.value,
      rules: renameRules.value
    })

    if (response.data.status === 'success') {
      renamePreviews.value = response.data.previews || []
      renameConflicts.value = response.data.conflicts || []
      renameHasConflicts.value = response.data.has_conflicts || false

      addLog(`[系统] 预览生成完成：${response.data.changed_count} 个文件将被重命名`, 'info')
      
      if (renameHasConflicts.value) {
        addLog(`[警告] 检测到 ${renameConflicts.value.length} 个冲突`, 'warning')
      }
    } else {
      renameError.value = '生成预览失败：服务器返回错误状态'
      addLog(`[错误] 生成重命名预览失败: ${renameError.value}`, 'error')
    }
  } catch (err) {
    renameError.value = extractErrorMessage(err)
    addLog(`[错误] 生成重命名预览失败: ${renameError.value}`, 'error')
    console.error('Generate rename preview error:', err)
  } finally {
    isLoadingRenamePreview.value = false
  }
}

const executeRename = async () => {
  if (!targetPath.value) {
    renameError.value = '缺少目标目录'
    return
  }

  if (renamePreviews.value.length === 0) {
    renameError.value = '请先生成重命名预览'
    return
  }

  if (renameHasConflicts.value) {
    if (!confirm('检测到命名冲突，是否忽略冲突并继续？（冲突的文件将不会被重命名）')) {
      return
    }
  }

  isExecutingRename.value = true
  renameError.value = null

  try {
    addLog('[系统] 正在执行批量重命名...', 'info')

    const response = await axios.post('/api/rename_execute', {
      target_path: targetPath.value,
      rename_plan: renamePreviews.value
    })

    if (response.data.status === 'success') {
      renameResult.value = response.data
      addLog(`[系统] 重命名完成：成功重命名 ${response.data.executed} 个文件`, 'info')

      hideRenamer()

      if (files.value.length > 0) {
        const responseList = await axios.post('/api/list_files', {
          target_path: targetPath.value
        })
        if (responseList.data.status === 'success') {
          files.value = responseList.data.files
        }
      }
    } else {
      renameError.value = '执行重命名失败：服务器返回错误状态'
      addLog(`[错误] 执行重命名失败: ${renameError.value}`, 'error')
    }
  } catch (err) {
    renameError.value = extractErrorMessage(err)
    addLog(`[错误] 执行重命名失败: ${renameError.value}`, 'error')
    console.error('Execute rename error:', err)
  } finally {
    isExecutingRename.value = false
  }
}

const getRenameRuleLabel = (rule) => {
  const typeInfo = RENAME_RULE_TYPES.find(t => t.value === rule.rule_type)
  if (!typeInfo) return '未知规则'

  if (rule.rule_type === 'prefix') {
    return `${typeInfo.label}: "${rule.prefix}"`
  } else if (rule.rule_type === 'suffix') {
    return `${typeInfo.label}: "${rule.suffix}"`
  } else if (rule.rule_type === 'find_replace') {
    return `${typeInfo.label}: "${rule.find_text}" → "${rule.replace_text}"`
  } else if (rule.rule_type === 'regex') {
    return `${typeInfo.label}: ${rule.regex_pattern}`
  } else if (rule.rule_type === 'numbering') {
    return `${typeInfo.label}: 从 ${rule.start_number} 开始 (${rule.number_position === 'prefix' ? '前缀' : rule.number_position === 'suffix' ? '后缀' : '替换'})`
  }
  return typeInfo.label
}

// 数据可视化仪表盘方法
const showDashboard = async () => {
  if (!targetPath.value) {
    addLog('[提示] 请先选择目标目录', 'info')
    return
  }

  isShowingDashboard.value = true
  dashboardStats.value = null
  dashboardError.value = null
  await loadDashboardStats()
}

const hideDashboard = () => {
  isShowingDashboard.value = false
  dashboardStats.value = null
  dashboardError.value = null
}

const loadDashboardStats = async () => {
  if (!targetPath.value) {
    return
  }

  isLoadingDashboard.value = true
  dashboardError.value = null

  try {
    addLog('[系统] 正在生成数据可视化报表...', 'info')

    const response = await axios.post('/api/dashboard_stats', {
      target_path: targetPath.value
    })

    if (response.data.status === 'success') {
      dashboardStats.value = response.data.stats
      addLog('[系统] 数据可视化报表生成完成', 'info')
    } else {
      dashboardError.value = '生成报表失败：服务器返回错误状态'
      addLog(`[错误] 生成仪表盘统计失败: ${dashboardError.value}`, 'error')
    }
  } catch (err) {
    dashboardError.value = extractErrorMessage(err)
    addLog(`[错误] 生成仪表盘统计失败: ${dashboardError.value}`, 'error')
    console.error('Load dashboard stats error:', err)
  } finally {
    isLoadingDashboard.value = false
  }
}

const calculatePieChartPercentages = () => {
  if (!dashboardStats.value?.overview?.categories) {
    return []
  }

  const categories = dashboardStats.value.overview.categories
  const total = Object.values(categories).reduce((sum, cat) => sum + (cat.count || 0), 0)
  
  let currentAngle = 0
  const segments = []

  for (const [key, data] of Object.entries(categories)) {
    const count = data.count || 0
    if (count === 0) continue

    const percentage = total > 0 ? (count / total) * 100 : 0
    const angle = total > 0 ? (count / total) * 360 : 0

    segments.push({
      key,
      count,
      size: data.size,
      percentage: percentage.toFixed(1),
      angle,
      startAngle: currentAngle,
      endAngle: currentAngle + angle,
      color: CATEGORY_COLORS[key] || '#64748b',
      label: CATEGORY_LABELS[key] || key
    })

    currentAngle += angle
  }

  return segments
}

const getSizeDistributionData = () => {
  if (!dashboardStats.value?.size_distribution) {
    return []
  }

  const sizeDist = dashboardStats.value.size_distribution
  const total = Object.values(sizeDist).reduce((sum, b) => sum + (b.count || 0), 0)

  return Object.entries(sizeDist).map(([key, bucket]) => ({
    key,
    count: bucket.count || 0,
    size: bucket.size || 0,
    label: SIZE_BUCKET_LABELS[key] || key,
    percentage: total > 0 ? ((bucket.count || 0) / total) * 100 : 0,
  })).filter(b => b.count > 0)
}

const getWeeklyActivityData = () => {
  if (!dashboardStats.value?.weekly_activity) {
    return []
  }

  return dashboardStats.value.weekly_activity
}

// 多目录批量处理方法
const showMultiTargets = () => {
  isShowingMultiTargets.value = true
  multiTargets.value = []
  multiScanResults.value = []
  multiPlanResults.value = []
  multiError.value = null
  isMultiMode.value = false
}

const hideMultiTargets = () => {
  isShowingMultiTargets.value = false
  if (!isMultiMode.value) {
    multiTargets.value = []
    multiScanResults.value = []
    multiPlanResults.value = []
    multiError.value = null
  }
}

const addMultiTarget = () => {
  const path = newMultiTargetPath.value.trim()
  if (!path) {
    return
  }
  
  if (multiTargets.value.includes(path)) {
    multiError.value = '该目录已添加'
    return
  }
  
  multiTargets.value.push(path)
  newMultiTargetPath.value = ''
  multiError.value = null
}

const removeMultiTarget = (index) => {
  multiTargets.value.splice(index, 1)
}

const addMultiTargetViaDialog = async () => {
  addLog('[系统] 请求系统原生目录选择器...', 'info')
  
  try {
    const response = await axios.get('/api/select_folder')
    if (response.data.status === 'cancelled' || !response.data.target_path) {
      addLog('[系统] 目录选择已取消', 'info')
      return
    }

    const path = response.data.target_path
    if (multiTargets.value.includes(path)) {
      multiError.value = '该目录已添加'
      return
    }
    
    multiTargets.value.push(path)
    addLog(`[系统] 已添加目录: ${path}`, 'info')
    multiError.value = null
  } catch (err) {
    multiError.value = extractErrorMessage(err)
    addLog(`[错误] 添加目录失败: ${multiError.value}`, 'error')
  }
}

const performMultiScan = async () => {
  if (multiTargets.value.length === 0) {
    multiError.value = '请至少添加一个目标目录'
    return
  }

  isMultiScanning.value = true
  multiError.value = null

  try {
    addLog('[系统] 正在执行多目录扫描...', 'info')

    const response = await axios.post('/api/multi_scan', {
      target_paths: multiTargets.value
    })

    if (response.data.status === 'success') {
      multiScanResults.value = response.data
      isMultiMode.value = true
      
      addLog(`[系统] 多目录扫描完成：${response.data.success_count} 个目录成功，${response.data.total_files} 个文件`, 'info')
      
      files.value = response.data.merged_files
      fileInventory.value = response.data.merged_file_inventory
      analysis.value = response.data.merged_analysis
      
      targetPath.value = response.data.merged_analysis?.target_paths?.[0] || multiTargets.value[0]
    } else {
      multiError.value = '多目录扫描失败：服务器返回错误状态'
      addLog(`[错误] 多目录扫描失败: ${multiError.value}`, 'error')
    }
  } catch (err) {
    multiError.value = extractErrorMessage(err)
    addLog(`[错误] 多目录扫描失败: ${multiError.value}`, 'error')
    console.error('Multi scan error:', err)
  } finally {
    isMultiScanning.value = false
  }
}

const performMultiGeneratePlan = async () => {
  if (multiTargets.value.length === 0) {
    multiError.value = '请至少添加一个目标目录'
    return
  }

  isMultiGeneratingPlan.value = true
  multiError.value = null

  try {
    addLog('[系统] 正在为多目录生成炼金计划...', 'info')

    const response = await axios.post('/api/multi_generate_plan', {
      target_paths: multiTargets.value
    })

    if (response.data.status === 'success') {
      multiPlanResults.value = response.data
      isMultiMode.value = true
      
      addLog(`[系统] 多目录计划生成完成：${response.data.success_count} 个目录成功，共 ${response.data.total_actions} 条行动`, 'info')
      
      actionPlan.value = response.data.merged_plan
      mode.value = response.data.mode || 'multi-directory-plan'
      
      files.value = []
      fileInventory.value = []
      
      for (const result of response.data.plan_results) {
        if (result.status === 'success' && result.files) {
          files.value = [...files.value, ...result.files]
        }
        if (result.status === 'success' && result.file_inventory) {
          fileInventory.value = [...fileInventory.value, ...result.file_inventory]
        }
      }
      
      if (response.data.llm_failed_count > 0) {
        addLog(`[警告] 有 ${response.data.llm_failed_count} 个目录的AI计划生成失败`, 'warning')
      }
    } else {
      multiError.value = '多目录计划生成失败：服务器返回错误状态'
      addLog(`[错误] 多目录计划生成失败: ${multiError.value}`, 'error')
    }
  } catch (err) {
    multiError.value = extractErrorMessage(err)
    addLog(`[错误] 多目录计划生成失败: ${multiError.value}`, 'error')
    console.error('Multi generate plan error:', err)
  } finally {
    isMultiGeneratingPlan.value = false
  }
}

const getHistoryTypeLabels = (type) => {
  const labels = {
    execute: '执行计划',
    undo: '回滚操作',
    deduplicate: '去重操作',
    rename: '重命名操作',
  }
  return labels[type] || type
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
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <h2 class="text-2xl font-bold flex items-center gap-3">
            <CheckCircle class="text-emerald-500" />
            发现待炼化物质 ({{ files.length }})
          </h2>
          <div class="flex items-center gap-2">
            <button
              type="button"
              class="px-3 py-1.5 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-xs"
              :class="[
                viewMode === 'list' 
                  ? 'text-sky-300 border-sky-400/30 bg-sky-500/10' 
                  : 'text-slate-300'
              ]"
              @click="viewMode = 'list'"
              title="列表视图"
            >
              列表视图
            </button>
            <button
              type="button"
              class="px-3 py-1.5 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-xs"
              :class="[
                viewMode === 'timeline' 
                  ? 'text-sky-300 border-sky-400/30 bg-sky-500/10' 
                  : 'text-slate-300'
              ]"
              @click="viewMode = 'timeline'"
              title="时间线视图"
            >
              分组视图
            </button>
            <button
              type="button"
              class="rounded-lg border border-sky-400/30 px-4 py-2 text-sky-100 bg-sky-500/10 hover:bg-sky-500/20 transition-colors text-sm"
              :disabled="isGeneratingPlan || isExecutingPlan || isUndoing"
              @click="showHistory"
            >
              查看历史记录
            </button>
            <button
              type="button"
              class="rounded-lg border border-amber-400/30 px-4 py-2 text-amber-100 bg-amber-500/10 hover:bg-amber-500/20 transition-colors text-sm"
              :disabled="isGeneratingPlan || isExecutingPlan || isUndoing || !targetPath"
              @click="showDuplicates"
            >
              检测重复文件
            </button>
            <button
              type="button"
              class="rounded-lg border border-fuchsia-400/30 px-4 py-2 text-fuchsia-100 bg-fuchsia-500/10 hover:bg-fuchsia-500/20 transition-colors text-sm"
              :disabled="isGeneratingPlan || isExecutingPlan || isUndoing"
              @click="showTemplates"
            >
              规则模板
            </button>
            <button
              type="button"
              class="rounded-lg border border-sky-400/30 px-4 py-2 text-sky-100 bg-sky-500/10 hover:bg-sky-500/20 transition-colors text-sm"
              :disabled="isGeneratingPlan || isExecutingPlan || isUndoing"
              @click="showRenamer"
            >
              批量重命名
            </button>
            <button
              type="button"
              class="rounded-lg border border-amber-400/30 px-4 py-2 text-amber-100 bg-amber-500/10 hover:bg-amber-500/20 transition-colors text-sm"
              :disabled="isGeneratingPlan || isExecutingPlan || isUndoing"
              @click="showDashboard"
            >
              数据可视化
            </button>
            <button
              type="button"
              class="rounded-lg border border-emerald-400/30 px-4 py-2 text-emerald-100 bg-emerald-500/10 hover:bg-emerald-500/20 transition-colors text-sm"
              :disabled="isGeneratingPlan || isExecutingPlan || isUndoing"
              @click="showMultiTargets"
            >
              多目录处理
            </button>
          </div>
        </div>

        <!-- 搜索和过滤区域 -->
        <div class="space-y-3">
          <div class="flex flex-col md:flex-row gap-3">
            <!-- 搜索框 -->
            <div class="relative flex-1">
              <div class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                <Search :size="18" />
              </div>
              <input
                type="text"
                v-model="searchQuery"
                placeholder="搜索文件名、路径或扩展名..."
                class="w-full pl-10 pr-10 py-2.5 rounded-lg glass border border-white/10 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-sky-400/50 transition-colors"
              />
              <button
                v-if="searchQuery"
                type="button"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
                @click="searchQuery = ''"
              >
                <X :size="16" />
              </button>
            </div>

            <!-- 过滤按钮 -->
            <button
              type="button"
              class="flex items-center gap-2 px-4 py-2.5 rounded-lg glass border border-white/10 text-slate-200 hover:bg-white/10 transition-colors"
              @click="isShowingFilters = !isShowingFilters"
            >
              <Filter :size="18" />
              <span>过滤选项</span>
              <ChevronDown :size="16" :class="['transition-transform', isShowingFilters ? 'rotate-180' : '']" />
            </button>
          </div>

          <!-- 过滤选项面板 -->
          <div v-if="isShowingFilters" class="p-4 rounded-lg glass border border-white/10 space-y-4">
            <!-- 分类过滤 -->
            <div>
              <label class="block text-sm text-slate-300 mb-2">文件类型</label>
              <div class="flex flex-wrap gap-2">
                <button
                  type="button"
                  class="px-3 py-1.5 rounded-lg border text-xs transition-colors"
                  :class="[
                    selectedCategory === 'all'
                      ? 'text-sky-300 border-sky-400/30 bg-sky-500/10'
                      : 'border-slate-400/20 bg-white/5 text-slate-300 hover:bg-white/10'
                  ]"
                  @click="selectedCategory = 'all'"
                >
                  全部 ({{ files.length }})
                </button>
                <button
                  v-for="(count, category) in categoryStats"
                  :key="category"
                  type="button"
                  class="px-3 py-1.5 rounded-lg border text-xs transition-colors"
                  :class="[
                    selectedCategory === category
                      ? 'text-sky-300 border-sky-400/30 bg-sky-500/10'
                      : 'border-slate-400/20 bg-white/5 text-slate-300 hover:bg-white/10'
                  ]"
                  @click="selectedCategory = category"
                >
                  {{ categoryLabels[category] || category }} ({{ count }})
                </button>
              </div>
            </div>

            <!-- 收藏过滤 -->
            <div class="flex items-center gap-2">
              <input
                type="checkbox"
                id="showFavoritesOnly"
                v-model="showFavoritesOnly"
                class="w-4 h-4 rounded border-slate-400/50 bg-transparent text-sky-500 focus:ring-sky-500"
              />
              <label for="showFavoritesOnly" class="text-sm text-slate-300 flex items-center gap-2">
                <Star :size="16" :class="showFavoritesOnly ? 'fill-amber-400 text-amber-400' : 'text-slate-400'" />
                只显示收藏的文件
              </label>
            </div>

            <!-- 清除过滤按钮 -->
            <div class="flex justify-end">
              <button
                type="button"
                class="px-4 py-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-slate-300 text-sm"
                @click="clearFilters"
              >
                清除所有过滤
              </button>
            </div>
          </div>
        </div>

        <!-- 搜索结果提示 -->
        <div
          v-if="(searchQuery || selectedCategory !== 'all' || showFavoritesOnly) && filteredFiles.length !== files.length"
          class="p-3 rounded-lg bg-sky-500/10 border border-sky-400/20 text-sky-200 text-sm flex items-center justify-between"
        >
          <span>
            找到 <strong>{{ filteredFiles.length }}</strong> 个匹配的文件（共 {{ files.length }} 个）
          </span>
          <button
            type="button"
            class="text-xs text-sky-300 hover:text-sky-200 underline"
            @click="clearFilters"
          >
            清除过滤
          </button>
        </div>

        <!-- 无搜索结果提示 -->
        <div
          v-if="filteredFiles.length === 0 && (searchQuery || selectedCategory !== 'all' || showFavoritesOnly)"
          class="p-8 rounded-lg glass border border-white/10 text-center"
        >
          <Search :size="48" class="mx-auto mb-4 text-slate-600" />
          <p class="text-slate-300 text-lg">没有找到匹配的文件</p>
          <p class="text-slate-500 text-sm mt-2">请尝试修改搜索条件或清除过滤</p>
          <button
            type="button"
            class="mt-4 px-4 py-2 rounded-lg border border-sky-400/30 bg-sky-500/10 hover:bg-sky-500/20 transition-colors text-sky-100 text-sm"
            @click="clearFilters"
          >
            清除所有过滤
          </button>
        </div>

        <!-- 文件列表视图 -->
        <template v-else-if="viewMode === 'list'">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              v-for="(file, index) in filteredFiles"
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
                  <Star
                    v-if="favoriteFiles.has(file.path)"
                    :size="14"
                    class="fill-amber-400 text-amber-400"
                    title="已收藏"
                  />
                </div>
                <p class="text-xs text-slate-500 font-mono truncate">{{ file.path }}</p>
                <p class="text-xs text-slate-500 font-mono uppercase">{{ file.extension || 'UNKNOWN' }} · {{ formatBytes(file.size) }}</p>
              </div>
              <div class="flex items-center gap-1">
                <button
                  type="button"
                  class="p-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors"
                  @click="toggleFavorite(file)"
                  :title="favoriteFiles.has(file.path) ? '取消收藏' : '添加收藏'"
                >
                  <Star
                    :size="18"
                    :class="[
                      'transition-colors',
                      favoriteFiles.has(file.path) ? 'fill-amber-400 text-amber-400' : 'text-slate-400 hover:text-slate-300'
                    ]"
                  />
                </button>
                <button
                  type="button"
                  class="p-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors disabled:opacity-50"
                  :disabled="isGeneratingPlan || isExecutingPlan"
                  @click="previewFile(file)"
                  title="预览文件"
                >
                  <Eye :size="18" class="text-slate-300" />
                </button>
              </div>
            </div>
          </div>
        </template>

        <!-- 时间线/分组视图 -->
        <template v-else-if="viewMode === 'timeline'">
          <div class="space-y-6">
            <div
              v-for="(group, groupIndex) in timelineGroups"
              :key="group.name"
              class="space-y-3"
            >
              <!-- 分组标题 -->
              <div class="flex items-center gap-3">
                <div class="flex-1 h-px bg-white/10"></div>
                <div class="flex items-center gap-2 px-4 py-1.5 rounded-full bg-slate-800 border border-white/10">
                  <FileText :size="16" class="text-sky-400" />
                  <span class="text-sm text-slate-200 font-medium">{{ group.name }}</span>
                  <span class="text-xs text-slate-500">{{ group.count }} 个文件 · {{ formatBytes(group.totalSize) }}</span>
                </div>
                <div class="flex-1 h-px bg-white/10"></div>
              </div>

              <!-- 分组内的文件列表 -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div
                  v-for="(file, fileIndex) in group.files"
                  :key="`${group.name}-${file.path}`"
                  class="flex items-center gap-3 p-3 rounded-lg bg-slate-900/50 border border-white/5 hover:bg-slate-800/50 hover:border-white/10 transition-all group"
                >
                  <div class="p-2 rounded-lg bg-slate-800 text-slate-500 group-hover:bg-slate-700 group-hover:text-slate-300 transition-colors">
                    <FileText :size="20" />
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                      <p class="text-sm font-medium text-slate-200 truncate">{{ file.name }}</p>
                      <Star
                        v-if="favoriteFiles.has(file.path)"
                        :size="12"
                        class="fill-amber-400 text-amber-400"
                      />
                    </div>
                    <p class="text-xs text-slate-500 font-mono truncate">{{ file.path }}</p>
                  </div>
                  <div class="flex items-center gap-2 text-xs text-slate-500 font-mono">
                    <span>{{ formatBytes(file.size) }}</span>
                    <div class="flex items-center gap-1">
                      <button
                        type="button"
                        class="p-1.5 rounded hover:bg-white/10 transition-colors"
                        @click="toggleFavorite(file)"
                        :title="favoriteFiles.has(file.path) ? '取消收藏' : '添加收藏'"
                      >
                        <Star
                          :size="14"
                          :class="[
                            favoriteFiles.has(file.path) ? 'fill-amber-400 text-amber-400' : 'text-slate-500 hover:text-slate-400'
                          ]"
                        />
                      </button>
                      <button
                        type="button"
                        class="p-1.5 rounded hover:bg-white/10 transition-colors disabled:opacity-50"
                        :disabled="isGeneratingPlan || isExecutingPlan"
                        @click="previewFile(file)"
                        title="预览文件"
                      >
                        <Eye :size="14" class="text-slate-400" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- 文件夹大小分析摘要 -->
        <div class="p-4 rounded-lg glass border border-white/10">
          <h3 class="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
            <HardDrive :size="20" class="text-sky-400" />
            文件夹分析摘要
          </h3>
          
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <!-- 总文件数和大小 -->
            <div class="p-4 rounded-lg bg-slate-900/50 border border-white/5">
              <p class="text-sm text-slate-500 mb-1">总文件数</p>
              <p class="text-2xl font-bold text-slate-200">{{ folderAnalysis.totalFiles }}</p>
              <p class="text-sm text-slate-400 mt-1">总大小：{{ formatBytes(folderAnalysis.totalSize) }}</p>
            </div>

            <!-- 最大的文件 -->
            <div class="p-4 rounded-lg bg-slate-900/50 border border-white/5">
              <p class="text-sm text-slate-500 mb-1">最大文件</p>
              <template v-if="folderAnalysis.largestFiles.length > 0">
                <p class="text-sm font-medium text-slate-200 truncate">
                  {{ folderAnalysis.largestFiles[0].name }}
                </p>
                <p class="text-sm text-slate-400 mt-1">
                  {{ formatBytes(folderAnalysis.largestFiles[0].size) }}
                </p>
              </template>
              <template v-else>
                <p class="text-slate-400">—</p>
              </template>
            </div>

            <!-- 收藏文件数 -->
            <div class="p-4 rounded-lg bg-slate-900/50 border border-white/5">
              <p class="text-sm text-slate-500 mb-1">收藏文件</p>
              <p class="text-2xl font-bold text-amber-400 flex items-center gap-2">
                <Star :size="24" class="fill-amber-400" />
                {{ favoriteFiles.size }}
              </p>
              <button
                v-if="favoriteFiles.size > 0"
                type="button"
                class="text-xs text-amber-400 hover:text-amber-300 mt-1"
                @click="showFavoritesOnly = true"
              >
                点击查看收藏
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 文件预览弹窗 -->
      <div v-if="isPreviewingFile" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
        <div class="relative w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-lg glass-strong border border-white/10 flex flex-col">
          <!-- 弹窗头部 -->
          <div class="flex items-center justify-between p-4 border-b border-white/10">
            <div class="flex items-center gap-3">
              <FileText :size="24" class="text-sky-300" />
              <div>
                <p class="font-medium text-slate-100">{{ previewingFile?.name }}</p>
                <p class="text-xs text-slate-400 font-mono">{{ previewingFile?.path }}</p>
              </div>
            </div>
            <button
              type="button"
              class="p-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors"
              @click="closePreview"
              title="关闭预览"
            >
              <X :size="20" class="text-slate-300" />
            </button>
          </div>

          <!-- 弹窗内容 -->
          <div class="flex-1 overflow-auto p-4">
            <div v-if="previewError" class="flex items-center gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
              <AlertCircle :size="20" />
              <p>{{ previewError }}</p>
            </div>

            <div v-else-if="!previewContent" class="flex items-center justify-center h-64">
              <div class="flex items-center gap-3 text-slate-400">
                <Loader2 :size="24" class="animate-spin" />
                <p>正在加载文件预览...</p>
              </div>
            </div>

            <div v-else-if="previewContent.type === 'text'" class="w-full">
              <div class="mb-3 flex items-center gap-2">
                <span class="text-xs text-slate-400 font-mono uppercase">文本文件预览</span>
                <span v-if="previewContent.truncated" class="text-xs text-amber-400 font-mono">（已截断，仅显示前 {{ formatBytes(10240) }}）</span>
              </div>
              <pre class="p-4 rounded-lg bg-slate-950/70 border border-white/10 text-sm text-slate-200 whitespace-pre-wrap overflow-auto max-h-[60vh]">
{{ previewContent.content || '文件内容为空' }}
              </pre>
            </div>

            <div v-else-if="previewContent.type === 'image'" class="w-full flex flex-col items-center justify-center">
              <div class="mb-3 text-xs text-slate-400 font-mono uppercase">图片文件预览</div>
              
              <!-- 检查 content 是否为有效的 base64 数据（非错误消息） -->
              <template v-if="previewContent.content && !previewContent.content.startsWith('[') && !previewContent.content.endsWith(']')">
                <img
                  :src="`data:image/${previewContent.extension.replace('.', '')};base64,${previewContent.content}`"
                  :alt="previewingFile?.name"
                  class="max-w-full max-h-[60vh] object-contain rounded-lg border border-white/10"
                  @error="(e) => { previewError = '图片预览失败，请检查文件格式'; }"
                />
              </template>
              
              <!-- 显示错误消息或空状态 -->
              <div v-else class="p-4 rounded-lg bg-slate-950/70 border border-white/10 text-slate-200">
                <p>{{ previewContent.content || '无法预览此图片' }}</p>
              </div>
            </div>

            <div v-else-if="previewContent.type === 'pdf'" class="w-full">
              <div class="mb-3 text-xs text-slate-400 font-mono uppercase">PDF文件预览</div>
              <div class="p-4 rounded-lg bg-slate-950/70 border border-white/10 text-slate-200">
                <p>{{ previewContent.content }}</p>
              </div>
            </div>

            <div v-else class="w-full">
              <div class="mb-3 text-xs text-slate-400 font-mono uppercase">文件类型：{{ previewContent.type }}</div>
              <div class="p-4 rounded-lg bg-slate-950/70 border border-white/10 text-slate-200">
                <p>{{ previewContent.content }}</p>
              </div>
            </div>
          </div>

          <!-- 弹窗底部 -->
          <div class="p-4 border-t border-white/10 flex items-center justify-between">
            <div class="flex items-center gap-4 text-xs text-slate-400 font-mono">
              <span>大小：{{ previewingFile ? formatBytes(previewingFile.size) : '—' }}</span>
              <span>类型：{{ previewingFile?.category || 'unknown' }}</span>
              <span>扩展名：{{ previewingFile?.extension || 'unknown' }}</span>
            </div>
            <button
              type="button"
              class="px-4 py-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-slate-200 text-sm"
              @click="closePreview"
            >
              关闭
            </button>
          </div>
        </div>
      </div>

      <!-- 操作历史记录弹窗 -->
      <div v-if="isShowingHistory" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
        <div class="relative w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-lg glass-strong border border-white/10 flex flex-col">
          <!-- 弹窗头部 -->
          <div class="flex items-center justify-between p-4 border-b border-white/10">
            <div class="flex items-center gap-3">
              <Sparkles :size="24" class="text-sky-300" />
              <div>
                <p class="font-medium text-slate-100">
                  {{ selectedHistory ? '历史记录详情' : '操作历史记录' }}
                </p>
                <p v-if="!selectedHistory" class="text-xs text-slate-400 font-mono">
                  共 {{ historyList.length }} 条记录
                </p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <button
                v-if="selectedHistory"
                type="button"
                class="px-3 py-1.5 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-slate-200 text-xs"
                @click="closeHistoryDetail"
              >
                返回列表
              </button>
              <button
                type="button"
                class="p-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors"
                @click="hideHistory"
                title="关闭"
              >
                <X :size="20" class="text-slate-300" />
              </button>
            </div>
          </div>

          <!-- 弹窗内容 -->
          <div class="flex-1 overflow-auto p-4">
            <div v-if="historyError" class="flex items-center gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
              <AlertCircle :size="20" />
              <p>{{ historyError }}</p>
            </div>

            <div v-else-if="isLoadingHistory" class="flex items-center justify-center h-64">
              <div class="flex items-center gap-3 text-slate-400">
                <Loader2 :size="24" class="animate-spin" />
                <p>正在加载历史记录...</p>
              </div>
            </div>

            <!-- 历史记录详情视图 -->
            <div v-else-if="selectedHistory" class="w-full space-y-4">
              <div class="p-4 rounded-lg bg-slate-950/70 border border-white/10 space-y-3">
                <div class="flex items-center gap-2">
                  <span :class="[
                    'px-2 py-0.5 rounded-lg border text-xs font-semibold',
                    selectedHistory.type === 'execute' 
                      ? 'text-emerald-300 bg-emerald-500/10 border-emerald-400/20'
                      : selectedHistory.type === 'deduplicate'
                        ? 'text-amber-300 bg-amber-500/10 border-amber-400/20'
                        : selectedHistory.type === 'rename'
                          ? 'text-sky-300 bg-sky-500/10 border-sky-400/20'
                          : 'text-sky-300 bg-sky-500/10 border-sky-400/20'
                  ]">
                    {{ selectedHistory.type === 'execute' ? '执行计划' : selectedHistory.type === 'deduplicate' ? '去重操作' : selectedHistory.type === 'rename' ? '重命名操作' : '回滚操作' }}
                  </span>
                  <span class="text-xs text-slate-400 font-mono">
                    {{ formatDateTime(selectedHistory.created_at) }}
                  </span>
                </div>
                <p class="text-xs text-slate-400 font-mono">
                  目标目录：{{ selectedHistory.target_path }}
                </p>
                <p class="text-xs text-slate-400 font-mono">
                  历史记录ID：{{ selectedHistory.id }}
                </p>
              </div>

              <div v-if="selectedHistory.results && selectedHistory.results.length > 0">
                <p class="text-sm text-slate-400 font-semibold mb-2">操作结果（共 {{ selectedHistory.results.length }} 条）</p>
                <div class="space-y-2 max-h-[40vh] overflow-auto">
                  <div
                    v-for="(result, index) in selectedHistory.results"
                    :key="`${result.file}-${index}`"
                    class="p-3 rounded-lg bg-slate-950/50 border border-white/5 space-y-1"
                  >
                    <div class="flex items-center gap-2">
                      <p class="text-sm text-slate-200 font-medium truncate">{{ result.file }}</p>
                      <span :class="[
                        'px-2 py-0.5 rounded-lg border text-xs',
                        actionTone[result.action] || actionTone.keep
                      ]">
                        {{ actionLabel[result.action] || result.action }}
                      </span>
                    </div>
                    <p v-if="result.new_path" class="text-xs text-slate-400 font-mono">
                      {{ result.original_path }} → {{ result.new_path }}
                    </p>
                    <p class="text-xs text-slate-400 font-mono">
                      状态：{{ result.status }}
                    </p>
                  </div>
                </div>
              </div>

              <div v-else class="p-4 rounded-lg bg-slate-950/50 border border-white/5 text-center text-slate-400">
                <p>暂无操作结果</p>
              </div>
            </div>

            <!-- 历史记录列表视图 -->
            <div v-else-if="historyList.length > 0" class="w-full space-y-3">
              <div
                v-for="(item, index) in historyList"
                :key="item.id"
                class="p-4 rounded-lg glass hover:bg-white/10 transition-colors cursor-pointer"
                @click="viewHistoryDetail(item)"
              >
                <div class="flex items-center justify-between mb-2">
                  <div class="flex items-center gap-2">
                    <span :class="[
                      'px-2 py-0.5 rounded-lg border text-xs font-semibold',
                      item.type === 'execute' 
                        ? 'text-emerald-300 bg-emerald-500/10 border-emerald-400/20'
                        : item.type === 'deduplicate'
                          ? 'text-amber-300 bg-amber-500/10 border-amber-400/20'
                          : item.type === 'rename'
                            ? 'text-sky-300 bg-sky-500/10 border-sky-400/20'
                            : 'text-sky-300 bg-sky-500/10 border-sky-400/20'
                    ]">
                      {{ item.type === 'execute' ? '执行计划' : item.type === 'deduplicate' ? '去重操作' : item.type === 'rename' ? '重命名操作' : '回滚操作' }}
                    </span>
                    <span class="text-xs text-slate-400 font-mono">
                      {{ formatDateTime(item.created_at) }}
                    </span>
                  </div>
                  <span class="text-xs text-slate-400 font-mono">
                    {{ item.results_count }} 条操作
                  </span>
                </div>
                <p class="text-xs text-slate-400 font-mono truncate">
                  目标目录：{{ item.target_path }}
                </p>
              </div>
            </div>

            <!-- 无历史记录视图 -->
            <div v-else class="flex flex-col items-center justify-center h-64 text-slate-400">
              <Sparkles :size="48" class="mb-3 text-slate-600" />
              <p class="text-lg font-medium">暂无操作历史记录</p>
              <p class="text-sm mt-1">执行文件整理计划后，历史记录将显示在这里</p>
            </div>
          </div>

          <!-- 弹窗底部 -->
          <div class="p-4 border-t border-white/10 flex items-center justify-end">
            <button
              type="button"
              class="px-4 py-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-slate-200 text-sm"
              @click="hideHistory"
            >
              关闭
            </button>
          </div>
        </div>
      </div>

      <!-- 规则模板系统弹窗 -->
      <div v-if="isShowingTemplates" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
        <div class="relative w-full max-w-6xl max-h-[90vh] overflow-hidden rounded-lg glass-strong border border-white/10 flex flex-col">
          <!-- 弹窗头部 -->
          <div class="flex items-center justify-between p-4 border-b border-white/10">
            <div class="flex items-center gap-3">
              <Sparkles :size="24" class="text-fuchsia-400" />
              <div>
                <p class="font-medium text-slate-100">
                  {{ isEditingTemplate ? '编辑模板' : '规则模板库' }}
                </p>
                <p class="text-xs text-slate-400 font-mono">
                  <template v-if="isEditingTemplate">
                    {{ editingTemplate?.name || '新建模板' }} · {{ editingTemplate?.rules?.length || 0 }} 条规则
                  </template>
                  <template v-else>
                    共 {{ templates.length }} 个模板 · {{ templates.filter(t => t.is_builtin).length }} 个内置
                  </template>
                </p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <button
                v-if="!isEditingTemplate"
                type="button"
                class="px-3 py-1.5 rounded-lg border border-fuchsia-400/30 bg-fuchsia-500/10 hover:bg-fuchsia-500/20 transition-colors text-fuchsia-100 text-xs"
                :disabled="isLoadingTemplates"
                @click="createNewTemplate"
              >
                新建模板
              </button>
              <button
                v-if="isEditingTemplate"
                type="button"
                class="px-3 py-1.5 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-slate-200 text-xs"
                @click="cancelEditTemplate"
              >
                取消
              </button>
              <button
                v-if="isEditingTemplate"
                type="button"
                class="px-3 py-1.5 rounded-lg border border-fuchsia-400/30 bg-fuchsia-500/10 hover:bg-fuchsia-500/20 transition-colors text-fuchsia-100 text-xs"
                :disabled="!editingTemplate?.name"
                @click="saveTemplate"
              >
                保存模板
              </button>
              <button
                type="button"
                class="p-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors"
                @click="hideTemplates"
                title="关闭"
              >
                <X :size="20" class="text-slate-300" />
              </button>
            </div>
          </div>

          <!-- 弹窗内容 -->
          <div v-if="!isEditingTemplate" class="flex-1 overflow-auto p-4">
            <!-- 加载中 -->
            <div v-if="isLoadingTemplates" class="flex items-center justify-center h-64">
              <div class="flex items-center gap-3 text-slate-400">
                <Loader2 :size="24" class="animate-spin" />
                <p>正在加载模板列表...</p>
              </div>
            </div>

            <!-- 错误显示 -->
            <div v-else-if="templateError" class="flex items-center gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
              <AlertCircle :size="20" />
              <p>{{ templateError }}</p>
            </div>

            <!-- 空状态 -->
            <div v-else-if="templates.length === 0" class="flex flex-col items-center justify-center h-64 text-slate-400">
              <Sparkles :size="48" class="mb-3 text-slate-600" />
              <p class="text-lg font-medium">暂无模板</p>
              <p class="text-sm mt-1">点击"新建模板"创建您的第一个整理规则</p>
            </div>

            <!-- 模板列表 -->
            <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div
                v-for="template in templates"
                :key="template.id"
                class="p-4 rounded-lg bg-slate-950/70 border border-white/10 hover:border-fuchsia-400/30 transition-all cursor-pointer"
              >
                <!-- 模板头部 -->
                <div class="flex items-start justify-between mb-3">
                  <div class="flex items-center gap-2">
                    <span class="text-2xl">{{ template.icon }}</span>
                    <div>
                      <p class="font-medium text-slate-200">{{ template.name }}</p>
                      <span
                        v-if="template.is_builtin"
                        class="inline-block px-1.5 py-0.5 rounded text-xs font-medium text-sky-300 bg-sky-500/10 border border-sky-400/20"
                      >
                        内置
                      </span>
                    </div>
                  </div>
                  <div class="flex items-center gap-1">
                    <button
                      type="button"
                      class="p-1.5 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors"
                      @click.stop="duplicateTemplate(template)"
                      title="复制模板"
                    >
                      <Copy :size="14" class="text-slate-400" />
                    </button>
                    <button
                      v-if="!template.is_builtin"
                      type="button"
                      class="p-1.5 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors"
                      @click.stop="editTemplate(template)"
                      title="编辑模板"
                    >
                      <Settings :size="14" class="text-slate-400" />
                    </button>
                    <button
                      v-if="!template.is_builtin"
                      type="button"
                      class="p-1.5 rounded-lg border border-red-400/20 bg-red-500/5 hover:bg-red-500/10 transition-colors"
                      @click.stop="deleteTemplate(template)"
                      title="删除模板"
                    >
                      <Trash2 :size="14" class="text-red-400" />
                    </button>
                  </div>
                </div>

                <!-- 模板描述 -->
                <p class="text-sm text-slate-400 mb-3 line-clamp-2">{{ template.description }}</p>

                <!-- 规则统计 -->
                <div class="flex items-center justify-between">
                  <span class="text-xs text-slate-500">
                    {{ template.rules_count || template.rules?.length || 0 }} 条规则
                  </span>
                  <button
                    type="button"
                    class="px-3 py-1 rounded-lg border border-fuchsia-400/30 bg-fuchsia-500/10 hover:bg-fuchsia-500/20 transition-colors text-fuchsia-100 text-xs"
                    :disabled="isApplyingTemplate || !targetPath"
                    @click.stop="applyTemplate(template)"
                  >
                    {{ isApplyingTemplate ? '应用中...' : '应用模板' }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- 模板编辑视图 -->
          <div v-else class="flex-1 overflow-hidden flex">
            <!-- 左侧：规则列表 -->
            <div class="w-1/3 border-r border-white/10 flex flex-col">
              <div class="p-3 border-b border-white/10 flex items-center justify-between">
                <span class="text-sm font-medium text-slate-200">规则列表</span>
                <button
                  type="button"
                  class="px-2 py-1 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-slate-200 text-xs"
                  @click="addNewRule"
                >
                  + 添加规则
                </button>
              </div>
              <div class="flex-1 overflow-auto p-2">
                <div
                  v-if="!editingTemplate?.rules?.length"
                  class="flex flex-col items-center justify-center h-32 text-slate-500 text-sm"
                >
                  <p>暂无规则</p>
                  <p class="text-xs">点击"添加规则"开始</p>
                </div>
                <div
                  v-else
                  v-for="(rule, index) in editingTemplate.rules"
                  :key="rule.rule_id"
                  class="p-2 rounded-lg mb-2 cursor-pointer transition-colors"
                  :class="[
                    editingRule === rule
                      ? 'bg-fuchsia-500/10 border border-fuchsia-400/30'
                      : 'bg-slate-900/50 border border-white/5 hover:bg-slate-800/50'
                  ]"
                  @click="editRule(rule)"
                >
                  <div class="flex items-center justify-between">
                    <span class="text-sm font-medium text-slate-200">{{ rule.name }}</span>
                    <button
                      type="button"
                      class="p-1 rounded hover:bg-red-500/10 text-red-400 opacity-60 hover:opacity-100"
                      @click.stop="deleteRule(rule)"
                    >
                      <X :size="12" />
                    </button>
                  </div>
                  <div class="text-xs text-slate-500 mt-1">
                    {{ rule.action === 'move' ? '移动' : rule.action === 'rename_and_move' ? '重命名并移动' : rule.action === 'delete' ? '删除' : '保留' }}
                    {{ rule.match_extensions?.length ? `· ${rule.match_extensions.join(', ')}` : '' }}
                  </div>
                </div>
              </div>
            </div>

            <!-- 右侧：规则编辑或模板基本信息 -->
            <div class="flex-1 flex flex-col overflow-auto">
              <!-- 当没有选中规则时，显示模板基本信息 -->
              <div v-if="!editingRule && editingTemplate" class="p-4 space-y-4">
                <h3 class="text-sm font-medium text-slate-200 border-b border-white/10 pb-2">模板基本信息</h3>
                
                <div class="space-y-2">
                  <label class="text-xs text-slate-400">模板名称</label>
                  <input
                    type="text"
                    v-model="editingTemplate.name"
                    class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-fuchsia-400 font-mono"
                    placeholder="输入模板名称"
                  >
                </div>

                <div class="space-y-2">
                  <label class="text-xs text-slate-400">图标 (emoji)</label>
                  <input
                    type="text"
                    v-model="editingTemplate.icon"
                    class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-fuchsia-400 font-mono"
                    placeholder="📁"
                  >
                </div>

                <div class="space-y-2">
                  <label class="text-xs text-slate-400">描述</label>
                  <textarea
                    v-model="editingTemplate.description"
                    rows="3"
                    class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-fuchsia-400 font-mono resize-none"
                    placeholder="描述这个模板的用途..."
                  />
                </div>
              </div>

              <!-- 当选中规则时，显示规则编辑 -->
              <div v-else-if="editingRule" class="p-4 space-y-4">
                <h3 class="text-sm font-medium text-slate-200 border-b border-white/10 pb-2">规则编辑</h3>
                
                <div class="space-y-2">
                  <label class="text-xs text-slate-400">规则名称</label>
                  <input
                    type="text"
                    v-model="editingRule.name"
                    class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-fuchsia-400 font-mono"
                    placeholder="例如：PDF文档"
                  >
                </div>

                <div class="space-y-2">
                  <label class="text-xs text-slate-400">匹配扩展名 (逗号分隔，如 .pdf,.doc)</label>
                  <input
                    type="text"
                    :value="editingRule.match_extensions?.join(',')"
                    @input="editingRule.match_extensions = $event.target.value.split(',').map(s => s.trim()).filter(s => s)"
                    class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-fuchsia-400 font-mono"
                    placeholder=".pdf,.doc,.docx"
                  >
                </div>

                <div class="space-y-2">
                  <label class="text-xs text-slate-400">匹配正则表达式 (可选，匹配文件名或路径)</label>
                  <input
                    type="text"
                    v-model="editingRule.match_pattern"
                    class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-fuchsia-400 font-mono"
                    placeholder="例如：screenshot|截图|error"
                  >
                </div>

                <div class="space-y-2">
                  <label class="text-xs text-slate-400">匹配分类 (可选)</label>
                  <select
                    v-model="editingRule.match_category"
                    class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-fuchsia-400 font-mono"
                  >
                    <option value="">不按分类匹配</option>
                    <option value="images">图片 (images)</option>
                    <option value="documents">文档 (documents)</option>
                    <option value="archives">压缩包 (archives)</option>
                    <option value="code">代码 (code)</option>
                    <option value="logs">日志 (logs)</option>
                    <option value="unknown">未知 (unknown)</option>
                  </select>
                </div>

                <div class="space-y-2">
                  <label class="text-xs text-slate-400">操作类型</label>
                  <select
                    v-model="editingRule.action"
                    class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-fuchsia-400 font-mono"
                  >
                    <option value="move">移动文件</option>
                    <option value="rename_and_move">重命名并移动</option>
                    <option value="delete">删除文件</option>
                    <option value="keep">保留 (不操作)</option>
                  </select>
                </div>

                <div v-if="editingRule.action !== 'delete' && editingRule.action !== 'keep'" class="space-y-2">
                  <label class="text-xs text-slate-400">
                    目标路径模板 (支持占位符: {name} 文件名, {date} 日期, {stem} 无扩展名文件名)
                  </label>
                  <input
                    type="text"
                    v-model="editingRule.target_path"
                    class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-fuchsia-400 font-mono"
                    placeholder="例如：documents/pdf/{name} 或 images/screenshots/{date}_{name}"
                  >
                </div>

                <div class="space-y-2">
                  <label class="text-xs text-slate-400">规则理由 (将显示在整理计划中)</label>
                  <textarea
                    v-model="editingRule.reason"
                    rows="2"
                    class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-fuchsia-400 font-mono resize-none"
                    placeholder="例如：PDF文档归档到pdf目录"
                  />
                </div>

                <div class="space-y-2">
                  <label class="text-xs text-slate-400">优先级 (数字越大优先级越高)</label>
                  <input
                    type="number"
                    v-model.number="editingRule.priority"
                    class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-fuchsia-400 font-mono"
                  >
                </div>
              </div>
            </div>
          </div>

          <!-- 弹窗底部 -->
          <div class="p-4 border-t border-white/10 flex items-center justify-between">
            <div class="text-xs text-slate-500 font-mono">
              <template v-if="isEditingTemplate">
                提示：内置模板不可编辑，但可以复制后修改
              </template>
              <template v-else>
                提示：选择一个模板并点击"应用模板"即可生成整理计划
              </template>
            </div>
            <button
              type="button"
              class="px-4 py-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-slate-200 text-sm"
              @click="hideTemplates"
            >
              关闭
            </button>
          </div>
        </div>
      </div>

      <!-- 智能批量重命名工具弹窗 -->
      <div v-if="isShowingRenamer" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
        <div class="relative w-full max-w-7xl max-h-[90vh] overflow-hidden rounded-lg glass-strong border border-white/10 flex flex-col">
          <!-- 弹窗头部 -->
          <div class="flex items-center justify-between p-4 border-b border-white/10">
            <div class="flex items-center gap-3">
              <Sparkles :size="24" class="text-sky-400" />
              <div>
                <p class="font-medium text-slate-100">智能批量重命名工具</p>
                <p class="text-xs text-slate-400 font-mono">
                  <template v-if="renamePreviews.length > 0">
                    已选择 {{ renameSelectedFiles.length }} 个文件 · {{ renamePreviews.filter(p => p.has_change).length }} 个将被重命名
                    <template v-if="renameHasConflicts">
                      <span class="text-red-400">· 检测到 {{ renameConflicts.length }} 个冲突</span>
                    </template>
                  </template>
                  <template v-else>
                    已选择 {{ renameSelectedFiles.length }} 个文件 · {{ renameRules.length }} 条规则
                  </template>
                </p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <button
                v-if="renamePreviews.length > 0 && !renameHasConflicts"
                type="button"
                class="px-3 py-1.5 rounded-lg border border-emerald-400/30 bg-emerald-500/10 hover:bg-emerald-500/20 transition-colors text-emerald-100 text-xs"
                :disabled="isExecutingRename"
                @click="executeRename"
              >
                执行重命名
              </button>
              <button
                v-if="renameRules.length > 0 && renameSelectedFiles.length > 0"
                type="button"
                class="px-3 py-1.5 rounded-lg border border-sky-400/30 bg-sky-500/10 hover:bg-sky-500/20 transition-colors text-sky-100 text-xs"
                :disabled="isLoadingRenamePreview"
                @click="generateRenamePreview"
              >
                生成预览
              </button>
              <button
                type="button"
                class="p-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors"
                @click="hideRenamer"
                title="关闭"
              >
                <X :size="20" class="text-slate-300" />
              </button>
            </div>
          </div>

          <!-- 弹窗内容区域 -->
          <div class="flex-1 overflow-hidden flex flex-col md:flex-row">
            <!-- 左侧：文件选择 -->
            <div class="w-full md:w-1/4 border-b md:border-b-0 md:border-r border-white/10 flex flex-col">
              <div class="p-3 border-b border-white/10 flex items-center justify-between">
                <span class="text-sm font-medium text-slate-200">选择文件</span>
                <div class="flex items-center gap-2">
                  <button
                    type="button"
                    class="px-2 py-1 rounded border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-slate-200 text-xs"
                    @click="selectAllRenameFiles"
                  >
                    全选
                  </button>
                  <button
                    type="button"
                    class="px-2 py-1 rounded border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-slate-200 text-xs"
                    @click="clearRenameSelection"
                  >
                    清空
                  </button>
                </div>
              </div>
              <div class="flex-1 overflow-auto p-2">
                <div v-if="!files || files.length === 0" class="flex flex-col items-center justify-center h-32 text-slate-500 text-sm">
                  <p>暂无文件</p>
                  <p class="text-xs mt-1">请先扫描目标目录</p>
                </div>
                <div v-else class="space-y-1">
                  <div
                    v-for="file in files"
                    :key="file.path"
                    class="flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors"
                    :class="[
                      renameSelectedFiles.includes(file.path)
                        ? 'bg-sky-500/10 border border-sky-400/30'
                        : 'bg-slate-900/50 border border-white/5 hover:bg-slate-800/50'
                    ]"
                    @click="toggleRenameFileSelection(file.path)"
                  >
                    <div class="flex items-center justify-center w-5 h-5 rounded border"
                      :class="[
                        renameSelectedFiles.includes(file.path)
                          ? 'border-sky-400 bg-sky-500/20'
                          : 'border-slate-600'
                      ]"
                    >
                      <CheckCircle
                        v-if="renameSelectedFiles.includes(file.path)"
                        :size="12"
                        class="text-sky-400"
                      />
                    </div>
                    <div class="p-1.5 rounded bg-slate-800 text-slate-400">
                      <FileText :size="16" />
                    </div>
                    <div class="flex-1 min-w-0">
                      <p class="text-sm text-slate-200 truncate">{{ file.name }}</p>
                      <p class="text-xs text-slate-500 font-mono truncate">
                        {{ file.extension || 'UNKNOWN' }} · {{ formatBytes(file.size) }}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 中间：规则配置 -->
            <div class="w-full md:w-1/3 border-b md:border-b-0 md:border-r border-white/10 flex flex-col">
              <div class="p-3 border-b border-white/10 flex items-center justify-between">
                <span class="text-sm font-medium text-slate-200">重命名规则</span>
                <div class="flex items-center gap-2">
                  <button
                    type="button"
                    class="px-2 py-1 rounded border border-sky-400/30 bg-sky-500/10 hover:bg-sky-500/20 transition-colors text-sky-200 text-xs"
                    @click="addRenameRule"
                  >
                    + 添加规则
                  </button>
                  <button
                    v-if="renameRules.length > 0"
                    type="button"
                    class="px-2 py-1 rounded border border-red-400/20 bg-red-500/5 hover:bg-red-500/10 transition-colors text-red-300 text-xs"
                    @click="clearRenameRules"
                  >
                    清空
                  </button>
                </div>
              </div>

              <!-- 规则类型选择 -->
              <div class="p-3 border-b border-white/10">
                <p class="text-xs text-slate-400 mb-2">选择规则类型</p>
                <div class="flex flex-wrap gap-1.5">
                  <button
                    v-for="ruleType in RENAME_RULE_TYPES"
                    :key="ruleType.value"
                    type="button"
                    class="px-2 py-1 rounded border text-xs transition-colors"
                    :class="[
                      activeRenameRuleType === ruleType.value
                        ? 'border-sky-400/30 bg-sky-500/10 text-sky-200'
                        : 'border-slate-400/20 bg-white/5 text-slate-300 hover:bg-white/10'
                    ]"
                    @click="activeRenameRuleType = ruleType.value"
                  >
                    {{ ruleType.icon }} {{ ruleType.label }}
                  </button>
                </div>
              </div>

              <!-- 已添加的规则列表 -->
              <div class="flex-1 overflow-auto p-3">
                <div v-if="renameRules.length === 0" class="flex flex-col items-center justify-center h-32 text-slate-500 text-sm">
                  <p>暂无规则</p>
                  <p class="text-xs mt-1">选择规则类型后点击"添加规则"</p>
                </div>
                <div v-else class="space-y-2">
                  <div
                    v-for="(rule, index) in renameRules"
                    :key="index"
                    class="p-3 rounded-lg bg-slate-950/70 border border-white/10 space-y-2"
                  >
                    <div class="flex items-center justify-between">
                      <span class="text-xs font-medium text-slate-200">
                        规则 {{ index + 1 }}: {{ getRenameRuleLabel(rule) }}
                      </span>
                      <button
                        type="button"
                        class="p-1 rounded hover:bg-red-500/10 text-red-400 opacity-60 hover:opacity-100"
                        @click="removeRenameRule(index)"
                      >
                        <X :size="14" />
                      </button>
                    </div>

                    <!-- 规则配置表单 -->
                    <div v-if="rule.rule_type === 'prefix'" class="space-y-2">
                      <label class="text-xs text-slate-400">前缀内容</label>
                      <input
                        type="text"
                        v-model="rule.prefix"
                        class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-400 font-mono"
                        placeholder="例如: IMG_ 或 2024_"
                      >
                    </div>

                    <div v-else-if="rule.rule_type === 'suffix'" class="space-y-2">
                      <label class="text-xs text-slate-400">后缀内容 (不含扩展名)</label>
                      <input
                        type="text"
                        v-model="rule.suffix"
                        class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-400 font-mono"
                        placeholder="例如: _backup 或 _processed"
                      >
                    </div>

                    <div v-else-if="rule.rule_type === 'find_replace'" class="space-y-2">
                      <label class="text-xs text-slate-400">查找文本</label>
                      <input
                        type="text"
                        v-model="rule.find_text"
                        class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-400 font-mono"
                        placeholder="要查找的文本"
                      >
                      <label class="text-xs text-slate-400">替换为</label>
                      <input
                        type="text"
                        v-model="rule.replace_text"
                        class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-400 font-mono"
                        placeholder="替换为的文本 (留空则删除)"
                      >
                    </div>

                    <div v-else-if="rule.rule_type === 'regex'" class="space-y-2">
                      <label class="text-xs text-slate-400">正则表达式</label>
                      <input
                        type="text"
                        v-model="rule.regex_pattern"
                        class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-400 font-mono"
                        placeholder="例如: (\d+) 或 (\w+)"
                      >
                      <label class="text-xs text-slate-400">替换模板</label>
                      <input
                        type="text"
                        v-model="rule.regex_replacement"
                        class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-400 font-mono"
                        placeholder="例如: img_$1"
                      >
                    </div>

                    <div v-else-if="rule.rule_type === 'numbering'" class="space-y-2">
                      <div class="grid grid-cols-2 gap-2">
                        <div>
                          <label class="text-xs text-slate-400">起始编号</label>
                          <input
                            type="number"
                            v-model.number="rule.start_number"
                            :min="0"
                            class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-400 font-mono"
                          >
                        </div>
                        <div>
                          <label class="text-xs text-slate-400">补零位数</label>
                          <input
                            type="number"
                            v-model.number="rule.number_padding"
                            :min="1"
                            :max="10"
                            class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-400 font-mono"
                          >
                        </div>
                      </div>
                      <div class="grid grid-cols-2 gap-2">
                        <div>
                          <label class="text-xs text-slate-400">分隔符</label>
                          <input
                            type="text"
                            v-model="rule.number_separator"
                            class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-400 font-mono"
                            placeholder="例如: _ 或 -"
                          >
                        </div>
                        <div>
                          <label class="text-xs text-slate-400">位置</label>
                          <select
                            v-model="rule.number_position"
                            class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-400 font-mono"
                          >
                            <option value="prefix">前缀</option>
                            <option value="suffix">后缀</option>
                            <option value="replace">替换</option>
                          </select>
                        </div>
                      </div>
                    </div>

                    <div v-else-if="rule.rule_type === 'date_prefix' || rule.rule_type === 'date_suffix'" class="space-y-2">
                      <label class="text-xs text-slate-400">日期分隔符</label>
                      <input
                        type="text"
                        v-model="rule.number_separator"
                        class="w-full rounded-lg border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-400 font-mono"
                        placeholder="例如: _ 或 -"
                      >
                      <p class="text-xs text-slate-500">
                        日期格式: YYYY-MM-DD (如 {{ new Date().toISOString().split('T')[0] }})
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 右侧：预览对比 -->
            <div class="w-full md:w-5/12 flex flex-col">
              <div class="p-3 border-b border-white/10">
                <span class="text-sm font-medium text-slate-200">预览对比</span>
              </div>
              <div class="flex-1 overflow-auto p-3">
                <!-- 错误显示 -->
                <div v-if="renameError" class="flex items-center gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 mb-3">
                  <AlertCircle :size="16" />
                  <p class="text-sm">{{ renameError }}</p>
                </div>

                <!-- 加载中 -->
                <div v-if="isLoadingRenamePreview" class="flex items-center justify-center h-32">
                  <div class="flex items-center gap-3 text-slate-400">
                    <Loader2 :size="20" class="animate-spin" />
                    <p class="text-sm">正在生成预览...</p>
                  </div>
                </div>

                <!-- 无预览状态 -->
                <div v-else-if="renamePreviews.length === 0" class="flex flex-col items-center justify-center h-32 text-slate-500 text-sm">
                  <Sparkles :size="32" class="mb-2 text-slate-600" />
                  <p>选择文件并添加规则后</p>
                  <p>点击"生成预览"查看重命名效果</p>
                </div>

                <!-- 预览列表 -->
                <div v-else class="space-y-2">
                  <div
                    v-for="preview in renamePreviews"
                    :key="preview.original_path"
                    class="p-3 rounded-lg bg-slate-950/70 border transition-colors"
                    :class="[
                      preview.conflict
                        ? 'border-red-500/30'
                        : preview.has_change
                          ? 'border-sky-400/30'
                          : 'border-white/10'
                    ]"
                  >
                    <div class="flex items-center gap-2 mb-1">
                      <div class="p-1.5 rounded bg-slate-800 text-slate-400">
                        <FileText :size="14" />
                      </div>
                      <div class="flex-1">
                        <div class="flex items-center gap-2">
                          <p class="text-sm text-slate-400 line-through">{{ preview.original_name }}</p>
                          <span v-if="preview.has_change" class="text-sky-400">→</span>
                          <p v-if="preview.has_change" class="text-sm text-sky-200 font-medium">{{ preview.new_name }}</p>
                        </div>
                        <p class="text-xs text-slate-500 font-mono truncate">{{ preview.original_path }}</p>
                      </div>
                      <div class="flex items-center gap-1">
                        <span
                          v-if="preview.conflict"
                          class="px-2 py-0.5 rounded text-xs font-medium text-red-300 bg-red-500/10 border border-red-400/20"
                        >
                          冲突
                        </span>
                        <span
                          v-else-if="preview.has_change"
                          class="px-2 py-0.5 rounded text-xs font-medium text-sky-300 bg-sky-500/10 border border-sky-400/20"
                        >
                          变更
                        </span>
                        <span
                          v-else
                          class="px-2 py-0.5 rounded text-xs font-medium text-slate-400 bg-slate-500/10 border border-slate-400/20"
                        >
                          无变化
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 弹窗底部 -->
          <div class="p-4 border-t border-white/10 flex items-center justify-between">
            <div class="text-xs text-slate-500 font-mono">
              <template v-if="renamePreviews.length > 0">
                <template v-if="renameHasConflicts">
                  <span class="text-red-400">警告：存在冲突，冲突的文件将不会被重命名</span>
                </template>
                <template v-else>
                  预览就绪，点击"执行重命名"开始操作 · 操作可通过"时光倒流"回滚
                </template>
              </template>
              <template v-else>
                提示：规则按顺序应用，先添加的规则先执行
              </template>
            </div>
            <button
              type="button"
              class="px-4 py-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-slate-200 text-sm"
              @click="hideRenamer"
            >
              关闭
            </button>
          </div>
        </div>
      </div>

      <!-- 数据可视化仪表盘弹窗 -->
      <div v-if="isShowingDashboard" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
        <div class="relative w-full max-w-6xl max-h-[90vh] overflow-hidden rounded-lg glass-strong border border-white/10 flex flex-col">
          <!-- 弹窗头部 -->
          <div class="flex items-center justify-between p-4 border-b border-white/10">
            <div class="flex items-center gap-3">
              <BarChart3 :size="24" class="text-amber-400" />
              <div>
                <p class="font-medium text-slate-100">数据可视化</p>
                <p class="text-xs text-slate-400 font-mono">
                  <template v-if="dashboardStats">
                    共 {{ dashboardStats.overview?.total_files || 0 }} 个文件 · 总大小 {{ formatBytes(dashboardStats.overview?.total_size || 0) }}
                  </template>
                  <template v-else-if="isLoadingDashboard">
                    正在生成数据报告...
                  </template>
                </p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <button
                type="button"
                class="px-3 py-1.5 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-slate-200 text-xs"
                :disabled="isLoadingDashboard"
                @click="loadDashboardStats"
              >
                刷新数据
              </button>
              <button
                type="button"
                class="p-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors"
                @click="hideDashboard"
                title="关闭"
              >
                <X :size="20" class="text-slate-300" />
              </button>
            </div>
          </div>

          <!-- 弹窗内容区域 -->
          <div class="flex-1 overflow-auto p-4">
            <!-- 加载中 -->
            <div v-if="isLoadingDashboard" class="flex items-center justify-center h-64">
              <div class="flex flex-col items-center gap-4 text-slate-400">
                <div class="flex items-center gap-3">
                  <Loader2 :size="24" class="animate-spin text-amber-400" />
                  <p class="text-sm">正在生成数据报告...</p>
                </div>
                <div class="w-64 h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div class="h-full bg-amber-500 rounded-full animate-pulse" style="width: 70%;" />
                </div>
              </div>
            </div>

            <!-- 错误显示 -->
            <div v-else-if="dashboardError" class="flex items-center gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
              <AlertCircle :size="20" />
              <p>{{ dashboardError }}</p>
            </div>

            <!-- 无数据状态 -->
            <div v-else-if="!dashboardStats" class="flex flex-col items-center justify-center h-64 text-slate-500">
              <BarChart3 :size="48" class="mb-3 text-slate-700" />
              <p class="text-lg">暂无数据</p>
              <p class="text-sm mt-1">选择目标目录后点击"刷新数据"生成报告</p>
            </div>

            <!-- 仪表盘内容 -->
            <div v-else class="space-y-6">
              <!-- 概览卡片行 -->
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="p-4 rounded-lg bg-slate-950/70 border border-white/10">
                  <div class="flex items-center justify-between">
                    <div>
                      <p class="text-xs text-slate-400">总文件数</p>
                      <p class="text-2xl font-bold text-slate-100">{{ dashboardStats.overview?.total_files || 0 }}</p>
                    </div>
                    <div class="p-2 rounded-lg bg-sky-500/10">
                      <FileText :size="20" class="text-sky-400" />
                    </div>
                  </div>
                </div>
                <div class="p-4 rounded-lg bg-slate-950/70 border border-white/10">
                  <div class="flex items-center justify-between">
                    <div>
                      <p class="text-xs text-slate-400">总大小</p>
                      <p class="text-2xl font-bold text-slate-100">{{ formatBytes(dashboardStats.overview?.total_size || 0) }}</p>
                    </div>
                    <div class="p-2 rounded-lg bg-emerald-500/10">
                      <HardDrive :size="20" class="text-emerald-400" />
                    </div>
                  </div>
                </div>
                <div class="p-4 rounded-lg bg-slate-950/70 border border-white/10">
                  <div class="flex items-center justify-between">
                    <div>
                      <p class="text-xs text-slate-400">文件类型</p>
                      <p class="text-2xl font-bold text-slate-100">
                        {{ Object.entries(dashboardStats.overview?.categories || {}).filter(([, c]) => (c.count || 0) > 0).length }}
                      </p>
                    </div>
                    <div class="p-2 rounded-lg bg-fuchsia-500/10">
                      <Star :size="20" class="text-fuchsia-400" />
                    </div>
                  </div>
                </div>
                <div class="p-4 rounded-lg bg-slate-950/70 border border-white/10">
                  <div class="flex items-center justify-between">
                    <div>
                      <p class="text-xs text-slate-400">历史操作</p>
                      <p class="text-2xl font-bold text-slate-100">
                        {{ dashboardStats.history_stats?.total_operations || 0 }}
                      </p>
                    </div>
                    <div class="p-2 rounded-lg bg-amber-500/10">
                      <Clock :size="20" class="text-amber-400" />
                    </div>
                  </div>
                </div>
              </div>

              <!-- 主要图表区域 -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <!-- 环形图：文件类型分布 -->
                <div class="p-4 rounded-lg bg-slate-950/70 border border-white/10">
                  <h3 class="text-sm font-medium text-slate-200 mb-4">文件类型分布</h3>
                  <div class="flex items-center gap-6">
                    <!-- SVG环形图 -->
                    <div class="w-40 h-40 flex-shrink-0">
                      <svg viewBox="0 0 100 100" class="w-full h-full transform -rotate-90">
                        <circle cx="50" cy="50" r="36" fill="none" stroke="#1e293b" stroke-width="16" />
                        <circle
                          v-for="(segment, index) in calculatePieChartPercentages()"
                          :key="segment.key"
                          :cx="50"
                          :cy="50"
                          :r="36"
                          fill="none"
                          :stroke="segment.color"
                          stroke-width="16"
                          :stroke-dasharray="`${(segment.angle / 360) * 226.195} 226.195`"
                          :stroke-dashoffset="-(segment.startAngle / 360) * 226.195"
                          class="transition-all duration-500"
                        />
                      </svg>
                    </div>
                    <!-- 图例 -->
                    <div class="flex-1 space-y-2">
                      <div
                        v-for="segment in calculatePieChartPercentages()"
                        :key="segment.key"
                        class="flex items-center justify-between text-sm"
                      >
                        <div class="flex items-center gap-2">
                          <div
                            class="w-3 h-3 rounded-full"
                            :style="{ backgroundColor: segment.color }"
                          />
                          <span class="text-slate-300">{{ segment.label }}</span>
                        </div>
                        <div class="flex items-center gap-2">
                          <span class="text-slate-400 font-mono text-xs">{{ segment.count }} 个</span>
                          <span
                            class="text-xs font-medium px-1.5 py-0.5 rounded"
                            :style="{ backgroundColor: segment.color + '20', color: segment.color }"
                          >
                            {{ segment.percentage }}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 条形图：大小分布 -->
                <div class="p-4 rounded-lg bg-slate-950/70 border border-white/10">
                  <h3 class="text-sm font-medium text-slate-200 mb-4">文件大小分布</h3>
                  <div class="space-y-3">
                    <div
                      v-for="bucket in getSizeDistributionData()"
                      :key="bucket.key"
                      class="space-y-1"
                    >
                      <div class="flex items-center justify-between text-xs">
                        <span class="text-slate-300">{{ bucket.label }}</span>
                        <span class="text-slate-400">{{ bucket.count }} 个 ({{ formatBytes(bucket.size) }})</span>
                      </div>
                      <div class="h-5 bg-slate-800/50 rounded-full overflow-hidden">
                        <div
                          class="h-full rounded-full transition-all duration-500"
                          :style="{
                            width: `${bucket.percentage}%`,
                            background: 'linear-gradient(90deg, #0ea5e9, #6366f1)'
                          }"
                        />
                      </div>
                    </div>
                    <div v-if="getSizeDistributionData().length === 0" class="text-center py-8 text-slate-500">
                      暂无数据
                    </div>
                  </div>
                </div>
              </div>

              <!-- 时间线和扩展统计 -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <!-- 周活动热力图 -->
                <div class="p-4 rounded-lg bg-slate-950/70 border border-white/10">
                  <h3 class="text-sm font-medium text-slate-200 mb-4">近7天文件修改分布</h3>
                  <div class="space-y-2">
                    <div class="flex items-center gap-2 text-xs text-slate-500 mb-2">
                      <span class="w-16">日期</span>
                      <span class="flex-1">文件活动强度</span>
                      <span class="w-12 text-right">数量</span>
                    </div>
                    <div
                      v-for="day in getWeeklyActivityData()"
                      :key="day.date"
                      class="flex items-center gap-2"
                    >
                      <span class="w-16 text-xs text-slate-400 font-mono">
                        {{ day.date.split('-').slice(1).join('/') }}
                      </span>
                      <div class="flex-1 h-6 bg-slate-800/30 rounded overflow-hidden">
                        <div
                          class="h-full transition-all duration-500"
                          :style="{
                            width: `${Math.min(100, (day.count || 0) * 10)}%`,
                            background: day.count > 0
                              ? 'linear-gradient(90deg, #22c55e, #84cc16)'
                              : 'transparent'
                          }"
                        />
                      </div>
                      <span class="w-12 text-right text-xs text-slate-400 font-mono">
                        {{ day.count || 0 }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- 扩展名Top10和历史统计 -->
                <div class="space-y-4">
                  <!-- 扩展名Top10 -->
                  <div class="p-4 rounded-lg bg-slate-950/70 border border-white/10">
                    <h3 class="text-sm font-medium text-slate-200 mb-3">热门扩展名 TOP 10</h3>
                    <div class="flex flex-wrap gap-2">
                      <template v-if="dashboardStats.extension_distribution">
                        <span
                          v-for="(data, ext) in dashboardStats.extension_distribution"
                          :key="ext"
                          class="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-mono"
                          :class="[
                            'border',
                            ext.toLowerCase().includes('jpg') || ext.toLowerCase().includes('png') || ext.toLowerCase().includes('gif') || ext.toLowerCase().includes('webp')
                              ? 'bg-emerald-500/10 text-emerald-300 border-emerald-400/20'
                              : ext.toLowerCase().includes('doc') || ext.toLowerCase().includes('pdf') || ext.toLowerCase().includes('xls') || ext.toLowerCase().includes('ppt')
                                ? 'bg-sky-500/10 text-sky-300 border-sky-400/20'
                                : ext.toLowerCase().includes('zip') || ext.toLowerCase().includes('rar') || ext.toLowerCase().includes('7z')
                                  ? 'bg-fuchsia-500/10 text-fuchsia-300 border-fuchsia-400/20'
                                  : 'bg-slate-500/10 text-slate-300 border-slate-400/20'
                          ]"
                        >
                          {{ ext }}
                          <span class="text-slate-400">·{{ data.count }}</span>
                        </span>
                      </template>
                      <span v-else class="text-slate-500 text-sm">暂无数据</span>
                    </div>
                  </div>

                  <!-- 历史操作统计 -->
                  <div v-if="dashboardStats.history_stats" class="p-4 rounded-lg bg-slate-950/70 border border-white/10">
                    <h3 class="text-sm font-medium text-slate-200 mb-3">操作历史统计</h3>
                    <div class="space-y-2">
                      <div class="flex items-center justify-between text-sm">
                        <span class="text-slate-400">总操作次数</span>
                        <span class="text-slate-200 font-medium">{{ dashboardStats.history_stats.total_operations }}</span>
                      </div>
                      <div class="flex items-center justify-between text-sm">
                        <span class="text-slate-400">近7天操作</span>
                        <span class="text-emerald-400 font-medium">{{ dashboardStats.history_stats.last_7_days }}</span>
                      </div>
                      <div class="mt-3 pt-3 border-t border-white/5">
                        <div class="text-xs text-slate-500 mb-2">操作类型分布</div>
                        <div class="flex flex-wrap gap-2">
                          <span
                            v-for="(count, type) in dashboardStats.history_stats.by_type"
                            :key="type"
                            class="inline-flex items-center gap-1 px-2 py-1 rounded text-xs"
                            :class="[
                              type === 'execute' ? 'bg-emerald-500/10 text-emerald-300' :
                              type === 'undo' ? 'bg-sky-500/10 text-sky-300' :
                              type === 'deduplicate' ? 'bg-amber-500/10 text-amber-300' :
                              type === 'rename' ? 'bg-fuchsia-500/10 text-fuchsia-300' :
                              'bg-slate-500/10 text-slate-300'
                            ]"
                          >
                            {{ getHistoryTypeLabels(type) }}: {{ count }}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 计划预览和二次确认弹窗 -->
      <div v-if="isShowingPlanPreview && planPreviewData" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
        <div class="relative w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-lg glass-strong border border-white/10 flex flex-col">
          <!-- 弹窗头部 -->
          <div class="flex items-center justify-between p-4 border-b border-white/10">
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-lg" :class="planPreviewData.safety_level === 'danger' ? 'bg-red-500/10' : planPreviewData.safety_level === 'warning' ? 'bg-amber-500/10' : 'bg-emerald-500/10'">
                <Shield :size="24" :class="planPreviewData.safety_level === 'danger' ? 'text-red-400' : planPreviewData.safety_level === 'warning' ? 'text-amber-400' : 'text-emerald-400'" />
              </div>
              <div>
                <p class="font-medium text-slate-100">执行计划预览</p>
                <p class="text-xs text-slate-400 font-mono">
                  共 {{ planPreviewData.summary?.total_actions || 0 }} 条操作 · 
                  <span :class="getSafetyLevelClass(planPreviewData.safety_level)" class="inline-flex px-2 py-0.5 rounded border text-xs ml-1">
                    {{ getSafetyLevelLabel(planPreviewData.safety_level) }}
                  </span>
                </p>
              </div>
            </div>
            <button
              type="button"
              class="p-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors"
              @click="cancelPlanPreview"
              title="取消"
            >
              <X :size="20" class="text-slate-300" />
            </button>
          </div>

          <!-- 弹窗内容 -->
          <div class="flex-1 overflow-auto p-4">
            <!-- 安全警告区域 -->
            <div v-if="planPreviewData.safety_reasons && planPreviewData.safety_reasons.length > 0"
              class="mb-4 p-4 rounded-lg border"
              :class="planPreviewData.safety_level === 'danger' ? 'bg-red-500/10 border-red-400/20' : 'bg-amber-500/10 border-amber-400/20'"
            >
              <div class="flex items-start gap-3">
                <AlertTriangle :size="18" :class="planPreviewData.safety_level === 'danger' ? 'text-red-400' : 'text-amber-400'" />
                <div>
                  <p class="text-sm font-medium" :class="planPreviewData.safety_level === 'danger' ? 'text-red-300' : 'text-amber-300'">
                    安全提示
                  </p>
                  <ul class="mt-2 space-y-1">
                    <li v-for="(reason, index) in planPreviewData.safety_reasons" :key="index" class="text-xs" :class="planPreviewData.safety_level === 'danger' ? 'text-red-200' : 'text-amber-200'">
                      ⚠️ {{ reason }}
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            <!-- 操作摘要 -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <div class="p-3 rounded-lg bg-slate-950/70 border border-white/10">
                <p class="text-xs text-slate-400">移动/重命名</p>
                <p class="text-xl font-bold text-sky-400">{{ planPreviewData.summary?.move_count || 0 }}</p>
              </div>
              <div class="p-3 rounded-lg bg-slate-950/70 border border-white/10">
                <p class="text-xs text-slate-400">删除</p>
                <p class="text-xl font-bold text-red-400">{{ planPreviewData.summary?.delete_count || 0 }}</p>
              </div>
              <div class="p-3 rounded-lg bg-slate-950/70 border border-white/10">
                <p class="text-xs text-slate-400">保留</p>
                <p class="text-xl font-bold text-slate-300">{{ planPreviewData.summary?.keep_count || 0 }}</p>
              </div>
              <div class="p-3 rounded-lg bg-slate-950/70 border border-white/10">
                <p class="text-xs text-slate-400">新建文件夹</p>
                <p class="text-xl font-bold text-emerald-400">{{ planPreviewData.summary?.new_folders_count || 0 }}</p>
              </div>
            </div>

            <!-- 冲突列表 -->
            <div v-if="planPreviewData.conflicts && planPreviewData.conflicts.length > 0" class="mb-4">
              <h4 class="text-sm font-medium text-red-400 mb-2 flex items-center gap-2">
                <AlertTriangle :size="16" />
                检测到 {{ planPreviewData.conflicts.length }} 个冲突
              </h4>
              <div class="space-y-2 max-h-32 overflow-auto">
                <div v-for="(conflict, index) in planPreviewData.conflicts" :key="index" class="p-3 rounded-lg bg-red-500/5 border border-red-400/20">
                  <p class="text-xs text-slate-200">
                    <span class="text-red-400 font-medium">{{ conflict.type === 'target_exists' ? '目标文件已存在:' : '目标冲突:' }}</span>
                  </p>
                  <p class="text-xs text-slate-400 font-mono mt-1">
                    {{ conflict.source }} → {{ conflict.target }}
                    <span v-if="conflict.other_source" class="text-red-400 ml-2">
                      (同时被 {{ conflict.other_source }} 占用)
                    </span>
                  </p>
                </div>
              </div>
            </div>

            <!-- 警告列表 -->
            <div v-if="planPreviewData.warnings && planPreviewData.warnings.length > 0" class="mb-4">
              <h4 class="text-sm font-medium text-amber-400 mb-2 flex items-center gap-2">
                <AlertCircle :size="16" />
                警告 ({{ planPreviewData.warnings.length }})
              </h4>
              <div class="space-y-2 max-h-24 overflow-auto">
                <div v-for="(warning, index) in planPreviewData.warnings" :key="index" class="p-2 rounded-lg bg-amber-500/5 border border-amber-400/20">
                  <p class="text-xs text-slate-200">
                    <span class="text-slate-400">{{ warning.file }}:</span>
                    <span class="text-amber-400 ml-1">{{ warning.message }}</span>
                  </p>
                </div>
              </div>
            </div>

            <!-- 操作详细列表 -->
            <div class="space-y-4">
              <!-- 移动操作列表 -->
              <div v-if="planPreviewData.move_actions && planPreviewData.move_actions.length > 0">
                <h4 class="text-sm font-medium text-slate-200 mb-2 flex items-center gap-2">
                  <ArrowRight :size="16" class="text-sky-400" />
                  移动/重命名操作 ({{ planPreviewData.move_actions.length }})
                </h4>
                <div class="space-y-1 max-h-40 overflow-auto">
                  <div
                    v-for="(action, index) in planPreviewData.move_actions"
                    :key="index"
                    class="flex items-center justify-between p-2 rounded-lg bg-slate-950/50 border border-white/5"
                  >
                    <div class="flex items-center gap-2 min-w-0 flex-1">
                      <FileText :size="14" class="text-slate-400 flex-shrink-0" />
                      <div class="min-w-0">
                        <p class="text-xs text-slate-200 truncate">{{ action.source_name }}</p>
                        <p class="text-xs text-sky-400 truncate flex items-center gap-1">
                          <ArrowRight :size="10" />
                          {{ action.target_name }}
                        </p>
                      </div>
                    </div>
                    <div v-if="!action.source_exists" class="flex-shrink-0 ml-2">
                      <span class="px-1.5 py-0.5 rounded text-xs bg-amber-500/10 text-amber-400 border border-amber-400/20">
                        不存在
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 删除操作列表 -->
              <div v-if="planPreviewData.delete_actions && planPreviewData.delete_actions.length > 0">
                <h4 class="text-sm font-medium text-slate-200 mb-2 flex items-center gap-2">
                  <Trash2 :size="16" class="text-red-400" />
                  删除操作 ({{ planPreviewData.delete_actions.length }})
                </h4>
                <div class="space-y-1 max-h-32 overflow-auto">
                  <div
                    v-for="(action, index) in planPreviewData.delete_actions"
                    :key="index"
                    class="flex items-center justify-between p-2 rounded-lg bg-red-500/5 border border-red-400/20"
                  >
                    <div class="flex items-center gap-2 min-w-0">
                      <FileText :size="14" class="text-red-400 flex-shrink-0" />
                      <p class="text-xs text-slate-200 truncate">{{ action.file_name }}</p>
                    </div>
                    <div v-if="!action.source_exists" class="flex-shrink-0 ml-2">
                      <span class="px-1.5 py-0.5 rounded text-xs bg-amber-500/10 text-amber-400 border border-amber-400/20">
                        不存在
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 保留操作列表 -->
              <div v-if="planPreviewData.keep_actions && planPreviewData.keep_actions.length > 0">
                <h4 class="text-sm font-medium text-slate-200 mb-2 flex items-center gap-2">
                  <Check :size="16" class="text-slate-400" />
                  保留操作 ({{ planPreviewData.keep_actions.length }})
                </h4>
                <div class="space-y-1 max-h-24 overflow-auto">
                  <div
                    v-for="(action, index) in planPreviewData.keep_actions"
                    :key="index"
                    class="flex items-center gap-2 p-2 rounded-lg bg-slate-950/50 border border-white/5"
                  >
                    <FileText :size="14" class="text-slate-400" />
                    <p class="text-xs text-slate-200 truncate">{{ action.file_name }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 弹窗底部 -->
          <div class="p-4 border-t border-white/10">
            <!-- 最终确认复选框 -->
            <div v-if="needFinalConfirmation" class="mb-4 p-3 rounded-lg bg-red-500/5 border border-red-400/20">
              <label class="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  v-model="finalConfirmChecked"
                  class="mt-0.5 w-4 h-4 rounded border-slate-500 bg-slate-800 text-red-500 focus:ring-red-500"
                />
                <div>
                  <p class="text-sm text-red-300 font-medium">我已知晓操作风险</p>
                  <p class="text-xs text-slate-400 mt-1">
                    我理解此操作将修改/删除文件，虽然可以通过"时光倒流"回滚，但仍需谨慎操作。
                  </p>
                </div>
              </label>
            </div>

            <div class="flex items-center justify-between">
              <div class="text-xs text-slate-500 font-mono">
                <template v-if="planPreviewData.has_conflicts">
                  <span class="text-red-400">⚠️ 存在冲突，建议先解决冲突再执行</span>
                </template>
                <template v-else-if="planPreviewData.has_warnings">
                  <span class="text-amber-400">⚠️ 存在警告，部分源文件可能不存在</span>
                </template>
                <template v-else>
                  ✓ 计划检查通过，可以安全执行
                </template>
              </div>
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  class="px-4 py-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-slate-200 text-sm"
                  @click="cancelPlanPreview"
                >
                  取消
                </button>
                <button
                  type="button"
                  class="px-4 py-2 rounded-lg border transition-colors text-sm"
                  :class="[
                    needFinalConfirmation && !finalConfirmChecked
                      ? 'border-slate-400/20 bg-slate-500/20 text-slate-500 cursor-not-allowed'
                      : planPreviewData.has_conflicts
                        ? 'border-red-400/30 bg-red-500/10 hover:bg-red-500/20 text-red-100'
                        : 'border-emerald-400/30 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-100'
                  ]"
                  :disabled="needFinalConfirmation && !finalConfirmChecked"
                  @click="executePlanDirectly"
                >
                  {{ planPreviewData.has_conflicts ? '强制执行' : '确认执行' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 多目录批量处理弹窗 -->
      <div v-if="isShowingMultiTargets" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
        <div class="relative w-full max-w-5xl max-h-[90vh] overflow-hidden rounded-lg glass-strong border border-white/10 flex flex-col">
          <!-- 弹窗头部 -->
          <div class="flex items-center justify-between p-4 border-b border-white/10">
            <div class="flex items-center gap-3">
              <HardDrive :size="24" class="text-emerald-400" />
              <div>
                <p class="font-medium text-slate-100">多目录批量处理</p>
                <p class="text-xs text-slate-400 font-mono">
                  <template v-if="multiTargets.length > 0">
                    已选择 {{ multiTargets.length }} 个目录
                    <template v-if="multiScanResults.success_count">
                      · 共 {{ multiScanResults.total_files }} 个文件
                    </template>
                    <template v-else-if="multiPlanResults.success_count">
                      · 共 {{ multiPlanResults.total_actions }} 条行动
                    </template>
                  </template>
                  <template v-else>
                    请添加要批量处理的目录
                  </template>
                </p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <button
                v-if="multiTargets.length > 0 && !isMultiMode"
                type="button"
                class="px-3 py-1.5 rounded-lg border border-emerald-400/30 bg-emerald-500/10 hover:bg-emerald-500/20 transition-colors text-emerald-100 text-xs"
                :disabled="isMultiScanning"
                @click="performMultiScan"
              >
                仅扫描
              </button>
              <button
                v-if="multiTargets.length > 0"
                type="button"
                class="px-3 py-1.5 rounded-lg border border-fuchsia-400/30 bg-fuchsia-500/10 hover:bg-fuchsia-500/20 transition-colors text-fuchsia-100 text-xs"
                :disabled="isMultiScanning || isMultiGeneratingPlan"
                @click="performMultiGeneratePlan"
              >
                {{ isMultiGeneratingPlan ? '生成中...' : '生成AI计划' }}
              </button>
              <button
                type="button"
                class="p-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors"
                @click="hideMultiTargets"
                title="关闭"
              >
                <X :size="20" class="text-slate-300" />
              </button>
            </div>
          </div>

          <!-- 弹窗内容 -->
          <div class="flex-1 overflow-auto p-4">
            <!-- 错误显示 -->
            <div v-if="multiError" class="flex items-center gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 mb-4">
              <AlertCircle :size="20" />
              <p>{{ multiError }}</p>
            </div>

            <!-- 加载中 -->
            <div v-if="isMultiScanning || isMultiGeneratingPlan" class="flex items-center justify-center h-48">
              <div class="flex flex-col items-center gap-4 text-slate-400">
                <div class="flex items-center gap-3">
                  <Loader2 :size="24" class="animate-spin text-emerald-400" />
                  <p class="text-sm">
                    {{ isMultiScanning ? '正在扫描多目录...' : '正在为多目录生成AI计划...' }}
                  </p>
                </div>
                <div class="w-64 h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div class="h-full bg-emerald-500 rounded-full animate-pulse" style="width: 60%;" />
                </div>
              </div>
            </div>

            <!-- 扫描结果展示 -->
            <div v-else-if="isMultiMode && multiScanResults.merged_analysis" class="space-y-4">
              <div class="p-4 rounded-lg bg-slate-950/70 border border-emerald-400/20">
                <h3 class="text-sm font-medium text-emerald-300 mb-3 flex items-center gap-2">
                  <CheckCircle :size="16" />
                  多目录扫描完成
                </h3>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div class="p-3 rounded-lg bg-slate-900/50 border border-white/5">
                    <p class="text-xs text-slate-400">目录总数</p>
                    <p class="text-xl font-bold text-slate-100">{{ multiScanResults.success_count }}</p>
                  </div>
                  <div class="p-3 rounded-lg bg-slate-900/50 border border-white/5">
                    <p class="text-xs text-slate-400">文件总数</p>
                    <p class="text-xl font-bold text-slate-100">{{ multiScanResults.total_files }}</p>
                  </div>
                  <div class="p-3 rounded-lg bg-slate-900/50 border border-white/5">
                    <p class="text-xs text-slate-400">总大小</p>
                    <p class="text-xl font-bold text-slate-100">{{ formatBytes(multiScanResults.total_size) }}</p>
                  </div>
                  <div class="p-3 rounded-lg bg-slate-900/50 border border-white/5">
                    <p class="text-xs text-slate-400">失败目录</p>
                    <p class="text-xl font-bold" :class="multiScanResults.failed_count > 0 ? 'text-red-400' : 'text-slate-100'">
                      {{ multiScanResults.failed_count }}
                    </p>
                  </div>
                </div>
              </div>

              <!-- 各目录详情 -->
              <div class="space-y-2">
                <h4 class="text-sm text-slate-400">各目录详情</h4>
                <div
                  v-for="(result, index) in multiScanResults.results"
                  :key="index"
                  class="p-3 rounded-lg border transition-colors"
                  :class="[
                    result.status === 'success'
                      ? 'bg-slate-950/70 border-emerald-400/20'
                      : 'bg-red-500/5 border-red-400/20'
                  ]"
                >
                  <div class="flex items-start justify-between">
                    <div class="flex items-start gap-2">
                      <div
                        class="p-1 rounded mt-0.5"
                        :class="result.status === 'success' ? 'bg-emerald-500/10' : 'bg-red-500/10'"
                      >
                        <CheckCircle
                          v-if="result.status === 'success'"
                          :size="14"
                          class="text-emerald-400"
                        />
                        <AlertCircle
                          v-else
                          :size="14"
                          class="text-red-400"
                        />
                      </div>
                      <div>
                        <p class="text-sm text-slate-200 font-mono break-all">{{ result.target_path }}</p>
                        <p v-if="result.status === 'success'" class="text-xs text-slate-500 mt-1">
                          {{ result.file_count }} 个文件 · {{ formatBytes(result.total_size) }}
                        </p>
                        <p v-else class="text-xs text-red-400 mt-1">
                          错误: {{ result.error }}
                        </p>
                      </div>
                    </div>
                    <span
                      class="inline-flex px-2 py-0.5 rounded text-xs font-medium"
                      :class="[
                        result.status === 'success'
                          ? 'text-emerald-300 bg-emerald-500/10 border border-emerald-400/20'
                          : 'text-red-300 bg-red-500/10 border border-red-400/20'
                      ]"
                    >
                      {{ result.status === 'success' ? '成功' : '失败' }}
                    </span>
                  </div>
                </div>
              </div>

              <div class="p-3 rounded-lg bg-emerald-500/5 border border-emerald-400/20">
                <p class="text-xs text-slate-400">
                  💡 提示：扫描完成后，文件已合并到主列表。可以继续使用现有的"规则模板"、"AI炼金计划"等功能，或点击"生成AI计划"为多目录生成统一的整理计划。
                </p>
              </div>
            </div>

            <!-- 计划生成结果展示 -->
            <div v-else-if="isMultiMode && multiPlanResults.merged_plan" class="space-y-4">
              <div class="p-4 rounded-lg bg-slate-950/70 border border-fuchsia-400/20">
                <h3 class="text-sm font-medium text-fuchsia-300 mb-3 flex items-center gap-2">
                  <Sparkles :size="16" />
                  多目录计划生成完成
                </h3>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div class="p-3 rounded-lg bg-slate-900/50 border border-white/5">
                    <p class="text-xs text-slate-400">成功目录</p>
                    <p class="text-xl font-bold text-slate-100">{{ multiPlanResults.success_count }}</p>
                  </div>
                  <div class="p-3 rounded-lg bg-slate-900/50 border border-white/5">
                    <p class="text-xs text-slate-400">LLM失败</p>
                    <p class="text-xl font-bold" :class="multiPlanResults.llm_failed_count > 0 ? 'text-amber-400' : 'text-slate-100'">
                      {{ multiPlanResults.llm_failed_count }}
                    </p>
                  </div>
                  <div class="p-3 rounded-lg bg-slate-900/50 border border-white/5">
                    <p class="text-xs text-slate-400">总文件数</p>
                    <p class="text-xl font-bold text-slate-100">{{ multiPlanResults.total_files }}</p>
                  </div>
                  <div class="p-3 rounded-lg bg-slate-900/50 border border-white/5">
                    <p class="text-xs text-slate-400">行动总数</p>
                    <p class="text-xl font-bold text-slate-100">{{ multiPlanResults.total_actions }}</p>
                  </div>
                </div>
              </div>

              <!-- 各目录计划详情 -->
              <div class="space-y-2">
                <h4 class="text-sm text-slate-400">各目录计划详情</h4>
                <div
                  v-for="(result, index) in multiPlanResults.plan_results"
                  :key="index"
                  class="p-3 rounded-lg border transition-colors"
                  :class="[
                    result.status === 'success'
                      ? 'bg-slate-950/70 border-fuchsia-400/20'
                      : result.status === 'llm_failed'
                        ? 'bg-amber-500/5 border-amber-400/20'
                        : 'bg-red-500/5 border-red-400/20'
                  ]"
                >
                  <div class="flex items-start justify-between">
                    <div class="flex items-start gap-2">
                      <div
                        class="p-1 rounded mt-0.5"
                        :class="[
                          result.status === 'success'
                            ? 'bg-fuchsia-500/10'
                            : result.status === 'llm_failed'
                              ? 'bg-amber-500/10'
                              : 'bg-red-500/10'
                        ]"
                      >
                        <CheckCircle
                          v-if="result.status === 'success'"
                          :size="14"
                          class="text-fuchsia-400"
                        />
                        <AlertCircle
                          v-else-if="result.status === 'llm_failed'"
                          :size="14"
                          class="text-amber-400"
                        />
                        <AlertCircle
                          v-else
                          :size="14"
                          class="text-red-400"
                        />
                      </div>
                      <div>
                        <p class="text-sm text-slate-200 font-mono break-all">{{ result.target_path }}</p>
                        <p class="text-xs text-slate-500 mt-1">
                          {{ result.file_count }} 个文件 · {{ result.action_count }} 条行动
                        </p>
                        <p v-if="result.error" class="text-xs" :class="result.status === 'llm_failed' ? 'text-amber-400' : 'text-red-400'" >
                          {{ result.status === 'llm_failed' ? 'LLM错误: ' : '错误: ' }}{{ result.error }}
                        </p>
                      </div>
                    </div>
                    <span
                      class="inline-flex px-2 py-0.5 rounded text-xs font-medium"
                      :class="[
                        result.status === 'success'
                          ? 'text-fuchsia-300 bg-fuchsia-500/10 border border-fuchsia-400/20'
                          : result.status === 'llm_failed'
                            ? 'text-amber-300 bg-amber-500/10 border border-amber-400/20'
                            : 'text-red-300 bg-red-500/10 border border-red-400/20'
                      ]"
                    >
                      {{ result.status === 'success' ? '成功' : result.status === 'llm_failed' ? 'LLM失败' : '失败' }}
                    </span>
                  </div>
                </div>
              </div>

              <div class="p-3 rounded-lg bg-fuchsia-500/5 border border-fuchsia-400/20">
                <p class="text-xs text-slate-400">
                  ✨ 计划已生成！关闭此弹窗后，可以在主界面查看完整的整理计划并执行。注意：由于每个目录的结构不同，建议分别检查和执行各目录的计划以确保安全性。
                </p>
              </div>
            </div>

            <!-- 目录添加界面 -->
            <div v-else class="space-y-4">
              <!-- 添加目录区域 -->
              <div class="p-4 rounded-lg bg-slate-950/70 border border-white/10">
                <h3 class="text-sm font-medium text-slate-200 mb-3">添加目标目录</h3>
                <div class="flex flex-col md:flex-row gap-3">
                  <div class="relative flex-1">
                    <div class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                      <FolderOpen :size="18" />
                    </div>
                    <input
                      type="text"
                      v-model="newMultiTargetPath"
                      class="w-full pl-10 pr-4 py-2.5 rounded-lg border border-white/10 bg-slate-950/80 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-400/50 font-mono text-sm"
                      placeholder="输入目录路径，如 C:\Users\Documents"
                      @keyup.enter="addMultiTarget"
                    />
                  </div>
                  <div class="flex gap-2">
                    <button
                      type="button"
                      class="px-4 py-2 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 transition-colors text-slate-200 text-sm"
                      @click="addMultiTargetViaDialog"
                    >
                      📂 选择目录
                    </button>
                    <button
                      type="button"
                      class="px-4 py-2 rounded-lg border border-emerald-400/30 bg-emerald-500/10 hover:bg-emerald-500/20 transition-colors text-emerald-200 text-sm"
                      :disabled="!newMultiTargetPath.trim()"
                      @click="addMultiTarget"
                    >
                      添加
                    </button>
                  </div>
                </div>
              </div>

              <!-- 已添加目录列表 -->
              <div v-if="multiTargets.length > 0" class="space-y-2">
                <h4 class="text-sm text-slate-400">已添加的目录 ({{ multiTargets.length }})</h4>
                <div class="space-y-2">
                  <div
                    v-for="(path, index) in multiTargets"
                    :key="index"
                    class="flex items-center justify-between p-3 rounded-lg bg-slate-950/70 border border-white/10 hover:border-emerald-400/30 transition-colors"
                  >
                    <div class="flex items-center gap-2 min-w-0">
                      <div class="p-1.5 rounded bg-emerald-500/10">
                        <FolderOpen :size="14" class="text-emerald-400" />
                      </div>
                      <div class="min-w-0">
                        <p class="text-sm text-slate-200 font-mono break-all">{{ path }}</p>
                        <p class="text-xs text-slate-500">#{{ index + 1 }}</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      class="p-1.5 rounded hover:bg-red-500/10 text-red-400 opacity-60 hover:opacity-100 transition-opacity"
                      @click="removeMultiTarget(index)"
                      title="移除此目录"
                    >
                      <X :size="16" />
                    </button>
                  </div>
                </div>
              </div>

              <!-- 空状态 -->
              <div v-else class="flex flex-col items-center justify-center py-12 text-slate-500">
                <HardDrive :size="48" class="mb-3 text-slate-700" />
                <p class="text-lg">暂无目录</p>
                <p class="text-sm mt-1">点击"选择目录"或输入路径添加要批量处理的目录</p>
              </div>

              <!-- 使用提示 -->
              <div class="p-3 rounded-lg bg-slate-950/50 border border-white/5">
                <h4 class="text-xs text-slate-400 font-semibold uppercase mb-2">使用说明</h4>
                <ul class="text-xs text-slate-500 space-y-1">
                  <li>• <span class="text-emerald-400">仅扫描</span>：多目录合并扫描，生成统一的文件列表和分析摘要</li>
                  <li>• <span class="text-fuchsia-400">生成AI计划</span>：为每个目录分别调用LLM生成整理计划，然后合并展示</li>
                  <li>• 扫描完成后，可以使用现有的"规则模板"快速应用整理规则</li>
                  <li>• 各目录的执行和回滚是独立的，建议谨慎检查后再执行</li>
                </ul>
              </div>
            </div>
          </div>

          <!-- 弹窗底部 -->
          <div class="p-4 border-t border-white/10 flex items-center justify-between">
            <div class="text-xs text-slate-500 font-mono">
              <template v-if="isMultiMode">
                💡 已进入多目录模式，关闭弹窗后可在主界面查看合并结果
              </template>
              <template v-else>
                提示：至少需要添加 2 个目录才能体现批量处理的优势
              </template>
            </div>
            <button
              type="button"
              class="px-4 py-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-slate-200 text-sm"
              @click="hideMultiTargets"
            >
              {{ isMultiMode ? '关闭' : '取消' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 文件去重功能弹窗 -->
      <div v-if="isShowingDuplicates" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
        <div class="relative w-full max-w-5xl max-h-[90vh] overflow-hidden rounded-lg glass-strong border border-white/10 flex flex-col">
          <!-- 弹窗头部 -->
          <div class="flex items-center justify-between p-4 border-b border-white/10">
            <div class="flex items-center gap-3">
              <Sparkles :size="24" class="text-amber-400" />
              <div>
                <p class="font-medium text-slate-100">文件去重检测</p>
                <p class="text-xs text-slate-400 font-mono">
                  <template v-if="hasDuplicates">
                    发现 {{ duplicateGroups.length }} 组重复文件，共 {{ totalDuplicateCount }} 个冗余文件
                    · 可释放空间：{{ formatBytes(totalDuplicateSize) }}
                  </template>
                  <template v-else-if="isDetectingDuplicates">
                    正在扫描...
                  </template>
                  <template v-else>
                    未发现重复文件
                  </template>
                </p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <button
                v-if="hasDuplicates"
                type="button"
                class="px-3 py-1.5 rounded-lg border border-amber-400/30 bg-amber-500/10 hover:bg-amber-500/20 transition-colors text-amber-100 text-xs"
                :disabled="isProcessingDuplicates || isDetectingDuplicates"
                @click="processAllDuplicates"
              >
                一键处理所有
              </button>
              <button
                type="button"
                class="px-3 py-1.5 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-slate-200 text-xs"
                :disabled="isDetectingDuplicates"
                @click="detectDuplicates"
              >
                重新检测
              </button>
              <button
                type="button"
                class="p-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors"
                @click="hideDuplicates"
                title="关闭"
              >
                <X :size="20" class="text-slate-300" />
              </button>
            </div>
          </div>

          <!-- 弹窗内容 -->
          <div class="flex-1 overflow-auto p-4">
            <div v-if="duplicateError" class="flex items-center gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
              <AlertCircle :size="20" />
              <p>{{ duplicateError }}</p>
            </div>

            <div v-else-if="isDetectingDuplicates" class="flex items-center justify-center h-64">
              <div class="flex items-center gap-3 text-slate-400">
                <Loader2 :size="24" class="animate-spin" />
                <p>正在检测重复文件...</p>
              </div>
            </div>

            <div v-else-if="duplicateResult" class="p-4 rounded-lg bg-emerald-500/10 border border-emerald-400/20 text-emerald-100">
              <p class="font-bold">处理完成！</p>
              <p class="text-sm text-emerald-200/80 mt-1">
                已删除 {{ duplicateResult.deleted_count }} 个重复文件
              </p>
              <p v-if="duplicateResult.kept_file" class="text-xs text-emerald-200/60 mt-2 font-mono">
                保留文件：{{ duplicateResult.kept_file }}
              </p>
            </div>

            <div v-else-if="!hasDuplicates && !isDetectingDuplicates" class="flex flex-col items-center justify-center h-64 text-slate-400">
              <Sparkles :size="48" class="mb-3 text-slate-600" />
              <p class="text-lg font-medium">未发现重复文件</p>
              <p class="text-sm mt-1">当前目录中的文件都是唯一的</p>
            </div>

            <div v-else class="w-full space-y-4">
              <div
                v-for="(group, groupIndex) in duplicateGroups"
                :key="group.hash"
                class="p-4 rounded-lg bg-slate-950/70 border border-white/10 space-y-3"
              >
                <!-- 组标题 -->
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-3">
                    <span class="px-2 py-0.5 rounded-lg border text-xs font-semibold text-amber-300 bg-amber-500/10 border-amber-400/20">
                      重复组 #{{ groupIndex + 1 }}
                    </span>
                    <span class="text-xs text-slate-400 font-mono">
                      {{ group.files.length }} 个文件 · 每个 {{ formatBytes(group.size) }} · 共浪费 {{ formatBytes(group.size * (group.files.length - 1)) }}
                    </span>
                  </div>
                  <button
                    type="button"
                    class="px-3 py-1.5 rounded-lg border border-amber-400/30 bg-amber-500/10 hover:bg-amber-500/20 transition-colors text-amber-100 text-xs"
                    :disabled="isProcessingDuplicates"
                    @click="processKeepSelected(groupIndex)"
                  >
                    处理此组
                  </button>
                </div>

                <!-- 哈希信息 -->
                <div class="text-xs text-slate-500 font-mono truncate">
                  哈希：{{ group.hash.substring(0, 16) }}...
                </div>

                <!-- 文件列表 -->
                <div class="space-y-2">
                  <div
                    v-for="(file, fileIndex) in group.files"
                    :key="file.path"
                    class="flex items-center gap-3 p-3 rounded-lg transition-colors cursor-pointer"
                    :class="[
                      selectedKeepFiles[groupIndex] === file.path
                        ? 'bg-emerald-500/10 border border-emerald-400/20'
                        : 'bg-slate-900/50 border border-white/5 hover:bg-slate-800/50'
                    ]"
                    @click="selectKeepFile(groupIndex, file.path)"
                  >
                    <!-- 选择标记 -->
                    <div class="flex items-center justify-center w-6 h-6 rounded-full border"
                      :class="[
                        selectedKeepFiles[groupIndex] === file.path
                          ? 'border-emerald-400 bg-emerald-500/20'
                          : 'border-slate-600'
                      ]"
                    >
                      <CheckCircle
                        v-if="selectedKeepFiles[groupIndex] === file.path"
                        :size="14"
                        class="text-emerald-400"
                      />
                    </div>

                    <!-- 文件信息 -->
                    <div class="p-2 rounded-lg bg-slate-800 text-slate-400">
                      <FileText :size="20" />
                    </div>

                    <div class="flex-1 min-w-0">
                      <div class="flex items-center gap-2">
                        <p class="font-medium text-slate-200 truncate">{{ file.name }}</p>
                        <span v-if="selectedKeepFiles[groupIndex] === file.path"
                          class="px-2 py-0.5 rounded-full text-xs font-semibold text-emerald-300 bg-emerald-500/10"
                        >
                          保留
                        </span>
                        <span v-else
                          class="px-2 py-0.5 rounded-full text-xs font-semibold text-red-400 bg-red-500/10"
                        >
                          将删除
                        </span>
                      </div>
                      <p class="text-xs text-slate-500 font-mono truncate">{{ file.path }}</p>
                      <p class="text-xs text-slate-500 font-mono">
                        {{ file.extension || 'UNKNOWN' }} · {{ formatBytes(file.size) }}
                      </p>
                    </div>

                    <!-- 预览按钮 -->
                    <button
                      type="button"
                      class="p-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors"
                      :disabled="isGeneratingPlan || isExecutingPlan"
                      @click.stop="previewFile(file)"
                      title="预览文件"
                    >
                      <Eye :size="16" class="text-slate-300" />
                    </button>
                  </div>
                </div>

                <!-- 提示 -->
                <p class="text-xs text-slate-500">
                  提示：点击选择要保留的文件，其他文件将被删除。删除的文件会进入回收站，可通过"时光倒流"恢复。
                </p>
              </div>
            </div>
          </div>

          <!-- 弹窗底部 -->
          <div class="p-4 border-t border-white/10 flex items-center justify-between">
            <div class="text-xs text-slate-500 font-mono">
              <template v-if="hasDuplicates">
                预计可释放空间：<span class="text-amber-400">{{ formatBytes(totalDuplicateSize) }}</span>
              </template>
            </div>
            <button
              type="button"
              class="px-4 py-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-slate-200 text-sm"
              @click="hideDuplicates"
            >
              关闭
            </button>
          </div>
        </div>
      </div>

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
