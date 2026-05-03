import { ref, computed, watch } from 'vue'
import api from '../api'

const RENAME_RULE_TYPES = [
  { value: 'prefix', label: '添加前缀', icon: '➕' },
  { value: 'suffix', label: '添加后缀', icon: '➕' },
  { value: 'find_replace', label: '查找替换', icon: '🔄' },
  { value: 'regex', label: '正则替换', icon: '🔍' },
  { value: 'numbering', label: '批量编号', icon: '🔢' },
  { value: 'date_prefix', label: '日期前缀', icon: '📅' },
  { value: 'date_suffix', label: '日期后缀', icon: '📅' },
]

export function useRenamer(options = {}) {
  const { onLog, extractErrorMessage } = options

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

  const hasSelectedFiles = computed(() => renameSelectedFiles.value.length > 0)
  const hasRules = computed(() => renameRules.value.length > 0)
  const canPreview = computed(() => hasSelectedFiles.value && hasRules.value)
  const canExecute = computed(() => renamePreviews.value.length > 0 && !renameHasConflicts.value && !isExecutingRename.value)

  const showRenamer = (availableFiles = []) => {
    isShowingRenamer.value = true
    renameSelectedFiles.value = []
    renameRules.value = [{ type: activeRenameRuleType.value, params: {} }]
    renamePreviews.value = []
    renameConflicts.value = []
    renameHasConflicts.value = false
    renameError.value = null
    renameResult.value = null
  }

  const hideRenamer = () => {
    isShowingRenamer.value = false
    renameError.value = null
    renameResult.value = null
  }

  const toggleFileSelection = (file) => {
    const index = renameSelectedFiles.value.findIndex(f => f.path === file.path)
    if (index > -1) {
      renameSelectedFiles.value.splice(index, 1)
    } else {
      renameSelectedFiles.value.push(file)
    }
    renamePreviews.value = []
  }

  const selectAllFiles = (allFiles) => {
    renameSelectedFiles.value = [...allFiles]
    renamePreviews.value = []
  }

  const deselectAllFiles = () => {
    renameSelectedFiles.value = []
    renamePreviews.value = []
  }

  const addRule = () => {
    renameRules.value.push({ type: activeRenameRuleType.value, params: {} })
    renamePreviews.value = []
  }

  const removeRule = (index) => {
    if (renameRules.value.length > 1) {
      renameRules.value.splice(index, 1)
      renamePreviews.value = []
    }
  }

  const updateRuleType = (index, type) => {
    renameRules.value[index].type = type
    renameRules.value[index].params = {}
    renamePreviews.value = []
  }

  const previewRename = async () => {
    if (!canPreview.value) {
      renameError.value = '请先选择文件并添加至少一条重命名规则'
      return
    }

    isLoadingRenamePreview.value = true
    renameError.value = null
    renamePreviews.value = []
    renameConflicts.value = []
    renameHasConflicts.value = false

    try {
      const response = await api.renamePreview(
        renameSelectedFiles.value.map(f => ({ path: f.path, name: f.name, extension: f.extension })),
        renameRules.value
      )

      renamePreviews.value = response.data.previews || []
      renameConflicts.value = response.data.conflicts || []
      renameHasConflicts.value = response.data.has_conflicts || false

      if (onLog) {
        onLog({ type: 'info', message: `预览生成完成，共 ${renamePreviews.value.length} 个文件` })
      }

      if (renameHasConflicts.value) {
        renameError.value = `检测到 ${renameConflicts.value.length} 个冲突，请检查重命名规则`
        if (onLog) {
          onLog({ type: 'warning', message: renameError.value })
        }
      }
    } catch (err) {
      renameError.value = extractErrorMessage ? extractErrorMessage(err) : '生成预览失败'
      if (onLog) {
        onLog({ type: 'error', message: `生成预览失败: ${renameError.value}` })
      }
      console.error('Rename preview error:', err)
    } finally {
      isLoadingRenamePreview.value = false
    }
  }

  const executeRename = async () => {
    if (!canExecute.value) {
      return
    }

    if (renameHasConflicts.value) {
      if (!confirm('检测到命名冲突，继续执行可能导致文件覆盖。是否继续？')) {
        return
      }
    }

    isExecutingRename.value = true
    renameError.value = null
    renameResult.value = null

    try {
      if (onLog) {
        onLog({ type: 'info', message: '正在执行重命名...' })
      }

      const response = await api.renameExecute(
        renameSelectedFiles.value.map(f => ({ path: f.path, name: f.name, extension: f.extension })),
        renameRules.value
      )

      renameResult.value = response.data

      if (onLog) {
        onLog({ type: 'success', message: `重命名完成，成功 ${response.data.success_count} 个，失败 ${response.data.failed_count} 个` })
      }

      return response.data
    } catch (err) {
      renameError.value = extractErrorMessage ? extractErrorMessage(err) : '执行重命名失败'
      if (onLog) {
        onLog({ type: 'error', message: `执行重命名失败: ${renameError.value}` })
      }
      console.error('Rename execute error:', err)
      return null
    } finally {
      isExecutingRename.value = false
    }
  }

  return {
    isShowingRenamer,
    isLoadingRenamePreview,
    isExecutingRename,
    renameSelectedFiles,
    renameRules,
    renamePreviews,
    renameConflicts,
    renameHasConflicts,
    renameError,
    renameResult,
    activeRenameRuleType,
    RENAME_RULE_TYPES,
    hasSelectedFiles,
    hasRules,
    canPreview,
    canExecute,
    showRenamer,
    hideRenamer,
    toggleFileSelection,
    selectAllFiles,
    deselectAllFiles,
    addRule,
    removeRule,
    updateRuleType,
    previewRename,
    executeRename,
  }
}

export default useRenamer
