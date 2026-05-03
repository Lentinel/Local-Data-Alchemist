<template>
  <div v-if="isVisible" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
    <div class="relative w-full max-w-6xl max-h-[90vh] overflow-hidden rounded-lg glass border border-white/10 flex flex-col">
      <div class="flex items-center justify-between p-4 border-b border-white/10">
        <div class="flex items-center gap-3">
          <Sparkles :size="24" class="text-fuchsia-400" />
          <div>
            <p class="font-medium text-slate-100">
              {{ isEditing ? '编辑模板' : '规则模板库' }}
            </p>
            <p class="text-xs text-slate-400 font-mono">
              <template v-if="isEditing">
                {{ editingTemplate?.name || '新建模板' }} · {{ editingTemplate?.rules?.length || 0 }} 条规则
              </template>
              <template v-else>
                共 {{ templates.length }} 个模板 · {{ builtinCount }} 个内置
              </template>
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-if="!isEditing"
            type="button"
            class="px-3 py-1.5 rounded-lg border border-fuchsia-400/30 bg-fuchsia-500/10 hover:bg-fuchsia-500/20 transition-colors text-fuchsia-100 text-xs"
            :disabled="isLoading"
            @click="handleCreateNew"
          >
            新建模板
          </button>
          <button
            v-if="isEditing"
            type="button"
            class="px-3 py-1.5 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-slate-200 text-xs"
            @click="handleCancelEdit"
          >
            取消
          </button>
          <button
            v-if="isEditing"
            type="button"
            class="px-3 py-1.5 rounded-lg border border-fuchsia-400/30 bg-fuchsia-500/10 hover:bg-fuchsia-500/20 transition-colors text-fuchsia-100 text-xs"
            :disabled="!editingTemplate?.name"
            @click="handleSave"
          >
            保存模板
          </button>
          <button
            type="button"
            class="p-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors"
            @click="handleClose"
            title="关闭"
          >
            <X :size="20" class="text-slate-300" />
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-auto p-4">
        <div v-if="error" class="flex items-center gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
          <AlertCircle :size="20" />
          <p>{{ error }}</p>
        </div>

        <div v-else-if="isLoading" class="flex items-center justify-center h-64">
          <div class="flex items-center gap-3 text-slate-400">
            <Loader2 :size="24" class="animate-spin" />
            <p>正在加载模板...</p>
          </div>
        </div>

        <div v-else-if="isEditing">
          <div class="max-w-3xl mx-auto space-y-6">
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">模板名称</label>
                <input
                  v-model="editingTemplate.name"
                  type="text"
                  class="w-full px-3 py-2 rounded-lg bg-slate-900/50 border border-white/10 text-slate-200 focus:outline-none focus:border-sky-500"
                  placeholder="输入模板名称"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">描述</label>
                <textarea
                  v-model="editingTemplate.description"
                  class="w-full px-3 py-2 rounded-lg bg-slate-900/50 border border-white/10 text-slate-200 focus:outline-none focus:border-sky-500"
                  placeholder="输入模板描述（可选）"
                  rows="2"
                ></textarea>
              </div>
            </div>

            <div>
              <div class="flex items-center justify-between mb-3">
                <label class="text-sm font-medium text-slate-300">规则列表</label>
                <button
                  type="button"
                  class="px-3 py-1 rounded text-xs bg-sky-500/10 border border-sky-500/20 text-sky-300 hover:bg-sky-500/20"
                  @click="handleAddRule"
                >
                  + 添加规则
                </button>
              </div>
              
              <div class="space-y-3">
                <div
                  v-for="(rule, index) in editingTemplate.rules"
                  :key="index"
                  class="p-3 rounded-lg bg-slate-900/50 border border-white/5 space-y-3"
                >
                  <div class="flex items-center justify-between">
                    <span class="text-xs text-slate-400">规则 {{ index + 1 }}</span>
                    <button
                      v-if="editingTemplate.rules.length > 1"
                      type="button"
                      class="p-1 rounded text-red-400 hover:bg-red-500/10"
                      @click="handleRemoveRule(index)"
                    >
                      <Trash2 :size="14" />
                    </button>
                  </div>
                  
                  <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
                    <div>
                      <label class="block text-xs text-slate-500 mb-1">匹配扩展名（逗号分隔）</label>
                      <input
                        v-model="ruleMatchExtensions"
                        type="text"
                        class="w-full px-2 py-1.5 rounded bg-slate-800 border border-white/10 text-slate-200 text-xs focus:outline-none focus:border-sky-500"
                        placeholder="jpg, png, gif"
                      />
                    </div>
                    <div>
                      <label class="block text-xs text-slate-500 mb-1">匹配模式（正则）</label>
                      <input
                        v-model="rule.match_pattern"
                        type="text"
                        class="w-full px-2 py-1.5 rounded bg-slate-800 border border-white/10 text-slate-200 text-xs focus:outline-none focus:border-sky-500"
                        placeholder=".*report.*"
                      />
                    </div>
                    <div>
                      <label class="block text-xs text-slate-500 mb-1">分类</label>
                      <input
                        v-model="rule.category"
                        type="text"
                        class="w-full px-2 py-1.5 rounded bg-slate-800 border border-white/10 text-slate-200 text-xs focus:outline-none focus:border-sky-500"
                        placeholder="images"
                      />
                    </div>
                    <div>
                      <label class="block text-xs text-slate-500 mb-1">操作类型</label>
                      <select
                        v-model="rule.action"
                        class="w-full px-2 py-1.5 rounded bg-slate-800 border border-white/10 text-slate-200 text-xs focus:outline-none focus:border-sky-500"
                      >
                        <option value="move">移动</option>
                        <option value="keep">保留</option>
                        <option value="delete">删除</option>
                      </select>
                    </div>
                    <div class="col-span-2">
                      <label class="block text-xs text-slate-500 mb-1">目标路径</label>
                      <input
                        v-model="rule.target_path"
                        type="text"
                        class="w-full px-2 py-1.5 rounded bg-slate-800 border border-white/10 text-slate-200 text-xs focus:outline-none focus:border-sky-500"
                        placeholder="images/photos"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="templates.length === 0" class="flex flex-col items-center justify-center h-64 text-slate-400">
          <Sparkles :size="48" class="mb-3 text-slate-600" />
          <p class="text-lg font-medium">暂无模板</p>
          <p class="text-sm mt-1">点击"新建模板"创建自定义规则模板</p>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            v-for="(template, index) in templates"
            :key="template.id"
            class="p-4 rounded-lg glass hover:bg-white/10 transition-colors cursor-pointer border"
            :class="template.is_builtin ? 'border-cyan-500/20' : 'border-white/5'"
            @click="handleSelectTemplate(template)"
          >
            <div class="flex items-start justify-between mb-2">
              <div class="flex items-center gap-2">
                <span 
                  class="px-2 py-0.5 rounded text-xs font-medium"
                  :class="template.is_builtin 
                    ? 'text-cyan-300 bg-cyan-500/10 border border-cyan-500/20' 
                    : 'text-amber-300 bg-amber-500/10 border border-amber-500/20'"
                >
                  {{ template.is_builtin ? '内置' : '自定义' }}
                </span>
                <h3 class="font-medium text-slate-200">{{ template.name }}</h3>
              </div>
              <div class="flex items-center gap-1">
                <button
                  v-if="!template.is_builtin"
                  type="button"
                  class="p-1.5 rounded text-slate-400 hover:text-sky-300 hover:bg-sky-500/10"
                  @click.stop="handleEditTemplate(template)"
                  title="编辑"
                >
                  <Settings :size="14" />
                </button>
                <button
                  v-if="!template.is_builtin"
                  type="button"
                  class="p-1.5 rounded text-slate-400 hover:text-red-300 hover:bg-red-500/10"
                  @click.stop="handleDeleteTemplate(template.id)"
                  title="删除"
                >
                  <Trash2 :size="14" />
                </button>
              </div>
            </div>
            
            <p v-if="template.description" class="text-xs text-slate-400 mb-2">
              {{ template.description }}
            </p>
            
            <p class="text-xs text-slate-500">
              {{ template.rules?.length || 0 }} 条规则
            </p>
          </div>
        </div>
      </div>

      <div class="p-4 border-t border-white/10 flex items-center justify-end">
        <button
          type="button"
          class="px-4 py-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-slate-200 text-sm"
          @click="handleClose"
        >
          关闭
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Sparkles, X, AlertCircle, Loader2, Settings, Trash2 } from 'lucide-vue-next'

