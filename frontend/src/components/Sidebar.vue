<script setup lang="ts">
import { inject, type Ref } from 'vue'
import type { RunStatus } from '../types'
import { useGlobalRun } from '../composables/useGlobalRun'

defineProps<{
  tabs: { id: string; label: string; icon: string }[]
  active: string
}>()
defineEmits<{ select: [id: string] }>()

const status = inject<Ref<RunStatus>>('status')!
const { runAll, stopAll } = useGlobalRun()
</script>

<template>
  <nav class="sidebar">
    <button
      v-for="tab in tabs"
      :key="tab.id"
      :class="['sidebar-tab', { active: active === tab.id }]"
      @click="$emit('select', tab.id)"
    >
      <span class="tab-icon">{{ tab.icon }}</span>
      <span class="tab-label">{{ tab.label }}</span>
    </button>

    <!-- 一键执行（RTA下方，浅灰分隔线区隔） -->
    <div class="sidebar-divider" />
    <button
      v-if="!status.running"
      class="sidebar-btn-run"
      @click="runAll"
      :disabled="status.busy"
    >
      ▶ 一键执行
    </button>
    <button
      v-else
      class="sidebar-btn-stop"
      @click="stopAll"
    >
      ⏹ 停止执行
    </button>
  </nav>
</template>

<style scoped>
.sidebar {
  width: 160px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: #fff;
  border-radius: 12px;
  padding: 8px;
}
.sidebar-tab {
  display: flex; align-items: center; gap: 10px;
  width: 100%; padding: 14px 16px;
  border: none; background: transparent;
  color: #666; font-size: 14px; font-weight: 500;
  cursor: pointer; border-radius: 8px;
  transition: all 0.2s; text-align: left;
}
.sidebar-tab:hover { background: #f3f4f6; }
.sidebar-tab.active { background: #8b5cf6; color: white; }
.tab-icon { font-size: 18px; }

.sidebar-divider {
  height: 1px;
  background: #e5e7eb;
  margin: 8px 4px;
}

.sidebar-btn-run, .sidebar-btn-stop {
  width: 100%;
  padding: 10px 0;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.sidebar-btn-run {
  background: #1a1a2e;
  color: #fff;
}
.sidebar-btn-run:hover:not(:disabled) { background: #2d2d4e; }
.sidebar-btn-run:disabled { opacity: 0.4; cursor: not-allowed; }

.sidebar-btn-stop {
  background: #ef4444;
  color: white;
}
.sidebar-btn-stop:hover { background: #dc2626; }
</style>
