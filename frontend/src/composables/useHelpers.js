import { ref } from 'vue'

/**
 * 工具函数和常量 composable
 * 包含文件名验证、格式化、分类标签等工具函数
 */
export function useHelpers() {
  // Windows 文件名验证常量
  const WINDOWS_INVALID_CHARS = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
  const WINDOWS_RESERVED_NAMES = [
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
  ]
  const MAX_FILENAME_LENGTH = 255

  // 重命名规则类型
  const RENAME_RULE_TYPES = [
    { value: 'prefix', label: '添加前缀', icon: '➕' },
    { value: 'suffix', label: '添加后缀', icon: '➕' },
    { value: 'find_replace', label: '查找替换', icon: '🔄' },
    { value: 'regex', label: '正则替换', icon: '🔍' },
    { value: 'numbering', label: '批量编号', icon: '🔢' },
    { value: 'date_prefix', label: '日期前缀', icon: '📅' },
    { value: 'date_suffix', label: '日期后缀', icon: '📅' },
  ]

  // 分类颜色
  const CATEGORY_COLORS = {
    images: '#10b981',
    documents: '#3b82f6',
    archives: '#f59e0b',
    code: '#8b5cf6',
    logs: '#ef4444',
    unknown: '#6b7280',
  }

  // 分类标签
  const CATEGORY_LABELS = {
    images: '图片',
    documents: '文档/数据表',
    archives: '压缩包',
    code: '代码',
    logs: '日志',
    unknown: '未知类型',
  }

  // 分类标签映射（详细版）
  const categoryLabels = {
    logs: '日志文件',
    images: '图片文件',
    documents: '文档文件',
    archives: '压缩包',
    code: '代码文件',
    unknown: '未知类型',
  }

  // 大小桶标签
  const SIZE_BUCKET_LABELS = {
    tiny: '< 100KB',
    small: '100KB - 1MB',
    medium: '1MB - 10MB',
    large: '10MB - 100MB',
    huge: '> 100MB',
  }

  // 分类样式
  const categoryTone = {
    logs: 'text-amber-300 bg-amber-500/10 border-amber-400/20',
    images: 'text-emerald-300 bg-emerald-500/10 border-emerald-400/20',
    documents: 'text-sky-300 bg-sky-500/10 border-sky-400/20',
    archives: 'text-orange-300 bg-orange-500/10 border-orange-400/20',
    code: 'text-violet-300 bg-violet-500/10 border-violet-400/20',
    unknown: 'text-gray-300 bg-gray-500/10 border-gray-400/20',
  }

  // 操作样式
  const actionTone = {
    rename_and_move: 'text-sky-200 bg-sky-500/10 border-sky-400/30',
    move: 'text-emerald-200 bg-emerald-500/10 border-emerald-400/30',
    delete: 'text-rose-200 bg-rose-500/10 border-rose-400/30',
    keep: 'text-gray-200 bg-gray-500/10 border-gray-400/30',
  }

  // 操作标签
  const actionLabel = {
    rename_and_move: '重命名并移动',
    move: '移动',
    delete: '删除',
    keep: '保留',
  }

  // 严重级别样式
  const severityTone = {
    low: 'text-emerald-200 bg-emerald-500/10 border-emerald-400/30',
    medium: 'text-amber-200 bg-amber-500/10 border-amber-400/30',
    high: 'text-orange-200 bg-orange-500/10 border-orange-400/30',
    critical: 'text-rose-200 bg-rose-500/10 border-rose-400/30',
  }

  // 严重级别标签
  const severityLabel = {
    low: '低',
    medium: '中',
    high: '高',
    critical: '严重',
  }

  // 加载提示
  const loadingTips = [
    '正在嗅探文件结构...',
    'AI 正在分析文件内容...',
    '正在生成整理计划...',
    '正在提取财务信息...',
    '正在分析日志文件...',
    '即将完成，请稍候...',
  ]

  // LLM 连接错误文本
  const llmConnectionErrorText = {
    placeholder_config_detected: '连接测试已跳过，因为配置仍是示例占位值',
    connection_timeout: '连接超时，请检查网络或 API 地址',
    authentication_error: '认证失败，请检查 API Key',
    connection_refused: '连接被拒绝，请检查 API 地址',
  }

  // 验证文件名
  const validateFilename = (filename) => {
    if (!filename || !filename.trim()) {
      return { valid: false, reason: '文件名为空' }
    }

    for (const char of WINDOWS_INVALID_CHARS) {
      if (filename.includes(char)) {
        return { valid: false, reason: `包含非法字符: ${char}` }
      }
    }

    const nameWithoutExt = filename.substring(0, filename.lastIndexOf('.') || filename.length).toUpperCase()
    for (const reserved of WINDOWS_RESERVED_NAMES) {
      if (nameWithoutExt === reserved || nameWithoutExt.startsWith(reserved + '.')) {
        return { valid: false, reason: `包含 Windows 保留名称: ${reserved}` }
      }
    }

    if (filename.endsWith('.') || filename.endsWith(' ')) {
      return { valid: false, reason: '文件名不能以点或空格结尾' }
    }

    if (filename.length > MAX_FILENAME_LENGTH) {
      return { valid: false, reason: `文件名过长 (${filename.length} > ${MAX_FILENAME_LENGTH})` }
    }

    const stem = filename.substring(0, filename.lastIndexOf('.') || filename.length)
    if (!stem.trim()) {
      return { valid: false, reason: '文件名主体部分为空' }
    }

    return { valid: true, reason: null }
  }

  // 格式化字节数
  const formatBytes = (bytes) => {
    if (!bytes) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB', 'TB']
    let i = 0
    let size = bytes
    while (size >= 1024 && i < units.length - 1) {
      size /= 1024
      i++
    }
    return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
  }

  // 格式化金额
  const formatMoney = (amount, currency) => {
    if (!Number.isFinite(amount)) {
      return '—'
    }
    try {
      return new Intl.NumberFormat('zh-CN', {
        style: 'currency',
        currency: currency || 'CNY',
        minimumFractionDigits: 2,
      }).format(amount)
    } catch {
      return `${amount.toFixed(2)} ${currency || 'CNY'}`
    }
  }

  // 格式化日期时间
  const formatDateTime = (dateTimeStr) => {
    if (!dateTimeStr) return '—'
    try {
      const date = new Date(dateTimeStr)
      return date.toLocaleString('zh-CN', { hour12: false })
    } catch {
      return dateTimeStr
    }
  }

  // 提取错误消息
  const extractErrorMessage = (error) => {
    if (!error) {
      return '未知错误'
    }
    if (typeof error === 'string') {
      return error
    }
    if (error.response?.data?.detail) {
      return error.response.data.detail
    }
    if (error.response?.data?.message) {
      return error.response.data.message
    }
    if (error.message) {
      return error.message
    }
    return String(error)
  }

  // 获取操作标签
  const getActionLabel = (action) => {
    switch (action) {
      case 'rename_and_move': return '重命名并移动'
      case 'move': return '移动'
      case 'delete': return '删除'
      case 'keep': return '保留'
      default: return action
    }
  }

  // 获取操作颜色
  const getActionColor = (action) => {
    switch (action) {
      case 'rename_and_move': return 'text-sky-300'
      case 'move': return 'text-emerald-300'
      case 'delete': return 'text-rose-300'
      case 'keep': return 'text-gray-300'
      default: return 'text-gray-300'
    }
  }

  // 获取安全级别样式
  const getSafetyLevelClass = (level) => {
    switch (level) {
      case 'safe': return 'text-emerald-300 bg-emerald-500/10 border-emerald-400/30'
      case 'warning': return 'text-amber-300 bg-amber-500/10 border-amber-400/30'
      case 'danger': return 'text-rose-300 bg-rose-500/10 border-rose-400/30'
      default: return 'text-gray-300 bg-gray-500/10 border-gray-400/30'
    }
  }

  // 获取安全级别标签
  const getSafetyLevelLabel = (level) => {
    switch (level) {
      case 'safe': return '安全'
      case 'warning': return '注意'
      case 'danger': return '危险'
      default: return '未知'
    }
  }

  // 获取历史记录类型标签
  const getHistoryTypeLabels = (type) => {
    const labels = {
      execute: '执行计划',
      undo: '回滚操作',
      rename: '批量重命名',
      deduplicate: '去重操作',
      template_apply: '应用模板',
    }
    return labels[type] || type
  }

  // LLM 连接状态格式化
  const formatLlmConnectionError = (connectionError) => {
    if (!connectionError) {
      return '未知错误'
    }
    return llmConnectionErrorText[connectionError] || connectionError
  }

  // LLM 连接状态格式化
  const formatLlmConnectionStatus = (connectionStatus) => {
    if (!connectionStatus) {
      return '未知'
    }
    const statusMap = {
      ok: '连接正常',
      failed: '连接失败',
      skipped: '已跳过',
      error: '发生错误',
    }
    return statusMap[connectionStatus] || connectionStatus
  }

  // LLM 配置状态格式化
  const formatLlmConfigStatus = (fieldName, configured) => {
    return configured ? '已配置' : '未配置'
  }

  return {
    // 常量
    WINDOWS_INVALID_CHARS,
    WINDOWS_RESERVED_NAMES,
    MAX_FILENAME_LENGTH,
    RENAME_RULE_TYPES,
    CATEGORY_COLORS,
    CATEGORY_LABELS,
    categoryLabels,
    SIZE_BUCKET_LABELS,
    categoryTone,
    actionTone,
    actionLabel,
    severityTone,
    severityLabel,
    loadingTips,
    llmConnectionErrorText,
    // 函数
    validateFilename,
    formatBytes,
    formatMoney,
    formatDateTime,
    extractErrorMessage,
    getActionLabel,
    getActionColor,
    getSafetyLevelClass,
    getSafetyLevelLabel,
    getHistoryTypeLabels,
    formatLlmConnectionError,
    formatLlmConnectionStatus,
    formatLlmConfigStatus,
  }
}