const props = defineProps({
  isVisible: {
    type: Boolean,
    default: false,
  },
  isLoading: {
    type: Boolean,
    default: false,
  },
  templates: {
    type: Array,
    default: () => [],
  },
  selectedTemplate: {
    type: Object,
    default: null,
  },
  isEditing: {
    type: Boolean,
    default: false,
  },
  editingTemplate: {
    type: Object,
    default: null,
  },
  error: {
    type: String,
    default: null,
  },
})

const emit = defineEmits([
  'close', 
  'select', 
  'create-new', 
  'edit', 
  'delete', 
  'save', 
  'cancel-edit',
  'add-rule',
  'remove-rule'
])

const builtinCount = computed(() => 
  props.templates.filter(t => t.is_builtin).length
)

const ruleMatchExtensions = computed({
  get: () => {
    if (!props.editingTemplate?.rules) return ''
    return props.editingTemplate.rules
      .map(r => r.match_extensions?.join(', ') || '')
      .join('')
  },
  set: (val) => {
    if (props.editingTemplate?.rules && props.editingTemplate.rules.length > 0) {
      props.editingTemplate.rules[0].match_extensions = val
        .split(',')
        .map(s => s.trim())
        .filter(s => s)
    }
  }
})

const handleClose = () => {
  emit('close')
}

const handleSelectTemplate = (template) => {
  emit('select', template)
}

const handleCreateNew = () => {
  emit('create-new')
}

const handleEditTemplate = (template) => {
  emit('edit', template)
}

const handleDeleteTemplate = (templateId) => {
  emit('delete', templateId)
}

const handleSave = () => {
  emit('save')
}

const handleCancelEdit = () => {
  emit('cancel-edit')
}

const handleAddRule = () => {
  emit('add-rule')
}

const handleRemoveRule = (index) => {
  emit('remove-rule', index)
}
</script>
