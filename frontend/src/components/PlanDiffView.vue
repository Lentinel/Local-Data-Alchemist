<template>
  <div class="plan-diff-view">
    <div v-if="!plan || plan.length === 0" class="text-slate-500 text-sm p-4 text-center">
      暂无计划数据
    </div>
    
    <div v-else class="space-y-2">
      <!-- 统计摘要 -->
      <div class="flex flex-wrap gap-3 mb-4">
        <div class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/50 border border-slate-700/50">
          <span class="text-xs text-slate-400">总操作</span>
          <span class="text-sm font-bold text-slate-200">{{ plan.length }}</span>
        </div>
        <div v-for="(count, action) in actionCounts" :key="action"
          class="flex items-center gap-2 px-3 py-1.5 rounded-lg border"
          :class="getActionBgClass(action)"
        >
          <span class="text-xs" :class="getActionTextClass(action)">{{ getActionLabel(action) }}</span>
          <span class="text-sm font-bold" :class="getActionTextClass(action)">{{ count }}</span>
        </div>
      </div>
      
      <!-- 差异列表 -->
      <div class="space-y-1 max-h-96 overflow-y-auto pr-1">
        <div
          v-for="(item, index) in sortedPlan"
          :key="index"
          class="flex items-start gap-3 p-3 rounded-lg border transition-colors hover:bg-white/5"
          :class="getDiffBorderClass(item.action)"
        >
          <!-- 操作图标 -->
          <div class="flex-shrink-0 mt-0.5">
            <component :is="getActionIcon(item.action)" :size="18" :class="getActionIconClass(item.action)" />
          </div>
          
          <!-- 差异内容 -->
          <div class="flex-1 min-w-0">
            <!-- 源文件 -->
            <div class="flex items-center gap-2">
              <span class="text-xs text-slate-500 font-mono uppercase w-8">从</span>
              <span class="text-sm text-slate-300 font-mono truncate">{{ item.file }}</span>
            </div>
            
            <!-- 目标路径（仅 move/rename_and_move） -->
            <div v-if="item.target_path && (item.action === 'move' || item.action === 'rename_and_move')" class="flex items-center gap-2 mt-1">
              <span class="text-xs text-slate-500 font-mono uppercase w-8">到</span>
              <span class="text-sm font-mono truncate" :class="isNewPath(item.target_path) ? 'text-emerald-300' : 'text-sky-300'">
                {{ item.target_path }}
              </span>
              <span v-if="isNewPath(item.target_path)" class="text-xs text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded flex-shrink-0">
                新目录
              </span>
            </div>
            
            <!-- 操作标签 -->
            <div class="flex items-center gap-2 mt-1.5">
              <span
                class="text-xs px-2 py-0.5 rounded-full border"
                :class="getActionTagClass(item.action)"
              >
                {{ getActionLabel(item.action) }}
              </span>
              <span v-if="item.reason" class="text-xs text-slate-500 truncate">{{ item.reason }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowRight, Trash2, Check, FolderInput, Pencil } from 'lucide-vue-next'

const props = defineProps({
  plan: { type: Array, default: () => [] },
  existingPaths: { type: Set, default: () => new Set() },
})

// 按操作类型排序：delete > rename_and_move > move > keep
const actionOrder = { delete: 0, rename_and_move: 1, move: 2, keep: 3 }

const sortedPlan = computed(() => {
  return [...props.plan].sort((a, b) => {
    const orderA = actionOrder[a.action] ?? 99
    const orderB = actionOrder[b.action] ?? 99
    if (orderA !== orderB) return orderA - orderB
    return a.file.localeCompare(b.file)
  })
})

const actionCounts = computed(() => {
  const counts = {}
  for (const item of props.plan) {
    counts[item.action] = (counts[item.action] || 0) + 1
  }
  return counts
})

const isNewPath = (path) => {
  // 检查目标路径是否是新创建的目录
  const dir = path.substring(0, path.lastIndexOf('/'))
  return dir && !props.existingPaths.has(dir)
}

const getActionLabel = (action) => {
  const labels = {
    rename_and_move: '重命名移动',
    move: '移动',
    delete: '删除',
    keep: '保留',
  }
  return labels[action] || action
}

const getActionIcon = (action) => {
  const icons = {
    rename_and_move: Pencil,
    move: FolderInput,
    delete: Trash2,
    keep: Check,
  }
  return icons[action] || ArrowRight
}

const getActionIconClass = (action) => {
  const classes = {
    rename_and_move: 'text-sky-300',
    move: 'text-emerald-300',
    delete: 'text-rose-300',
    keep: 'text-slate-400',
  }
  return classes[action] || 'text-slate-400'
}

const getActionTextClass = (action) => {
  const classes = {
    rename_and_move: 'text-sky-300',
    move: 'text-emerald-300',
    delete: 'text-rose-300',
    keep: 'text-slate-300',
  }
  return classes[action] || 'text-slate-300'
}

const getActionBgClass = (action) => {
  const classes = {
    rename_and_move: 'bg-sky-500/10 border-sky-400/20',
    move: 'bg-emerald-500/10 border-emerald-400/20',
    delete: 'bg-rose-500/10 border-rose-400/20',
    keep: 'bg-slate-500/10 border-slate-400/20',
  }
  return classes[action] || 'bg-slate-500/10 border-slate-400/20'
}

const getDiffBorderClass = (action) => {
  const classes = {
    rename_and_move: 'border-sky-400/20',
    move: 'border-emerald-400/20',
    delete: 'border-rose-400/20',
    keep: 'border-slate-700/50',
  }
  return classes[action] || 'border-slate-700/50'
}

const getActionTagClass = (action) => {
  const classes = {
    rename_and_move: 'text-sky-200 bg-sky-500/10 border-sky-400/30',
    move: 'text-emerald-200 bg-emerald-500/10 border-emerald-400/30',
    delete: 'text-rose-200 bg-rose-500/10 border-rose-400/30',
    keep: 'text-slate-300 bg-slate-500/10 border-slate-400/30',
  }
  return classes[action] || 'text-slate-300 bg-slate-500/10 border-slate-400/30'
}
</script>
