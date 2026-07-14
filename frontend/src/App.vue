<script setup lang="ts">
import { ref, provide, onMounted } from 'vue'
import type { RunStatus } from './types'
import { usePywebview } from './composables/usePywebview'
import { useGlobalRun } from './composables/useGlobalRun'
import AppHeader from './components/AppHeader.vue'
import Sidebar from './components/Sidebar.vue'
import DailyPage from './components/DailyPage.vue'
import EventPage from './components/EventPage.vue'
import ShilianPage from './components/ShilianPage.vue'
import RtaPage from './components/RtaPage.vue'
import ControlBar from './components/ControlBar.vue'
import LogPanel from './components/LogPanel.vue'
import ServerSelect from './components/ServerSelect.vue'

const activeTab = ref('daily')
const serverReady = ref(false)
const status = ref<RunStatus>({ running: false, busy: false })
const updateInfo = ref<any>(null)
const { logs, init, addLog, clearLogs } = usePywebview()
const { registerTask } = useGlobalRun()

const tabs = [
  { id: 'daily', label: '日常', icon: '📋' },
  { id: 'shilian', label: '试炼', icon: '⚔️' },
  { id: 'events', label: '活动', icon: '🎉' },
  { id: 'rta', label: 'RTA', icon: '⚡' },
]

provide('addLog', addLog)
provide('status', status)
provide('registerTask', registerTask)

onMounted(async () => {
  addLog('程序启动')
  await init()
})

function onServerSelected() {
  serverReady.value = true
  addLog('区服已选择')
  // 后台检查更新
  checkUpdate()
}

async function checkUpdate() {
  try {
    const api = (window as any).pywebview?.api
    if (!api) return
    const info = await api.check_update()
    if (info?.has_update) {
      updateInfo.value = info
    }
  } catch (_) {}
}
</script>

<template>
  <ServerSelect v-if="!serverReady" @selected="onServerSelected" />
  <template v-else>
    <AppHeader />
    <div v-if="updateInfo" class="update-banner">
      <span>发现新版本 {{ updateInfo.latest }}（当前 {{ updateInfo.current }}）</span>
      <a class="update-link" :href="updateInfo.url" target="_blank">前往下载</a>
      <button class="update-dismiss" @click="updateInfo = null">✕</button>
    </div>
    <div class="layout">
      <Sidebar :tabs="tabs" :active="activeTab" @select="activeTab = $event" />
      <div class="main">
        <DailyPage v-show="activeTab === 'daily'" />
        <ShilianPage v-show="activeTab === 'shilian'" />
        <EventPage v-show="activeTab === 'events'" />
        <RtaPage v-show="activeTab === 'rta'" />
        <ControlBar :status="status" />
        <LogPanel :logs="logs" @clear="clearLogs" />
      </div>
    </div>
  </template>
</template>

<style scoped>
.update-banner {
  background: linear-gradient(135deg, #7c3aed, #a855f7);
  color: #fff;
  padding: 8px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 14px;
  border-radius: 8px;
  margin-bottom: 4px;
}
.update-link {
  color: #fbbf24;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
}
.update-link:hover { text-decoration: underline; }
.update-dismiss {
  margin-left: auto;
  background: none;
  border: none;
  color: #fff;
  font-size: 18px;
  cursor: pointer;
  opacity: 0.7;
}
.update-dismiss:hover { opacity: 1; }
.layout { display: flex; gap: 12px; min-height: 500px; }
.main { flex: 1; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
</style>
