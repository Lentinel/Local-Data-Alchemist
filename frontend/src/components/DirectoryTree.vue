<template>
  <div class="directory-tree">
    <div v-if="loading" class="flex items-center justify-center py-8">
      <Loader2 :size="24" class="animate-spin text-emerald-300" />
      <span class="ml-2 text-slate-400">加载目录树...</span>
    </div>
    
    <div v-else-if="error" class="text-red-300 text-sm p-4">
      {{ error }}
    </div>
    
    <div v-else-if="tree" class="space-y-1">
      <TreeNode :node="tree" :depth="0" :expanded="expandedNodes" @toggle="toggleNode" />
    </div>
    
    <div v-else class="text-slate-500 text-sm p-4">
      暂无目录数据
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Loader2, Folder, FolderOpen, File, FileText, Image, Code, Archive } from 'lucide-vue-next'

const props = defineProps({
  tree: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: null },
})

const expandedNodes = ref(new Set(['.']))

const toggleNode = (path) => {
  if (expandedNodes.value.has(path)) {
    expandedNodes.value.delete(path)
  } else {
    expandedNodes.value.add(path)
  }
}

const getFileIcon = (extension) => {
  if (!extension) return File
  const ext = extension.toLowerCase()
  if (['.txt', '.log', '.md', '.csv'].includes(ext)) return FileText
  if (['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'].includes(ext)) return Image
  if (['.py', '.js', '.ts', '.vue', '.html', '.css', '.java', '.go', '.rs'].includes(ext)) return Code
  if (['.zip', '.rar', '.7z', '.tar', '.gz'].includes(ext)) return Archive
  return File
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

const TreeNode = {
  props: {
    node: { type: Object, required: true },
    depth: { type: Number, default: 0 },
    expanded: { type: Set, required: true },
  },
  emits: ['toggle'],
  setup(props, { emit }) {
    const isExpanded = computed(() => props.expanded.has(props.node.path))
    const isDirectory = computed(() => props.node.type === 'directory')
    const hasChildren = computed(() => isDirectory.value && props.node.children && props.node.children.length > 0)
    
    const toggle = () => {
      if (isDirectory.value) {
        emit('toggle', props.node.path)
      }
    }
    
    return { isExpanded, isDirectory, hasChildren, toggle }
  },
  template: `
    <div>
      <div
        class="flex items-center gap-2 py-1 px-2 rounded hover:bg-white/5 cursor-pointer transition-colors"
        :style="{ paddingLeft: (depth * 16 + 8) + 'px' }"
        @click="toggle"
      >
        <span v-if="isDirectory" class="text-slate-500 w-4">
          <ChevronRight v-if="!isExpanded" :size="14" />
          <ChevronDown v-else :size="14" />
        </span>
        <span v-else class="w-4"></span>
        
        <component
          :is="isDirectory ? (isExpanded ? FolderOpen : Folder) : getFileIcon(node.extension)"
          :size="16"
          :class="isDirectory ? 'text-emerald-300' : 'text-slate-400'"
        />
        
        <span class="flex-1 text-sm" :class="isDirectory ? 'text-emerald-200 font-medium' : 'text-slate-300'">
          {{ node.name }}
        </span>
        
        <span v-if="!isDirectory && node.size" class="text-xs text-slate-500">
          {{ formatSize(node.size) }}
        </span>
        
        <span v-if="isDirectory && node.file_count" class="text-xs text-slate-500">
          {{ node.file_count }} 个文件
        </span>
        
        <span v-if="node.is_planned" class="text-xs text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">
          新增
        </span>
      </div>
      
      <div v-if="isDirectory && isExpanded && hasChildren">
        <TreeNode
          v-for="child in node.children"
          :key="child.path"
          :node="child"
          :depth="depth + 1"
          :expanded="expanded"
          @toggle="$emit('toggle', $event)"
        />
      </div>
    </div>
  `,
}
</script>

<style scoped>
.directory-tree {
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
}
</style>
