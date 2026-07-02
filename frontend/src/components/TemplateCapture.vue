<script setup lang="ts">
import { ref, inject } from 'vue'

const addLog = inject<(msg: string) => void>('addLog')!
const name = ref('')
const count = ref(0)
function getApi() { return window.pywebview?.api }

async function selectRegion() {
  const api = getApi()
  if (!name.value || !api) return
  addLog('正在截取游戏画面...')
  try {
    const result = await api.select_and_save_template(name.value)
    if (result.success) {
      addLog(`模板已保存: ${result.filename} (${result.region[2]}x${result.region[3]})`)
      const tpls = await api.list_templates()
      count.value = (tpls || []).length
      name.value = ''
    } else {
      addLog(result.message || '选取失败')
    }
  } catch (e: any) { addLog(`选取失败: ${e}`) }
}
</script>

<template>
  <hr class="divider" />
  <div class="inline-form">
    <input type="text" v-model="name" placeholder="模板名称（如：尼可娜娜图标）" class="input-name" />
    <button class="btn-sm" @click="selectRegion" :disabled="!name">🎯 截取图标</button>
    <span class="tpl-count" v-if="count">已存 {{ count }} 个</span>
  </div>
</template>

<style scoped>
.divider { border: none; border-top: 1px solid #e5e7eb; margin: 20px 0; }
.inline-form { display: flex; gap: 8px; align-items: center; }
.input-name { flex: 1; max-width: 200px; padding: 8px 12px; border: 1px solid #e5e7eb; border-radius: 6px; font-size: 14px; outline: none; }
.input-name:focus { border-color: #8b5cf6; }
.btn-sm { padding: 4px 12px; border: none; border-radius: 4px; font-size: 12px; cursor: pointer; background: #8b5cf6; color: white; }
.btn-sm:hover { background: #7c3aed; }
.btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
.tpl-count { font-size: 12px; color: #666; white-space: nowrap; }
</style>
