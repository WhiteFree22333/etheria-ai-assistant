<script setup lang="ts">
defineProps<{ logs: string[] }>()
defineEmits<{ clear: [] }>()
</script>

<template>
  <section class="log-panel">
    <div class="log-header">
      <h3>运行日志</h3>
      <button class="btn-sm" @click="$emit('clear')">清空</button>
    </div>
    <div class="log-content">
      <div v-for="(log, i) in logs" :key="i" class="log-line">{{ log }}</div>
      <div v-if="logs.length === 0" class="log-empty">等待任务开始...</div>
    </div>
  </section>
</template>

<style scoped>
.log-panel { background: #fff; border-radius: 12px; overflow: hidden; }
.log-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid #e5e7eb; }
.log-header h3 { font-size: 14px; }
.log-content { max-height: 150px; overflow-y: auto; padding: 12px 16px; font-size: 12px; font-family: Consolas, monospace; color: #666; line-height: 1.6; }
.log-empty { color: #bbb; font-style: italic; }
.btn-sm { padding: 4px 12px; border: none; border-radius: 4px; font-size: 12px; cursor: pointer; background: #8b5cf6; color: white; }
.btn-sm:hover { background: #7c3aed; }
</style>
