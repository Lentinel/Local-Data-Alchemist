<template>
  <div v-if="isVisible" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
    <div class="relative w-full max-w-5xl max-h-[90vh] overflow-hidden rounded-lg glass border border-white/10 flex flex-col">
      <div class="flex items-center justify-between p-4 border-b border-white/10">
        <div class="flex items-center gap-3">
          <Copy :size="24" class="text-amber-400" />
          <div>
            <p class="font-medium text-slate-100">重复文件检测</p>
            <p class="text-xs text-slate-400 font-mono">
              共 {{ duplicateGroups.length }} 组重复文件
            </p>
          </div>
        </div>
        <button
          type="button"
          class="p-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors"
          @click="handleClose"
          title="关闭"
        >
          <X :size="20" class="text-slate-300" />
        </button>
      </div>

      <div class="flex-1 overflow-auto p-4">
        <div v-if="error" class="flex items-center gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
          <AlertCircle :size="20" />
          <p>{{ error }}</p>
        </div>

        <div v-else-if="isLoading" class="flex items-center justify-center h-64">
          <div class="flex items-center gap-3 text-slate-400">
            <Loader2 :size="24" class="animate-spin" />
            <p>正在检测重复文件...</p>
          </div>
        </div>

        <div v-else-if="duplicateGroups.length === 0" class="flex flex-col items-center justify-center h-64 text-slate-400">
          <CheckCircle :size="48" class="mb-3 text-emerald-500" />
          <p class="text-lg font-medium">未检测到重复文件</p>
          <p class="text-sm mt-1">当前目录中的文件都是唯一的</p>
        </div>

        <div v-else class="w-full space-y-4">
          <div
            v-for="(group, groupIndex) in duplicateGroups"
            :key="group.hash"
            class="rounded-lg border"
            :class="group.processed ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-slate-950/50 border-white/5'"
          >
            <div class="flex items-center justify-between p-3 border-b border-white/5">
              <div class="flex items-center gap-3">
                <div 
                  class="w-10 h-10 rounded-lg flex items-center justify-center"
                  :class="group.processed ? 'bg-emerald-500/20' : 'bg-amber-500/10'"
                >
                  <Copy 
                    :size="20" 
                    :class="group.processed ? 'text-emerald-400' : 'text-amber-400'" 
                  />
                </div>
                <div>
                  <p class="text-sm font-medium text-slate-200">
                    第 {{ groupIndex + 1 }} 组 · {{ group.files.length }} 个重复文件
                  </p>
                  <p class="text-xs text-slate-400 font-mono">
                    MD5: {{ group.hash.substring(0, 16) }}... · {{ formatBytesFn ? formatBytesFn(group.size) : group.size + ' B' }}
                  </p>
                </div>
              </div>
              <div v-if="group.processed" class="flex items-center gap-2">
                <span class="px-2 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs">
                  已处理
                </span>
              </div>
            </div>

            <div class="p-3 space-y-2">
              <div
                v-for="(file, fileIndex) in group.files"
                :key="file.path"
                class="flex items-center justify-between p-2 rounded-lg"
                :class="[
                  selectedKeepFiles[group.hash] === file.path 
                    ? 'bg-sky-500/10 border border-sky-500/20' 
                    : 'bg-white/5 hover:bg-white/10 border border-transparent'
                ]"
              >
                <label class="flex items-center gap-3 cursor-pointer flex-1">
                  <input
                    type="radio"
                    :name="`keep-${group.hash}`"
                    :value="file.path"
                    :checked="selectedKeepFiles[group.hash] === file.path"
                    @click="handleToggleKeep(group.hash, file.path)"
                    :disabled="isProcessing || group.processed"
                    class="rounded border-slate-400 bg-transparent text-sky-500 focus:ring-sky-500"
                  />
                  <div class="flex-1 min-w-0">
                    <p class="text-sm text-slate-200 truncate">{{ file.name }}</p>
                    <p class="text-xs text-slate-500 font-mono truncate">{{ file.path }}</p>
                  </div>
                  <div class="flex items-center gap-2 flex-shrink-0">
                    <span 
                      v-if="selectedKeepFiles[group.hash] === file.path"
                      class="px-2 py-0.5 rounded bg-sky-500/10 text-sky-300 text-xs"
                    >
                      保留
                    </span>
                    <button
                      v-if="!group.processed"
                      type="button"
                      class="px-3 py-1 rounded text-xs"
                      :class="[
                        isProcessing
                          ? 'bg-slate-600 text-slate-400 cursor-not-allowed'
                          : 'bg-sky-500/10 border border-sky-500/20 text-sky-300 hover:bg-sky-500/20'
                      ]"
                      :disabled="isProcessing"
                      @click="handleKeepSelected(group.hash, fileIndex)"
                    >
                      保留此文件
                    </button>
                  </div>
                </label>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="p-4 border-t border-white/10 flex items-center justify-between">
        <div class="text-xs text-slate-400">
          提示：选择要保留的文件，其他副本将被删除
        </div>
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
import { Copy, X, AlertCircle, Loader2, CheckCircle } from 'lucide-vue-next'

const props = defineProps({
  isVisible: {
    type: Boolean,
    default: false,
  },
  isLoading: {
    type: Boolean,
    default: false,
  },
  isProcessing: {
    type: Boolean,
    default: false,
  },
  duplicateGroups: {
    type: Array,
    default: () => [],
  },
  selectedKeepFiles: {
    type: Object,
    default: () => ({}),
  },
  error: {
    type: String,
    default: null,
  },
  formatBytesFn: {
    type: Function,
    default: null,
  },
})

const emit = defineEmits(['close', 'toggle-keep', 'keep-selected'])

const handleClose = () => {
  emit('close')
}

const handleToggleKeep = (hash, filePath) => {
  emit('toggle-keep', hash, filePath)
}

const handleKeepSelected = (hash, index) => {
  emit('keep-selected', hash, index)
}
</script>
