<template>
  <div v-if="isVisible" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
    <div class="relative w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-lg glass border border-white/10 flex flex-col">
      <div class="flex items-center justify-between p-4 border-b border-white/10">
        <div class="flex items-center gap-3">
          <FileText :size="24" class="text-sky-300" />
          <div>
            <p class="font-medium text-slate-100">{{ file?.name }}</p>
            <p class="text-xs text-slate-400 font-mono">{{ file?.path }}</p>
          </div>
        </div>
        <button
          type="button"
          class="p-2 rounded-lg border border-slate-400/20 bg-white/5 hover:bg-white/10 transition-colors"
          @click="handleClose"
          title="关闭预览"
        >
          <X :size="20" class="text-slate-300" />
        </button>
      </div>

      <div class="flex-1 overflow-auto p-4">
        <div v-if="error" class="flex items-center gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
          <AlertCircle :size="20" />
          <p>{{ error }}</p>
        </div>

        <div v-else-if="!content" class="flex items-center justify-center h-64">
          <div class="flex items-center gap-3 text-slate-400">
            <Loader2 :size="24" class="animate-spin" />
            <p>正在加载文件预览...</p>
          </div>
        </div>

        <div v-else-if="content.type === 'text'" class="w-full">
          <div class="mb-3 flex items-center gap-2">
            <span class="text-xs text-slate-400 font-mono uppercase">文本文件预览</span>
            <span v-if="content.truncated" class="text-xs text-amber-400 font-mono">（已截断，仅显示前 10KB）</span>
          </div>
          <pre class="p-4 rounded-lg bg-slate-950/70 border border-white/10 text-sm text-slate-200 whitespace-pre-wrap overflow-auto max-h-[60vh]">
{{ content.content || '文件内容为空' }}
          </pre>
        </div>

        <div v-else-if="content.type === 'image'" class="w-full flex flex-col items-center justify-center">
          <div class="mb-3 text-xs text-slate-400 font-mono uppercase">图片文件预览</div>
          
          <template v-if="isValidImageContent">
            <img
              :src="imageSrc"
              :alt="file?.name"
              class="max-w-full max-h-[60vh] object-contain rounded-lg border border-white/10"
              @error="handleImageError"
            />
          </template>
          
          <div v-else class="p-4 rounded-lg bg-slate-950/70 border border-white/10 text-slate-200">
            <p>{{ content.content || '无法预览此图片' }}</p>
          </div>
        </div>

        <div v-else-if="content.type === 'pdf'" class="w-full">
          <div class="mb-3 text-xs text-slate-400 font-mono uppercase">PDF文件预览</div>
          <div class="p-4 rounded-lg bg-slate-950/70 border border-white/10 text-slate-200">
            <p>{{ content.content }}</p>
          </div>
        </div>

        <div v-else class="w-full">
          <div class="mb-3 text-xs text-slate-400 font-mono uppercase">文件类型：{{ content.type }}</div>
          <div class="p-4 rounded-lg bg-slate-950/70 border border-white/10 text-slate-200">
            <p>{{ content.content }}</p>
          </div>
        </div>
      </div>

      <div class="p-4 border-t border-white/10 flex items-center justify-between">
        <div class="flex items-center gap-4 text-xs text-slate-400 font-mono">
          <span>大小：{{ formattedSize }}</span>
          <span>类型：{{ file?.category || 'unknown' }}</span>
          <span>扩展名：{{ file?.extension || 'unknown' }}</span>
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
import { computed } from 'vue'
import { FileText, X, AlertCircle, Loader2 } from 'lucide-vue-next'

const props = defineProps({
  isVisible: {
    type: Boolean,
    default: false,
  },
  file: {
    type: Object,
    default: null,
  },
  content: {
    type: Object,
    default: null,
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

const emit = defineEmits(['close', 'imageError'])

const formattedSize = computed(() => {
  if (props.formatBytesFn && props.file?.size !== undefined) {
    return props.formatBytesFn(props.file.size)
  }
  return props.file?.size ? `${props.file.size} B` : '—'
})

const isValidImageContent = computed(() => {
  if (!props.content?.content) return false
  const c = props.content.content
  return !c.startsWith('[') && !c.endsWith(']')
})

const imageSrc = computed(() => {
  if (!props.content?.content || !props.content?.extension) return ''
  const ext = props.content.extension.replace('.', '')
  return `data:image/${ext};base64,${props.content.content}`
})

const handleClose = () => {
  emit('close')
}

const handleImageError = () => {
  emit('imageError', '图片预览失败，请检查文件格式')
}
</script>
