<template>
  <div v-if="isVisible && previewData" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
    <div class="w-full max-w-3xl max-h-[90vh] overflow-hidden rounded-2xl border border-white/10 bg-slate-900/95 shadow-2xl flex flex-col">
      <div class="flex items-center justify-between p-4 border-b border-white/5">
        <div class="flex items-center gap-3">
          <div 
            class="p-2 rounded-lg"
            :class="previewData.safety_level === 'danger' ? 'bg-red-500/10' : previewData.safety_level === 'warning' ? 'bg-amber-500/10' : 'bg-emerald-500/10'"
          >
            <Shield 
              :size="24" 
              :class="previewData.safety_level === 'danger' ? 'text-red-400' : previewData.safety_level === 'warning' ? 'text-amber-400' : 'text-emerald-400'" 
            />
          </div>
          <div>
            <h3 class="text-lg font-bold text-slate-100">计划预检查</h3>
            <p class="text-xs text-slate-400">
              共 {{ previewData.summary?.total_actions || 0 }} 条操作 ·
              <span :class="getSafetyLevelClass(previewData.safety_level)" class="inline-flex px-2 py-0.5 rounded border text-xs ml-1">
                {{ getSafetyLevelLabel(previewData.safety_level) }}
              </span>
            </p>
          </div>
        </div>
        <button 
          type="button" 
          class="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-colors"
          @click="handleCancel"
        >
          <X :size="20" />
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-4 space-y-4">
        <div 
          v-if="previewData.safety_reasons && previewData.safety_reasons.length > 0"
          class="p-4 rounded-lg border"
          :class="previewData.safety_level === 'danger' ? 'bg-red-500/10 border-red-400/20' : 'bg-amber-500/10 border-amber-400/20'"
        >
          <div class="flex items-center gap-2 mb-2">
            <AlertTriangle 
              :size="18" 
              :class="previewData.safety_level === 'danger' ? 'text-red-400' : 'text-amber-400'" 
            />
            <p 
              class="text-sm font-medium"
              :class="previewData.safety_level === 'danger' ? 'text-red-300' : 'text-amber-300'"
            >
              安全提示
            </p>
          </div>
          <ul class="list-disc list-inside space-y-1">
            <li 
              v-for="(reason, index) in previewData.safety_reasons" 
              :key="index" 
              class="text-xs"
              :class="previewData.safety_level === 'danger' ? 'text-red-200' : 'text-amber-200'"
            >
              {{ reason }}
            </li>
          </ul>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div class="p-3 rounded-lg bg-sky-500/10 border border-sky-500/20 text-center">
            <p class="text-2xl font-bold text-sky-400">{{ previewData.summary?.move_count || 0 }}</p>
            <p class="text-xs text-slate-400">移动/重命名</p>
          </div>
          <div class="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-center">
            <p class="text-2xl font-bold text-red-400">{{ previewData.summary?.delete_count || 0 }}</p>
            <p class="text-xs text-slate-400">删除</p>
          </div>
          <div class="p-3 rounded-lg bg-slate-500/10 border border-slate-500/20 text-center">
            <p class="text-2xl font-bold text-slate-300">{{ previewData.summary?.keep_count || 0 }}</p>
            <p class="text-xs text-slate-400">保留</p>
          </div>
          <div class="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-center">
            <p class="text-2xl font-bold text-emerald-400">{{ previewData.summary?.new_folders_count || 0 }}</p>
            <p class="text-xs text-slate-400">新建文件夹</p>
          </div>
        </div>

        <div v-if="previewData.conflicts && previewData.conflicts.length > 0" class="mb-4">
          <h4 class="text-sm font-medium text-slate-300 mb-2 flex items-center gap-2">
            <AlertCircle :size="16" class="text-red-400" />
            检测到 {{ previewData.conflicts.length }} 个冲突
          </h4>
          <div class="space-y-2">
            <div v-for="(conflict, index) in previewData.conflicts" :key="index" class="p-3 rounded-lg bg-red-500/5 border border-red-400/20">
              <p class="text-xs text-red-300 font-medium">{{ conflict.type }} 冲突</p>
              <p class="text-xs text-slate-400 mt-1">{{ conflict.source }} → {{ conflict.target }}</p>
              <p v-if="conflict.message" class="text-xs text-red-200/80 mt-1">{{ conflict.message }}</p>
            </div>
          </div>
        </div>

        <div v-if="previewData.warnings && previewData.warnings.length > 0" class="mb-4">
          <h4 class="text-sm font-medium text-slate-300 mb-2 flex items-center gap-2">
            <AlertTriangle :size="16" class="text-amber-400" />
            警告 ({{ previewData.warnings.length }})
          </h4>
          <div class="space-y-2">
            <div v-for="(warning, index) in previewData.warnings" :key="index" class="p-2 rounded-lg bg-amber-500/5 border border-amber-400/20">
              <p class="text-xs text-amber-300">{{ warning }}</p>
            </div>
          </div>
        </div>

        <div v-if="previewData.move_actions && previewData.move_actions.length > 0">
          <h4 class="text-sm font-medium text-slate-300 mb-2">
            移动/重命名操作 ({{ previewData.move_actions.length }})
          </h4>
          <div class="space-y-1 max-h-40 overflow-y-auto">
            <div 
              v-for="(action, index) in previewData.move_actions" 
              :key="index" 
              class="flex items-center justify-between p-2 rounded bg-sky-500/5 border border-sky-500/10"
            >
              <span class="text-xs text-slate-300 font-mono truncate">{{ action.source }}</span>
              <ArrowRight :size="14" class="text-sky-400 flex-shrink-0 mx-2" />
              <span class="text-xs text-sky-300 font-mono truncate">{{ action.target }}</span>
            </div>
          </div>
        </div>

        <div v-if="previewData.delete_actions && previewData.delete_actions.length > 0">
          <h4 class="text-sm font-medium text-slate-300 mb-2">
            删除操作 ({{ previewData.delete_actions.length }})
          </h4>
          <div class="space-y-1 max-h-40 overflow-y-auto">
            <div 
              v-for="(action, index) in previewData.delete_actions" 
              :key="index" 
              class="flex items-center gap-2 p-2 rounded bg-red-500/5 border border-red-500/10"
            >
              <Trash2 :size="14" class="text-red-400 flex-shrink-0" />
              <span class="text-xs text-slate-300 font-mono truncate">{{ action.file }}</span>
              <span v-if="action.reason" class="text-xs text-slate-500 ml-auto">- {{ action.reason }}</span>
            </div>
          </div>
        </div>

        <div v-if="previewData.keep_actions && previewData.keep_actions.length > 0">
          <h4 class="text-sm font-medium text-slate-300 mb-2">
            保留操作 ({{ previewData.keep_actions.length }})
          </h4>
          <div class="space-y-1 max-h-40 overflow-y-auto">
            <div 
              v-for="(action, index) in previewData.keep_actions" 
              :key="index" 
              class="flex items-center gap-2 p-2 rounded bg-emerald-500/5 border border-emerald-500/10"
            >
              <Check :size="14" class="text-emerald-400 flex-shrink-0" />
              <span class="text-xs text-slate-300 font-mono truncate">{{ action.file }}</span>
              <span v-if="action.reason" class="text-xs text-slate-500 ml-auto">- {{ action.reason }}</span>
            </div>
          </div>
        </div>

        <div v-if="needConfirmation" class="mb-4 p-3 rounded-lg bg-red-500/5 border border-red-400/20">
          <label class="flex items-start gap-2 cursor-pointer">
            <input 
              type="checkbox" 
              v-model="confirmChecked"
              class="mt-0.5 rounded border-red-400 bg-transparent text-red-500 focus:ring-red-500"
            />
            <div class="text-xs">
              <p class="text-red-300 font-medium">我已知晓操作风险，确认继续执行</p>
              <p class="text-slate-400 mt-1">
                <template v-if="previewData.has_conflicts">
                  此操作包含 {{ previewData.conflicts?.length || 0 }} 个冲突，强制执行可能导致数据丢失。
                </template>
                <template v-else-if="previewData.has_warnings">
                  此操作包含 {{ previewData.warnings?.length || 0 }} 个警告，可能存在潜在风险。
                </template>
                <template v-else>
                  此操作包含删除操作，删除的文件将被移动到 .alchemy_trash 文件夹。
                </template>
              </p>
            </div>
          </label>
        </div>
      </div>

      <div class="flex items-center justify-end gap-3 p-4 border-t border-white/5">
        <button 
          type="button" 
          class="px-4 py-2 rounded-lg border border-slate-400/20 text-slate-300 bg-white/5 hover:bg-white/10 transition-colors text-sm"
          @click="handleCancel"
        >
          取消
        </button>
        <button 
          type="button" 
          class="px-6 py-2.5 rounded-lg text-sm font-medium transition-all"
          :class="[
            needConfirmation && !confirmChecked
              ? 'bg-slate-600 text-slate-400 cursor-not-allowed'
              : previewData.has_conflicts
                ? 'bg-red-500 hover:bg-red-600 text-white'
                : 'bg-sky-500 hover:bg-sky-600 text-white'
          ]"
          :disabled="needConfirmation && !confirmChecked"
          @click="handleConfirm"
        >
          {{ previewData.has_conflicts ? '强制执行' : '确认执行' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Shield, X, AlertTriangle, AlertCircle, ArrowRight, Trash2, Check } from 'lucide-vue-next'

const props = defineProps({
  isVisible: {
    type: Boolean,
    default: false,
  },
  previewData: {
    type: Object,
    default: null,
  },
  needConfirmation: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['confirm', 'cancel', 'update:confirmChecked'])

const confirmChecked = ref(false)

watch(() => props.isVisible, (newVal) => {
  if (!newVal) {
    confirmChecked.value = false
  }
})

const getSafetyLevelClass = (level) => {
  switch (level) {
    case 'danger':
      return 'text-red-400 bg-red-500/10 border-red-400/20'
    case 'warning':
      return 'text-amber-400 bg-amber-500/10 border-amber-400/20'
    default:
      return 'text-emerald-400 bg-emerald-500/10 border-emerald-400/20'
  }
}

const getSafetyLevelLabel = (level) => {
  switch (level) {
    case 'danger':
      return '高风险'
    case 'warning':
      return '中风险'
    default:
      return '安全'
  }
}

const handleConfirm = () => {
  emit('confirm', { confirmChecked: confirmChecked.value })
}

const handleCancel = () => {
  emit('cancel')
}
</script>
