import { ref, computed } from 'vue'
import api from '../api'

export function useMultiDirectory(options = {}) {
  const { onLog, extractErrorMessage } = options

  const isShowingMultiTargets = ref(false)
  const isMultiScanning = ref(false)
  const isMultiGeneratingPlan = ref(false)
  const multiTargets = ref([])
  const multiScanResults = ref([])
  const multiPlanResults = ref([])
  const multiError = ref(null)
  const newMultiTargetPath = ref('')
  const isMultiMode = ref(false)

  const hasTargets = computed(() => multiTargets.value.length > 0)
  const hasScanResults = computed(() => multiScanResults.value.length > 0)
  const hasPlanResults = computed(() => multiPlanResults.value.length > 0)
  const canScan = computed(() => hasTargets.value && !isMultiScanning.value)
  const canGeneratePlan = computed(() => hasScanResults.value && !isMultiGeneratingPlan.value)

  const showMultiTargets = () => {
    isShowingMultiTargets.value = true
    isMultiMode.value = true
    multiError.value = null
  }

  const hideMultiTargets = () => {
    isShowingMultiTargets.value = false
    isMultiMode.value = false
    if (!isMultiScanning.value && !isMultiGeneratingPlan.value) {
      multiTargets.value = []
      multiScanResults.value = []
      multiPlanResults.value = []
      multiError.value = null
    }
  }

  const toggleMultiMode = () => {
    if (isMultiMode.value) {
      hideMultiTargets()
    } else {
      showMultiTargets()
    }
  }

  const addMultiTarget = async (path) => {
    const targetPath = path || newMultiTargetPath.value.trim()
    if (!targetPath) {
      multiError.value = '请输入目录路径'
      return
    }

    const exists = multiTargets.value.some(t => t.path === targetPath)
    if (exists) {
      multiError.value = '该目录已添加'
      return
    }

    multiTargets.value.push({
      id: Date.now().toString(),
      path: targetPath,
      name: targetPath.split(/[/\\]/).pop() || targetPath,
      status: 'pending',
    })

    newMultiTargetPath.value = ''
    multiError.value = null

    if (onLog) {
      onLog({ type: 'info', message: `已添加目录: ${targetPath}` })
    }
  }

  const removeMultiTarget = (id) => {
    const index = multiTargets.value.findIndex(t => t.id === id)
    if (index > -1) {
      const removed = multiTargets.value.splice(index, 1)[0]
      if (onLog) {
        onLog({ type: 'info', message: `已移除目录: ${removed.path}` })
      }
    }
    multiScanResults.value = multiScanResults.value.filter(r => r.target_id !== id)
    multiPlanResults.value = multiPlanResults.value.filter(r => r.target_id !== id)
  }

  const selectFolderForMulti = async () => {
    try {
      const response = await api.selectFolder()
      if (response.data && response.data.path) {
        await addMultiTarget(response.data.path)
      }
    } catch (err) {
      multiError.value = extractErrorMessage ? extractErrorMessage(err) : '选择文件夹失败'
      if (onLog) {
        onLog({ type: 'error', message: `选择文件夹失败: ${multiError.value}` })
      }
      console.error('Select folder for multi error:', err)
    }
  }

  const performMultiScan = async () => {
    if (!canScan.value) return

    isMultiScanning.value = true
    multiError.value = null
    multiScanResults.value = []

    try {
      if (onLog) {
        onLog({ type: 'info', message: `开始扫描 ${multiTargets.value.length} 个目录...` })
      }

      const response = await api.multiScan(multiTargets.value.map(t => ({
        id: t.id,
        path: t.path,
      })))

      multiScanResults.value = response.data.results || []

      multiTargets.value.forEach(target => {
        const result = multiScanResults.value.find(r => r.target_id === target.id)
        if (result) {
          target.status = result.status
        }
      })

      if (onLog) {
        const successCount = multiScanResults.value.filter(r => r.status === 'success').length
        const failCount = multiScanResults.value.filter(r => r.status === 'failed').length
        onLog({ 
          type: successCount > 0 ? 'info' : 'warning', 
          message: `多目录扫描完成: 成功 ${successCount} 个，失败 ${failCount} 个` 
        })
      }
    } catch (err) {
      multiError.value = extractErrorMessage ? extractErrorMessage(err) : '多目录扫描失败'
      if (onLog) {
        onLog({ type: 'error', message: `多目录扫描失败: ${multiError.value}` })
      }
      console.error('Multi scan error:', err)
    } finally {
      isMultiScanning.value = false
    }
  }

  const performMultiGeneratePlan = async () => {
    if (!canGeneratePlan.value) return

    isMultiGeneratingPlan.value = true
    multiError.value = null
    multiPlanResults.value = []

    try {
      if (onLog) {
        onLog({ type: 'info', message: '开始生成多目录整理计划...' })
      }

      const response = await api.multiGeneratePlan(multiScanResults.value)

      multiPlanResults.value = response.data.results || []

      const successCount = multiPlanResults.value.filter(r => r.status === 'success').length
      const failCount = multiPlanResults.value.filter(r => r.status === 'failed').length

      if (onLog) {
        onLog({ 
          type: successCount > 0 ? 'info' : 'warning', 
          message: `多目录计划生成完成: 成功 ${successCount} 个，失败 ${failCount} 个` 
        })
      }

      return response.data
    } catch (err) {
      multiError.value = extractErrorMessage ? extractErrorMessage(err) : '多目录计划生成失败'
      if (onLog) {
        onLog({ type: 'error', message: `多目录计划生成失败: ${multiError.value}` })
      }
      console.error('Multi generate plan error:', err)
      return null
    } finally {
      isMultiGeneratingPlan.value = false
    }
  }

  const getTotalFiles = computed(() => {
    return multiScanResults.value.reduce((sum, r) => sum + (r.file_count || 0), 0)
  })

  const getTotalSize = computed(() => {
    return multiScanResults.value.reduce((sum, r) => sum + (r.total_size || 0), 0)
  })

  const getTotalPlanItems = computed(() => {
    return multiPlanResults.value.reduce((sum, r) => sum + (r.plan?.length || 0), 0)
  })

  return {
    isShowingMultiTargets,
    isMultiScanning,
    isMultiGeneratingPlan,
    multiTargets,
    multiScanResults,
    multiPlanResults,
    multiError,
    newMultiTargetPath,
    isMultiMode,
    hasTargets,
    hasScanResults,
    hasPlanResults,
    canScan,
    canGeneratePlan,
    getTotalFiles,
    getTotalSize,
    getTotalPlanItems,
    showMultiTargets,
    hideMultiTargets,
    toggleMultiMode,
    addMultiTarget,
    removeMultiTarget,
    selectFolderForMulti,
    performMultiScan,
    performMultiGeneratePlan,
  }
}

export default useMultiDirectory
