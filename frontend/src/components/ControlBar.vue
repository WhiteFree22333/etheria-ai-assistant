<script setup lang="ts">
defineProps<{ status: { running: boolean; busy: boolean } }>()
</script>

<template>
  <div class="control-panel">
    <div class="control-info">
      <div class="status-dot" :class="{ running: status.running }"></div>
      <span>{{ status.running ? '任务运行中...' : status.busy ? '忙碌中...' : '就绪' }}</span>
    </div>
  </div>
</template>

<style scoped>
.control-panel {
  display: flex; justify-content: space-between; align-items: center;
  background: #fff; border-radius: 12px; padding: 14px 24px;
}
.control-info { display: flex; align-items: center; gap: 10px; font-size: 14px; }
.status-dot { width: 10px; height: 10px; border-radius: 50%; background: #d1d5db; }
.status-dot.running { background: #10b981; animation: pulse 1.5s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
</style>
