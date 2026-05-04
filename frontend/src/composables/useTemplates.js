import { ref, computed } from 'vue'
import api from '../api'

export function useTemplates(options = {}) {
  const { onLog, extractErrorMessage } = options

  const isShowingTemplates = ref(false)
  const isLoadingTemplates = ref(false)
  const isApplyingTemplate = ref(false)
  const templates = ref([])
  const selectedTemplate = ref(null)
  const templateError = ref(null)
  const templateResult = ref(null)

  const isEditingTemplate = ref(false)
  const editingTemplate = ref(null)
  const editingRule = ref(null)

  const builtinTemplates = computed(() => 
    templates.value.filter(t => t.is_builtin)
  )
  const customTemplates = computed(() => 
    templates.value.filter(t => !t.is_builtin)
  )
  const totalTemplates = computed(() => templates.value.length)

  const listTemplates = async () => {
    isLoadingTemplates.value = true
    templateError.value = null

    try {
      const response = await api.listTemplates()
      templates.value = response.data.templates || []

      if (onLog) {
        onLog({ type: 'info', message: `已加载 ${templates.value.length} 个模板` })
      }
    } catch (err) {
      templateError.value = extractErrorMessage ? extractErrorMessage(err) : '加载模板列表失败'
      if (onLog) {
        onLog({ type: 'error', message: `加载模板列表失败: ${templateError.value}` })
      }
      console.error('List templates error:', err)
    } finally {
      isLoadingTemplates.value = false
    }
  }

  const showTemplates = async () => {
    isShowingTemplates.value = true
    if (templates.value.length === 0) {
      await listTemplates()
    }
  }

  const hideTemplates = () => {
    isShowingTemplates.value = false
    templateError.value = null
    templateResult.value = null
    cancelEditTemplate()
  }

  const applyTemplate = async (targetPath, templateId) => {
    if (!targetPath) {
      templateError.value = '请先锁定一个目录'
      return null
    }

    isApplyingTemplate.value = true
    templateError.value = null
    templateResult.value = null

    try {
      if (onLog) {
        onLog({ type: 'info', message: '正在应用模板...' })
      }

      const response = await api.applyTemplate(targetPath, templateId)
      templateResult.value = response.data

      if (onLog) {
        onLog({ type: 'success', message: `模板应用成功，生成了 ${response.data.plan?.length || 0} 条规则` })
      }

      return response.data
    } catch (err) {
      templateError.value = extractErrorMessage ? extractErrorMessage(err) : '应用模板失败'
      if (onLog) {
        onLog({ type: 'error', message: `应用模板失败: ${templateError.value}` })
      }
      console.error('Apply template error:', err)
      return null
    } finally {
      isApplyingTemplate.value = false
    }
  }

  const selectTemplate = (template) => {
    selectedTemplate.value = template
  }

  const createNewTemplate = () => {
    isEditingTemplate.value = true
    editingTemplate.value = {
      name: '',
      description: '',
      is_builtin: false,
      rules: [
        { match_extensions: [], match_pattern: '', category: '', action: 'move', target_path: '' }
      ],
    }
    editingRule.value = null
  }

  const editTemplate = (template) => {
    if (template.is_builtin) {
      if (onLog) {
        onLog({ type: 'warning', message: '内置模板不可编辑' })
      }
      return
    }
    isEditingTemplate.value = true
    editingTemplate.value = JSON.parse(JSON.stringify(template))
    editingRule.value = null
  }

  const cancelEditTemplate = () => {
    isEditingTemplate.value = false
    editingTemplate.value = null
    editingRule.value = null
  }

  const addRule = () => {
    if (!editingTemplate.value) return
    editingTemplate.value.rules.push({
      match_extensions: [],
      match_pattern: '',
      category: '',
      action: 'move',
      target_path: '',
    })
  }

  const removeRule = (index) => {
    if (!editingTemplate.value) return
    if (editingTemplate.value.rules.length > 1) {
      editingTemplate.value.rules.splice(index, 1)
    }
  }

  const saveTemplate = async () => {
    if (!editingTemplate.value) return
    if (!editingTemplate.value.name.trim()) {
      templateError.value = '请输入模板名称'
      return null
    }

    isLoadingTemplates.value = true
    templateError.value = null

    try {
      const templateData = {
        ...editingTemplate.value,
        name: editingTemplate.value.name.trim(),
        description: editingTemplate.value.description?.trim() || '',
        rules: editingTemplate.value.rules.filter(r => 
          (r.match_extensions && r.match_extensions.length > 0) || 
          (r.match_pattern && r.match_pattern.trim())
        ),
      }

      const response = await api.saveTemplate(templateData)

      if (onLog) {
        onLog({ type: 'success', message: `模板 "${editingTemplate.value.name}" 保存成功` })
      }

      await listTemplates()
      cancelEditTemplate()

      return response.data
    } catch (err) {
      templateError.value = extractErrorMessage ? extractErrorMessage(err) : '保存模板失败'
      if (onLog) {
        onLog({ type: 'error', message: `保存模板失败: ${templateError.value}` })
      }
      console.error('Save template error:', err)
      return null
    } finally {
      isLoadingTemplates.value = false
    }
  }

  const deleteTemplate = async (templateId) => {
    if (!confirm('确定要删除此模板吗？此操作不可撤销。')) {
      return
    }

    isLoadingTemplates.value = true
    templateError.value = null

    try {
      await api.deleteTemplate(templateId)

      if (onLog) {
        onLog({ type: 'info', message: '模板已删除' })
      }

      await listTemplates()
    } catch (err) {
      templateError.value = extractErrorMessage ? extractErrorMessage(err) : '删除模板失败'
      if (onLog) {
        onLog({ type: 'error', message: `删除模板失败: ${templateError.value}` })
      }
      console.error('Delete template error:', err)
    } finally {
      isLoadingTemplates.value = false
    }
  }

  return {
    isShowingTemplates,
    isLoadingTemplates,
    isApplyingTemplate,
    templates,
    selectedTemplate,
    templateError,
    templateResult,
    isEditingTemplate,
    editingTemplate,
    editingRule,
    builtinTemplates,
    customTemplates,
    totalTemplates,
    listTemplates,
    showTemplates,
    hideTemplates,
    applyTemplate,
    selectTemplate,
    createNewTemplate,
    editTemplate,
    cancelEditTemplate,
    addRule,
    removeRule,
    saveTemplate,
    deleteTemplate,
  }
}

export default useTemplates
