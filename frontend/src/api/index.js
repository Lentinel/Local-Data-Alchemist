import axios from 'axios'

export const api = {
  getTaskStatus: (taskId) => 
    axios.get(`/api/task_status/${taskId}`),

  cancelTask: (taskId) => 
    axios.post('/api/cancel_task', { task_id: taskId }),

  selectFolder: () => 
    axios.get('/api/select_folder'),

  lockFolder: (targetPath) => 
    axios.post('/api/lock_folder', { target_path: targetPath }),

  generatePlan: (targetPath, files, analysis) => 
    axios.post('/api/generate_plan', { target_path: targetPath, files, analysis }),

  previewPlan: (targetPath, plan) => 
    axios.post('/api/preview_plan', { target_path: targetPath, plan }),

  startExecuteTask: (targetPath, plan) => 
    axios.post('/api/start_execute_task', { target_path: targetPath, plan }),

  undoPlan: (targetPath) => 
    axios.post('/api/undo_plan', { target_path: targetPath }),

  previewFile: (targetPath, filePath) => 
    axios.post('/api/preview_file', { target_path: targetPath, file_path: filePath }),

  listHistory: (targetPath) => 
    axios.post('/api/list_history', { target_path: targetPath }),

  getHistory: (targetPath, historyId) => 
    axios.post('/api/get_history', { target_path: targetPath, history_id: historyId }),

  detectDuplicates: (targetPath) => 
    axios.post('/api/detect_duplicates', { target_path: targetPath }),

  keepDuplicate: (targetPath, hash, index) => 
    axios.post('/api/keep_duplicate', { target_path: targetPath, hash, index }),

  listTemplates: () => 
    axios.get('/api/list_templates'),

  applyTemplate: (targetPath, templateId, files) => 
    axios.post('/api/apply_template', { target_path: targetPath, template_id: templateId, files }),

  saveTemplate: (template) => 
    axios.post('/api/save_template', template),

  deleteTemplate: (templateId) => 
    axios.post('/api/delete_template', { template_id: templateId }),

  renamePreview: (selectedFiles, rules) => 
    axios.post('/api/rename_preview', { selected_files: selectedFiles, rules }),

  renameExecute: (selectedFiles, rules) => 
    axios.post('/api/rename_execute', { selected_files: selectedFiles, rules }),

  listFiles: (targetPath) => 
    axios.post('/api/list_files', { target_path: targetPath }),

  dashboardStats: (targetPath) => 
    axios.post('/api/dashboard_stats', { target_path: targetPath }),

  multiScan: (targets) => 
    axios.post('/api/multi_scan', { targets }),

  multiGeneratePlan: (scanResults) => 
    axios.post('/api/multi_generate_plan', { scan_results: scanResults }),
}

export default api
