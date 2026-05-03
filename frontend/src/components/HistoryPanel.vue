<template>
  <div v-if="isVisible" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
    <div class="relative w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-lg glass border border-white/10 flex flex-col">
      <div class="flex items-center justify-between p-4 border-b border-white/10">
        <div class="flex items-center gap-3">
          <Clock :size="24" class="text-sky-300" />
          <div>
            <p class="font-medium text-slate-100">
              {{ selectedItem ? '历史记录详情' : '操作历史记录' }}
            </p>
            <p v-if="!selectedItem" class="text-xs text-slate-400 font-mono">
              共 {{ historyList.length }} 条记录
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-if="selectedItem"
            type="button"
            class="px-3 py-1.5 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors text-slate-200 text-xs"
            @click="handleBack"
          >
            返回列表
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
            <p>正在加载历史记录...</p>
          </div>
        </div>

        <div v-else-if="selectedItem" class="w-full space-y-4">
          <div class="p-4 rounded-lg bg-slate-950/70 border border-white/10 space-y-3">
            <div class="flex items-center gap-2">
              <span 
                :class="[
                  'px-2 py-0.5 rounded-lg border text-xs font-semibold',
                  getTypeClass(selectedItem.type)
                ]"
              >
                {{ getTypeLabel(selectedItem.type) }}
              </span>
              <span class="text-xs text-slate-400 font-mono">
                {{ formatDateTimeFn ? formatDateTimeFn(selectedItem.created_at) : selectedItem.created_at }}
              </span>
            </div>
            <p class="text-xs text-slate-400 font-mono">
              目标目录：{{ selectedItem.target_path }}
            </p>
            <p class="text-xs text-slate-400 font-mono">
              历史记录ID：{{ selectedItem.id }}
            </p>
          </div>

          <div v-if="selectedItem.results && selectedItem.results.length > 0">
            <p class="text-sm text-slate-400 font-semibold mb-2">操作结果（共 {{ selectedItem.results.length }} 条）</p>
            <div class="space-y-2 max-h-[40vh] overflow-auto">
              <div
                v-for="(result, index) in selectedItem.results"
                :key="`${result.file}-${index}`"
                class="p-3 rounded-lg bg-slate-950/50 border border-white/5 space-y-1"
              >
                <div class="flex items-center gap-2">
                  <p class="text-sm text-slate-200 font-medium truncate">{{ result.file }}</p>
                  <span 
                    :class="[
                      'px-2 py-0.5 rounded-lg border text-xs',
                      getActionTone(result.action)
                    ]"
                  >
                    {{ getActionLabel(result.action) }}
                  </span>
                </div>
                <p v-if="result.new_path" class="text-xs text-slate-400 font-mono">
                  {{ result.original_path }} → {{ result.new_path }}
                </p>
                <p class="text-xs text-slate-400 font-mono">
                  状态：{{ result.status }}
                </p>
              </div>
            </div>
          </div>

          <div v-else class="p-4 rounded-lg bg-slate-950/50 border border-white/5 text-center text-slate-400">
            <p>暂无操作结果</p>
          </div>
        </div>

        <div v-else-if="historyList.length > 0" class="w-full space-y-3">
          <div
            v-for="(item, index) in historyList"
            :key="item.id"
            class="p-4 rounded-lg glass hover:bg-white/10 transition-colors cursor-pointer"
            @click="handleSelectItem(item)"
          >
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center gap-2">
                <span 
                  :class="[
                    'px-2 py-0.5 rounded-lg border text-xs font-semibold',
                    getTypeClass(item.type)
                  ]"
                >
                  {{ getTypeLabel(item.type) }}
                </span>
                <span class="text-xs text-slate-400 font-mono">
                  {{ formatDateTimeFn ? formatDateTimeFn(item.created_at) : item.created_at }}
                </span>
              </div>
              <span class="text-xs text-slate-400 font-mono">
                {{ item.results_count }} 条操作
              </span>
            </div>
            <p class="text-xs text-slate-400 font-mono truncate">
              目标目录：{{ item.target_path }}
            </p>
          </div>
        </div>

        <div v-else class="flex flex-col items-center justify-center h-64 text-slate-400">
          <Clock :size="48" class="mb-3 text-slate-600" />
          <p class="text-lg font-medium">暂无操作历史记录</p>
          <p class="text-sm mt-1">执行文件整理计划后，历史记录将显示在这里</p>
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
import { Clock, X, AlertCircle, Loader2 } from 'lucide-vue-next'

const props = defineProps({
  isVisible: {
    type: Boolean,
    default: false,
  },
  historyList: {
    type: Array,
    default: () => [],
  },
  selectedItem: {
    type: Object,
    default: null,
  },
  isLoading: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: null,
  },
  formatDateTimeFn: {
    type: Function,
    default: null,
  },
})

const emit = defineEmits(['close', 'select', 'back'])

const getTypeClass = (type) => {
  switch (type) {
    case 'execute':
      return 'text-emerald-300 bg-emerald-500/10 border-emerald-400/20'
    case 'deduplicate':
      return 'text-amber-300 bg-amber-500/10 border-amber-400/20'
    case 'rename':
      return 'text-sky-300 bg-sky-500/10 border-sky-400/20'
    default:
      return 'text-sky-300 bg-sky-500/10 border-sky-400/20'
  }
}

const getTypeLabel = (type) => {
  switch (type) {
    case 'execute':
      return '执行计划'
    case 'deduplicate':
      return '去重操作'
    case 'rename':
      return '重命名操作'
    default:
      return '回滚操作'
  }
}

const getActionTone = (action) => {
  switch (action) {
    case 'move':
      return 'text-sky-300 bg-sky-500/10 border-sky-400/20'
    case 'rename_and_move':
      return 'text-fuchsia-300 bg-fuchsia-500/10 border-fuchsia-400/20'
    case 'delete':
      return 'text-red-300 bg-red-500/10 border-red-400/20'
    case 'keep':
    default:
      return 'text-slate-300 bg-slate-500/10 border-slate-400/20'
  }
}

const getActionLabel = (action) => {
  switch (action) {
    case 'move':
      return '移动'
    case 'rename_and_move':
      return '重命名移动'
    case 'delete':
      return '删除'
    case 'keep':
      return '保留'
    default:
      return action
  }
}

const handleClose = () => {
  emit('close')
}

const handleSelectItem = (item) => {
  emit('select', item)
}

const handleBack = () => {
  emit('back')
}
</script>
