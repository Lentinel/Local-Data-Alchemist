<template>
  <div v-if="isRunning && total > 0" class="space-y-4">
    <div class="p-5 rounded-xl border border-sky-400/20 bg-gradient-to-br from-sky-500/10 to-cyan-500/5">
      <div class="flex flex-col md:flex-row items-start md:items-center gap-6">
        <div class="relative w-28 h-28 flex-shrink-0">
          <svg class="w-28 h-28 transform -rotate-90" viewBox="0 0 120 120">
            <circle
              cx="60"
              cy="60"
              r="52"
              fill="none"
              stroke="#1e293b"
              stroke-width="12"
            />
            <circle
              cx="60"
              cy="60"
              r="52"
              fill="none"
              stroke="url(#progressGradient)"
              stroke-width="12"
              stroke-linecap="round"
              :stroke-dasharray="326.73"
              :stroke-dashoffset="326.73 - (326.73 * percentage / 100)"
              class="transition-all duration-500"
            />
            <defs>
              <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#0ea5e9" />
                <stop offset="100%" stop-color="#22d3ee" />
              </linearGradient>
            </defs>
          </svg>
          <div class="absolute inset-0 flex flex-col items-center justify-center">
            <span class="text-2xl font-black text-sky-400">{{ percentage }}%</span>
            <span class="text-xs text-slate-400 mt-1">{{ current }}/{{ total }}</span>
          </div>
        </div>

        <div class="flex-1 w-full space-y-3">
          <div class="flex items-center gap-2">
            <Loader2 :size="20" class="animate-spin text-sky-400" />
            <span class="text-base font-semibold text-sky-200">{{ message }}</span>
          </div>

          <div class="w-full h-3 bg-slate-800/80 rounded-full overflow-hidden">
            <div
              class="h-full bg-gradient-to-r from-sky-500 via-cyan-400 to-teal-400 rounded-full transition-all duration-300 relative overflow-hidden"
              :style="{ width: `${percentage}%` }"
            >
              <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-pulse"></div>
            </div>
          </div>

          <div v-if="currentFile" class="flex items-center gap-2">
            <FileText :size="16" class="text-sky-400 flex-shrink-0" />
            <span class="text-sm text-slate-300 font-mono truncate max-w-md">{{ currentFile }}</span>
          </div>

          <div class="flex items-center gap-4 text-xs">
            <div v-if="speed > 0" class="flex items-center gap-1.5 text-slate-400">
              <span class="text-slate-500">⚡ 速度:</span>
              <span class="text-sky-300 font-medium">{{ speed.toFixed(1) }} 个/秒</span>
            </div>
            <div class="flex items-center gap-1.5 text-slate-400">
              <span class="text-slate-500">⏱ 剩余:</span>
              <span class="text-cyan-300 font-medium">{{ formattedEta }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div
        v-if="stats.move_total > 0"
        class="p-3 rounded-lg border border-blue-500/20 bg-blue-500/5 space-y-2"
      >
        <div class="flex items-center justify-between">
          <span class="text-xs text-slate-400">📂 移动文件</span>
          <span class="text-xs font-mono text-blue-400">{{ stats.move_done }}/{{ stats.move_total }}</span>
        </div>
        <div class="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div
            class="h-full bg-blue-500 rounded-full transition-all duration-300"
            :style="{ width: stats.move_total > 0 ? `${(stats.move_done / stats.move_total) * 100}%` : '0%' }"
          ></div>
        </div>
      </div>

      <div
        v-if="stats.rename_total > 0"
        class="p-3 rounded-lg border border-purple-500/20 bg-purple-500/5 space-y-2"
      >
        <div class="flex items-center justify-between">
          <span class="text-xs text-slate-400">✏️ 重命名</span>
          <span class="text-xs font-mono text-purple-400">{{ stats.rename_done }}/{{ stats.rename_total }}</span>
        </div>
        <div class="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div
            class="h-full bg-purple-500 rounded-full transition-all duration-300"
            :style="{ width: stats.rename_total > 0 ? `${(stats.rename_done / stats.rename_total) * 100}%` : '0%' }"
          ></div>
        </div>
      </div>

      <div
        v-if="stats.delete_total > 0"
        class="p-3 rounded-lg border border-red-500/20 bg-red-500/5 space-y-2"
      >
        <div class="flex items-center justify-between">
          <span class="text-xs text-slate-400">🗑️ 删除</span>
          <span class="text-xs font-mono text-red-400">{{ stats.delete_done }}/{{ stats.delete_total }}</span>
        </div>
        <div class="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div
            class="h-full bg-red-500 rounded-full transition-all duration-300"
            :style="{ width: stats.delete_total > 0 ? `${(stats.delete_done / stats.delete_total) * 100}%` : '0%' }"
          ></div>
        </div>
      </div>

      <div
        v-if="stats.keep_total > 0"
        class="p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 space-y-2"
      >
        <div class="flex items-center justify-between">
          <span class="text-xs text-slate-400">✅ 保留</span>
          <span class="text-xs font-mono text-emerald-400">{{ stats.keep_done }}/{{ stats.keep_total }}</span>
        </div>
        <div class="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div
            class="h-full bg-emerald-500 rounded-full transition-all duration-300"
            :style="{ width: stats.keep_total > 0 ? `${(stats.keep_done / stats.keep_total) * 100}%` : '0%' }"
          ></div>
        </div>
      </div>
    </div>

    <div v-if="completedItems.length > 0" class="p-4 rounded-lg border border-slate-600/30 bg-slate-900/50">
      <div class="flex items-center justify-between mb-3">
        <span class="text-sm font-medium text-slate-300">📋 已完成操作 ({{ completedItems.length }})</span>
      </div>
      <div class="space-y-1.5 max-h-36 overflow-y-auto pr-1">
        <div
          v-for="(item, index) in displayedCompletedItems"
          :key="index"
          class="flex items-center gap-2 text-xs p-2 rounded bg-slate-800/50"
        >
          <CheckCircle :size="14" class="text-emerald-400 flex-shrink-0" />
          <span
            class="px-1.5 py-0.5 rounded text-xs font-medium flex-shrink-0"
            :style="{ backgroundColor: getActionColor(item.action) + '20', color: getActionColor(item.action) }"
          >
            {{ getActionLabel(item.action) }}
          </span>
          <span class="text-slate-400 truncate flex-1 font-mono">{{ item.file }}</span>
          <span v-if="item.new_path && item.new_path !== item.file" class="text-slate-500 hidden md:inline">
            → {{ item.new_path }}
          </span>
        </div>
      </div>
    </div>

    <button
      type="button"
      class="w-full px-6 py-3 rounded-lg border border-red-400/30 text-red-300 bg-red-500/10 hover:bg-red-500/20 transition-all text-sm font-medium flex items-center justify-center gap-2"
      @click="handleCancel"
    >
      <X :size="18" />
      取消任务
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Loader2, FileText, CheckCircle, X } from 'lucide-vue-next'

const props = defineProps({
  isRunning: {
    type: Boolean,
    default: false,
  },
  current: {
    type: Number,
    default: 0,
  },
  total: {
    type: Number,
    default: 0,
  },
  message: {
    type: String,
    default: '',
  },
  currentFile: {
    type: String,
    default: '',
  },
  speed: {
    type: Number,
    default: 0,
  },
  formattedEta: {
    type: String,
    default: '计算中...',
  },
  stats: {
    type: Object,
    default: () => ({
      move_total: 0,
      move_done: 0,
      delete_total: 0,
      delete_done: 0,
      rename_total: 0,
      rename_done: 0,
      keep_total: 0,
      keep_done: 0,
    }),
  },
  completedItems: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['cancel'])

const percentage = computed(() => {
  if (props.total === 0) return 0
  return Math.min(100, Math.round((props.current / props.total) * 100))
})

const displayedCompletedItems = computed(() => {
  return props.completedItems.slice(-8)
})

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

const handleCancel = () => {
  emit('cancel')
}
</script>
