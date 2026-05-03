import { reactive, computed } from 'vue'

const state = reactive({
  targetPath: null,
  files: [],
  analysis: null,
  actionPlan: [],
  executionResult: null,
  undoMessage: null,
  error: null,
  loadingTipIndex: 0,
  animatedFinancialTotal: 0,
  manualTargetPath: 'C:\\Users\\Lentinel\\Desktop\\trae\\sample_messy_folder',
  isSelectingFolder: false,
  isGeneratingPlan: false,
  isExecutingPlan: false,
  isUndoing: false,
  consoleLogs: [],
  copyToast: null,
})

const getters = {
  totalFiles: computed(() => state.files.length),
  totalSize: computed(() => {
    return state.files.reduce((sum, file) => sum + (file.size || 0), 0)
  }),
  categories: computed(() => {
    const cats = new Set()
    state.files.forEach(file => {
      if (file.category) cats.add(file.category)
    })
    return ['all', ...Array.from(cats)]
  }),
  hasActivePlan: computed(() => state.actionPlan && state.actionPlan.length > 0),
  canUndo: computed(() => !state.isUndoing && state.executionResult !== null),
}

const actions = {
  reset: () => {
    state.files = []
    state.analysis = null
    state.actionPlan = []
    state.executionResult = null
    state.undoMessage = null
    state.error = null
  },

  setTargetPath: (path) => {
    state.targetPath = path
  },

  setFiles: (files) => {
    state.files = files
  },

  setAnalysis: (analysis) => {
    state.analysis = analysis
  },

  setActionPlan: (plan) => {
    state.actionPlan = plan
  },

  setExecutionResult: (result) => {
    state.executionResult = result
  },

  setUndoMessage: (message) => {
    state.undoMessage = message
  },

  setError: (error) => {
    state.error = error
  },

  clearError: () => {
    state.error = null
  },

  setSelectingFolder: (value) => {
    state.isSelectingFolder = value
  },

  setGeneratingPlan: (value) => {
    state.isGeneratingPlan = value
  },

  setExecutingPlan: (value) => {
    state.isExecutingPlan = value
  },

  setUndoing: (value) => {
    state.isUndoing = value
  },

  addLog: (log) => {
    state.consoleLogs.push(log)
  },

  clearLogs: () => {
    state.consoleLogs = []
  },

  setCopyToast: (value) => {
    state.copyToast = value
  },
}

export const useAppStore = () => ({
  state,
  getters,
  actions,
})

export default useAppStore
