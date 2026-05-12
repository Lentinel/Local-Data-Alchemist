import { ref, computed, watch } from 'vue'
import api from '../api'

/**
 * 核心业务逻辑 composable
 * 包含目录锁定、计划生成、执行、回滚等核心功能
 */
export function useCore(options = {}) {
  const { onLog, extractErrorMessage } = options

  // 核心状态
  const targetPath = ref(null)
  const manualTargetPath = ref('')
  const files = ref([])
  const analysis = ref(null)
  const actionPlan = ref([])
  const executionResult = ref(null)
  const undoMessage = ref(null)
  const error = ref(null)
  const fileInventory = ref([])
  const mode = ref('')
  const isSelectingFolder = ref(false)
  const isGeneratingPlan = ref(false)
  const isExecutingPlan = ref(false)
  const isUndoing = ref(false)

  // 计划预览和二次确认
  const isShowingPlanPreview = ref(false)
  const isLoadingPreview = ref(false)
  const planPreviewData = ref(null)
  const planPreviewError = ref(null)
  const needFinalConfirmation = ref(false)
  const finalConfirmChecked = ref(false)

  // 计算属性
  const hasActivePlan = computed(() => actionPlan.value && actionPlan.value.length > 0)
  const canUndo = computed(() => !isUndoing.value && executionResult.value !== null)

  // 打开系统目录选择器
  const openNativeFolderDialog = async () => {
    if (onLog) onLog('[系统] 请求系统原生目录选择器...', 'info')
    isSelectingFolder.value = true
    error.value = null

    try {
      const response = await api.selectFolder()
      const data = response.data

      if (data.status === 'cancelled') {
        if (onLog) onLog('[系统] 用户取消了目录选择', 'info')
        return
      }

      targetPath.value = data.target_path
      files.value = data.files || []
      analysis.value = data.analysis || null
      actionPlan.value = []
      executionResult.value = null
      undoMessage.value = null

      if (onLog) onLog(`[系统] 已锁定目录：${data.target_path}`, 'info')
      if (onLog) onLog(`[扫描] 发现 ${files.value.length} 个文件`, 'info')
    } catch (err) {
      error.value = extractErrorMessage ? extractErrorMessage(err) : '目录选择失败'
      if (onLog) onLog(`[错误] 目录选择失败：${error.value}`, 'error')
    } finally {
      isSelectingFolder.value = false
    }
  }

  // 手动锁定目录
  const lockManualTarget = async () => {
    const path = manualTargetPath.value.trim()
    if (!path) {
      error.value = '请输入目标目录路径'
      return
    }

    isSelectingFolder.value = true
    error.value = null

    try {
      const response = await api.lockFolder(path)
      const data = response.data

      targetPath.value = data.target_path
      files.value = data.files || []
      analysis.value = data.analysis || null
      actionPlan.value = []
      executionResult.value = null
      undoMessage.value = null

      if (onLog) onLog(`[系统] 已锁定目录：${data.target_path}`, 'info')
      if (onLog) onLog(`[扫描] 发现 ${files.value.length} 个文件`, 'info')
    } catch (err) {
      error.value = extractErrorMessage ? extractErrorMessage(err) : '锁定目录失败'
      if (onLog) onLog(`[错误] 锁定目录失败：${error.value}`, 'error')
    } finally {
      isSelectingFolder.value = false
    }
  }

  // 生成 AI 炼金计划
  const generateAlchemyPlan = async () => {
    if (!targetPath.value) {
      error.value = '请先锁定一个目录'
      return
    }

    isGeneratingPlan.value = true
    error.value = null
    actionPlan.value = []
    executionResult.value = null
    undoMessage.value = null

    try {
      if (onLog) onLog('[AI] 正在生成炼金计划...', 'info')

      const response = await api.generatePlan(targetPath.value)
      const data = response.data

      actionPlan.value = data.plan || []
      fileInventory.value = data.file_inventory || []
      mode.value = data.mode || ''

      if (data.llm_error) {
        if (onLog) onLog(`[AI] LLM 不可用，已启用本地兜底：${data.llm_error}`, 'warning')
      }

      if (onLog) onLog(`[AI] 计划生成完成，共 ${actionPlan.value.length} 条操作`, 'info')
    } catch (err) {
      error.value = extractErrorMessage ? extractErrorMessage(err) : '生成计划失败'
      if (onLog) onLog(`[错误] 生成计划失败：${error.value}`, 'error')
    } finally {
      isGeneratingPlan.value = false
    }
  }

  // 加载计划预览
  const loadPlanPreview = async () => {
    if (!targetPath.value || !actionPlan.value || actionPlan.value.length === 0) {
      planPreviewError.value = '没有可预览的计划'
      return
    }

    isLoadingPreview.value = true
    planPreviewError.value = null
    isShowingPlanPreview.value = true

    try {
      if (onLog) onLog('[预览] 正在加载计划预览...', 'info')

      const response = await api.previewPlan(targetPath.value, actionPlan.value)
      planPreviewData.value = response.data

      if (onLog) onLog('[预览] 计划预览加载完成', 'info')
    } catch (err) {
      planPreviewError.value = extractErrorMessage ? extractErrorMessage(err) : '加载预览失败'
      if (onLog) onLog(`[错误] 加载预览失败：${planPreviewError.value}`, 'error')
    } finally {
      isLoadingPreview.value = false
    }
  }

  // 批准并执行
  const approveAndExecute = async () => {
    if (!targetPath.value || actionPlan.value.length === 0) {
      error.value = '没有可执行的计划'
      return
    }

    isShowingPlanPreview.value = false
    await executePlanDirectly()
  }

  // 直接执行计划
  const executePlanDirectly = async () => {
    if (!targetPath.value || actionPlan.value.length === 0) {
      error.value = '没有可执行的计划'
      return
    }

    isExecutingPlan.value = true
    error.value = null
    executionResult.value = null
    undoMessage.value = null

    try {
      if (onLog) onLog('[执行] 正在执行炼金计划...', 'info')

      const response = await api.startExecuteTask(targetPath.value, actionPlan.value)
      const data = response.data

      if (data.task_id) {
        if (onLog) onLog(`[执行] 异步任务已启动：${data.task_id}`, 'info')
        return data.task_id
      }

      executionResult.value = data
      if (onLog) onLog(`[执行] 执行完成，共处理 ${data.executed || 0} 个文件`, 'info')
    } catch (err) {
      error.value = extractErrorMessage ? extractErrorMessage(err) : '执行计划失败'
      if (onLog) onLog(`[错误] 执行计划失败：${error.value}`, 'error')
    } finally {
      isExecutingPlan.value = false
    }
  }

  // 取消计划预览
  const cancelPlanPreview = () => {
    isShowingPlanPreview.value = false
    planPreviewData.value = null
    planPreviewError.value = null
    needFinalConfirmation.value = false
    finalConfirmChecked.value = false
  }

  // 回滚计划
  const undoPlan = async () => {
    if (!targetPath.value) {
      error.value = '没有可回滚的目标目录'
      return
    }

    isUndoing.value = true
    error.value = null
    undoMessage.value = null

    try {
      if (onLog) onLog('[回滚] 正在执行时光倒流...', 'info')

      const response = await api.undoPlan(targetPath.value)
      const data = response.data

      undoMessage.value = data.message || '回滚完成'
      executionResult.value = null

      if (onLog) onLog(`[回滚] ${undoMessage.value}`, 'info')

      // 重新扫描目录
      const lockResponse = await api.lockFolder(targetPath.value)
      const lockData = lockResponse.data
      files.value = lockData.files || []
      analysis.value = lockData.analysis || null
      actionPlan.value = []
    } catch (err) {
      error.value = extractErrorMessage ? extractErrorMessage(err) : '回滚失败'
      if (onLog) onLog(`[错误] 回滚失败：${error.value}`, 'error')
    } finally {
      isUndoing.value = false
    }
  }

  // 重置状态
  const resetState = () => {
    files.value = []
    analysis.value = null
    actionPlan.value = []
    executionResult.value = null
    undoMessage.value = null
    error.value = null
  }

  return {
    // 状态
    targetPath,
    manualTargetPath,
    files,
    analysis,
    actionPlan,
    executionResult,
    undoMessage,
    error,
    fileInventory,
    mode,
    isSelectingFolder,
    isGeneratingPlan,
    isExecutingPlan,
    isUndoing,
    isShowingPlanPreview,
    isLoadingPreview,
    planPreviewData,
    planPreviewError,
    needFinalConfirmation,
    finalConfirmChecked,
    // 计算属性
    hasActivePlan,
    canUndo,
    // 方法
    openNativeFolderDialog,
    lockManualTarget,
    generateAlchemyPlan,
    loadPlanPreview,
    approveAndExecute,
    executePlanDirectly,
    cancelPlanPreview,
    undoPlan,
    resetState,
  }
}
