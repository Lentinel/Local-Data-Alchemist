import { ref, computed } from 'vue'
import api from '../api'

export function useDuplicates(options = {}) {
  const { onLog, extractErrorMessage } = options

  const isDetectingDuplicates = ref(false)
  const isShowingDuplicates = ref(false)
  const isProcessingDuplicates = ref(false)
  const duplicateGroups = ref([])
  const selectedKeepFiles = ref({})
  const duplicateError = ref(null)
  const duplicateResult = ref(null)

  const hasDuplicates = computed(() => duplicateGroups.value.length > 0)

  const detectDuplicates = async (targetPath, fastMode = true) => {
    if (!targetPath) {
      duplicateError.value = '请先锁定一个目录'
      return
    }

    duplicateError.value = null
    duplicateResult.value = null
    duplicateGroups.value = []
    selectedKeepFiles.value = {}
    isDetectingDuplicates.value = true
    isShowingDuplicates.value = true

    try {
      if (onLog) {
        onLog({ type: 'info', message: '开始检测重复文件...' })
      }

      const response = await api.detectDuplicates(targetPath, fastMode)
      duplicateGroups.value = response.data.groups || []

      if (duplicateGroups.value.length > 0) {
        duplicateGroups.value.forEach((group) => {
          if (group.files && group.files.length > 0) {
            selectedKeepFiles.value[group.hash] = group.files[0].path
          }
        })
        if (onLog) {
          onLog({ type: 'info', message: `检测到 ${duplicateGroups.value.length} 组重复文件` })
        }
      } else {
        if (onLog) {
          onLog({ type: 'info', message: '未检测到重复文件' })
        }
      }
    } catch (err) {
      duplicateError.value = extractErrorMessage ? extractErrorMessage(err) : '检测重复文件失败'
      if (onLog) {
        onLog({ type: 'error', message: `检测重复文件失败: ${duplicateError.value}` })
      }
      console.error('Detect duplicates error:', err)
    } finally {
      isDetectingDuplicates.value = false
    }
  }

  const toggleKeepFile = (hash, filePath) => {
    selectedKeepFiles.value[hash] = filePath
  }

  const keepSelectedFile = async (targetPath, hash, keepFileIndex) => {
    if (!targetPath) {
      duplicateError.value = '请先锁定一个目录'
      return
    }

    const group = duplicateGroups.value.find(g => g.hash === hash)
    if (!group || !group.files) {
      duplicateError.value = '无效的重复文件组'
      return
    }

    const keepFile = selectedKeepFiles.value[hash] || group.files[0]?.path
    if (!keepFile) {
      duplicateError.value = '请选择要保留的文件'
      return
    }

    const duplicateFiles = group.files
      .map(f => f.path)
      .filter(p => p !== keepFile)

    if (duplicateFiles.length === 0) {
      duplicateError.value = '没有需要删除的重复文件'
      return
    }

    isProcessingDuplicates.value = true
    duplicateError.value = null

    try {
      if (onLog) {
        onLog({ type: 'info', message: '正在处理重复文件...' })
      }

      const response = await api.keepDuplicate(targetPath, keepFile, duplicateFiles)
      duplicateResult.value = response.data

      if (group) {
        group.processed = true
        group.kept_file = keepFile
      }

      if (onLog) {
        onLog({ type: 'success', message: `已保留文件，删除了 ${response.data.deleted_count} 个副本` })
      }
    } catch (err) {
      duplicateError.value = extractErrorMessage ? extractErrorMessage(err) : '处理重复文件失败'
      if (onLog) {
        onLog({ type: 'error', message: `处理重复文件失败: ${duplicateError.value}` })
      }
      console.error('Keep duplicate error:', err)
    } finally {
      isProcessingDuplicates.value = false
    }
  }

  const hideDuplicates = () => {
    isShowingDuplicates.value = false
    if (!isDetectingDuplicates.value) {
      duplicateGroups.value = []
      selectedKeepFiles.value = {}
      duplicateError.value = null
      duplicateResult.value = null
    }
  }

  return {
    isDetectingDuplicates,
    isShowingDuplicates,
    isProcessingDuplicates,
    duplicateGroups,
    selectedKeepFiles,
    duplicateError,
    duplicateResult,
    hasDuplicates,
    detectDuplicates,
    toggleKeepFile,
    keepSelectedFile,
    hideDuplicates,
  }
}

export default useDuplicates
