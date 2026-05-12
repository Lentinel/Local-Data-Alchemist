import axios from 'axios'

export const api = {
  getTaskStatus: (taskId) => 
    axios.get(`/api/task_status/${taskId}`),

  cancelTask: (taskId) => 
    axios.post('/api/cancel_task', { task_id: taskId }),

  selectFolder: () =>
    axios.get('/api/select_folder'),

  llmHealth: (checkConnection = false) =>
    axios.get('/api/llm_health', {
      params: checkConnection ? { check_connection: true } : undefined,
    }),

  lockFolder: (targetPath) => 
    axios.post('/api/lock_folder', { target_path: targetPath }),

  generatePlan: (targetPath) => 
    axios.post('/api/generate_plan', { target_path: targetPath }),

  previewPlan: (targetPath, plan) => 
    axios.post('/api/preview_plan', { target_path: targetPath, plan }),

  startExecuteTask: (targetPath, plan) => 
    axios.post('/api/start_execute_task', { target_path: targetPath, plan }),

  executePlan: (targetPath, plan) => 
    axios.post('/api/execute_plan', { target_path: targetPath, plan }),

  undoPlan: (targetPath) => 
    axios.post('/api/undo_plan', { target_path: targetPath }),

  previewFile: (targetPath, filePath) => 
    axios.post('/api/preview_file', { target_path: targetPath, file_path: filePath }),

  listHistory: (targetPath) => 
    axios.post('/api/list_history', { target_path: targetPath }),

  getHistory: (targetPath, historyId) => 
    axios.post('/api/get_history', { target_path: targetPath, history_id: historyId }),

  detectDuplicates: (targetPath, fastMode = true) => 
    axios.post('/api/detect_duplicates', { target_path: targetPath, fast_mode: fastMode }),

  keepDuplicate: (targetPath, keepFile, duplicateFiles) => 
    axios.post('/api/keep_duplicate', { 
      target_path: targetPath, 
      keep_file: keepFile, 
      duplicate_files: duplicateFiles 
    }),

  listTemplates: () => 
    axios.get('/api/list_templates'),

  getTemplate: (templateId) => 
    axios.post('/api/get_template', { template_id: templateId }),

  applyTemplate: (targetPath, templateId) => 
    axios.post('/api/apply_template', { target_path: targetPath, template_id: templateId }),

  saveTemplate: (template) => 
    axios.post('/api/save_template', { template }),

  deleteTemplate: (templateId) => 
    axios.post('/api/delete_template', { template_id: templateId }),

  renamePreview: (targetPath, selectedFiles, rules) => 
    axios.post('/api/rename_preview', { 
      target_path: targetPath,
      selected_files: selectedFiles, 
      rules 
    }),

  renameExecute: (targetPath, renamePlan) => 
    axios.post('/api/rename_execute', { 
      target_path: targetPath,
      rename_plan: renamePlan 
    }),

  dashboardStats: (targetPath) =>
    axios.post('/api/dashboard_stats', { target_path: targetPath }),

  directoryTree: (targetPath) =>
    axios.post('/api/directory_tree', { target_path: targetPath }),

  analyzePlan: (targetPath, plan) =>
    axios.post('/api/analyze_plan', { target_path: targetPath, plan }),

  selectiveUndo: (targetPath, files) =>
    axios.post('/api/selective_undo', { target_path: targetPath, files }),

  exportPdf: (targetPath) =>
    axios.post('/api/export_pdf', { target_path: targetPath }, { responseType: 'blob' }),

  exportExcel: (targetPath) =>
    axios.post('/api/export_excel', { target_path: targetPath }, { responseType: 'blob' }),

  multiScan: (targetPaths) => 
    axios.post('/api/multi_scan', { target_paths: targetPaths }),

  multiGeneratePlan: (targetPaths) => 
    axios.post('/api/multi_generate_plan', { target_paths: targetPaths }),
}

export default api
