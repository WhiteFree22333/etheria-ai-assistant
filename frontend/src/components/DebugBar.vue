<template>
  <div class="debug-bar">
    <span class="debug-label">🔧 退出点调试</span>
    <label>X: <input type="number" v-model.number="offsetX" style="width:50px" /></label>
    <label>Y: <input type="number" v-model.number="offsetY" style="width:50px" /></label>
    <button @click="capture">截图标点</button>
    <img v-if="preview" :src="'data:image/png;base64,' + preview" class="debug-preview" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const offsetX = ref(60)
const offsetY = ref(60)
const preview = ref('')

async function capture() {
  const b64 = await (window as any).pywebview.api.debug_exit_point(offsetX.value, offsetY.value)
  preview.value = b64
}
</script>

<style scoped>
.debug-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #1a1a2e;
  border-top: 1px solid #333;
  font-size: 13px;
}
.debug-bar label { color: #aaa; }
.debug-bar button {
  padding: 2px 10px;
  background: #444;
  color: #fff;
  border: 1px solid #666;
  border-radius: 3px;
  cursor: pointer;
}
.debug-preview { max-height: 100px; border: 1px solid #555; }
</style>
