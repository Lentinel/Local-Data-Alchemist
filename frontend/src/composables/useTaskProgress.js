import { ref, onBeforeUnmount } from 'vue'
import api from '../api'

export function useTaskProgress(emit) {
  const currentTaskId = ref(null)
  const taskStatus = ref(null)
  const taskProgress = ref(0)
  const taskTotal = ref(0)
  const taskMessage = ref('')
  const taskCurrentFile = ref('')
  const isTaskRunning = ref(false)
  let taskPollingInterval = null

  const taskStats = ref({
    move_total: 0,
    move_done: 0,
    delete_total: 0,
    delete_done: 0,
    rename_total: 0,
    rename_done: 0,
    keep_total: 0,
    keep_done: 0,
  })
  const taskCompletedItems = ref([])
  const taskSpeed = ref(0)
  const taskFormattedEta = ref('计算中...')

  const clearTaskPolling = () => {
    if (taskPollingInterval) {
      clearInterval(taskPollingInterval)
      taskPollingInterval = null
    }
  }

  const pollTaskStatus = async () => {
    if (!currentTaskId.value) {
      clearTaskPolling()
      return
    }

    try {
      const response = await api.getTaskStatus(currentTaskId.value)
      const data = response.data
      
      taskStatus.value = data.status
      taskProgress.value = data.current
      taskTotal.value = data.total
      taskMessage.value = data.message
      taskCurrentFile.value = data.current_file
      
      taskStats.value = {
        move_total: data.move_total || 0,
        move_done: data.move_done || 0,
        delete_total: data.delete_total || 0,
        delete_done: data.delete_done || 0,
        rename_total: data.rename_total || 0,
        rename_done: data.rename_done || 0,
        keep_total: data.keep_total || 0,
        keep_done: data.keep_done || 0,
      }
      taskCompletedItems.value = data.completed_items || []
      taskSpeed.value = data.items_per_second || 0
      taskFormattedEta.value = data.formatted_eta || '计算中...'

      emit('status-update', data)

      if (data.status === 'completed') {
        clearTaskPolling()
        isTaskRunning.value = false
        emit('completed', data.result)
      } else if (data.status === 'cancelled') {
        clearTaskPolling()
        isTaskRunning.value = false
        emit('cancelled', data.message)
      } else if (data.status === 'failed') {
        clearTaskPolling()
        isTaskRunning.value = false
        emit('failed', data.error)
      }
    } catch (err) {
      console.error('Poll task status error:', err)
    }
  }

  const startTask = (taskId) => {
    currentTaskId.value = taskId
    isTaskRunning.value = true
    clearTaskPolling()
    taskPollingInterval = setInterval(pollTaskStatus, 500)
  }

  const cancelTask = async () => {
    if (!currentTaskId.value) return
    
    try {
      await api.cancelTask(currentTaskId.value)
      emit('log', { type: 'info', message: '正在取消任务...' })
    } catch (err) {
      emit('log', { type: 'error', message: '取消任务失败' })
    }
  }

  const getTaskPercentage = () => {
    if (taskTotal.value === 0) return 0
    return Math.min(100, Math.round((taskProgress.value / taskTotal.value * 100))
  }

  const getActionLabel = (action) => {
    switch (action) {
      case 'move': return '移动'
      case 'rename_and_move': return '重命名'
      case 'delete': return '删除'
      case 'keep': return '保留'
      default: return action
    }
  }

  const getActionColor = (action) => {
    switch (action) {
      case 'move': return '#3b82f6'
      case 'rename_and_move': return '#8b5cf6'
      case 'delete': return '#ef4444'
      case 'keep': return '#10b981'
      default: return '#64748b'
    }
  }

  onBeforeUnmount(() => {
    clearTaskPolling()
  })

  return {
    currentTaskId,
    taskStatus,
    taskProgress,
    taskTotal,
    taskMessage,
    taskCurrentFile,
    isTaskRunning,
    taskStats,
    taskCompletedItems,
    taskSpeed,
    taskFormattedEta,
    startTask,
    cancelTask,
    getTaskPercentage,
    getActionLabel,
    getActionColor,
    clearTaskPolling,
  }
}

export default useTaskProgress
