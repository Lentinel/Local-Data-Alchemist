import { ref } from 'vue'
import api from '../api'

export function useDashboard(options = {}) {
  const { onLog, extractErrorMessage } = options

  const isShowingDashboard = ref(false)
  const isLoadingDashboard = ref(false)
  const dashboardStats = ref(null)
  const dashboardError = ref(null)

  const showDashboard = async (targetPath) => {
    if (!targetPath) {
      dashboardError.value = '请先锁定一个目录'
      if (onLog) {
        onLog({ type: 'warning', message: dashboardError.value })
      }
      return
    }

    isShowingDashboard.value = true
    await loadDashboardStats(targetPath)
  }

  const hideDashboard = () => {
    isShowingDashboard.value = false
    dashboardError.value = null
  }

  const loadDashboardStats = async (targetPath) => {
    if (!targetPath) return

    isLoadingDashboard.value = true
    dashboardError.value = null
    dashboardStats.value = null

    try {
      if (onLog) {
        onLog({ type: 'info', message: '正在加载仪表盘统计数据...' })
      }

      const response = await api.dashboardStats(targetPath)
      dashboardStats.value = response.data

      if (onLog) {
        onLog({ type: 'info', message: '仪表盘统计数据加载完成' })
      }
    } catch (err) {
      dashboardError.value = extractErrorMessage ? extractErrorMessage(err) : '加载统计数据失败'
      if (onLog) {
        onLog({ type: 'error', message: `加载统计数据失败: ${dashboardError.value}` })
      }
      console.error('Load dashboard stats error:', err)
    } finally {
      isLoadingDashboard.value = false
    }
  }

  const refreshDashboard = async (targetPath) => {
    await loadDashboardStats(targetPath)
  }

  return {
    isShowingDashboard,
    isLoadingDashboard,
    dashboardStats,
    dashboardError,
    showDashboard,
    hideDashboard,
    loadDashboardStats,
    refreshDashboard,
  }
}

export default useDashboard
