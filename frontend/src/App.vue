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

const activeTab = ref('daily')
const status = ref<RunStatus>({ running: false, busy: false })
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
</script>

<template>
  <AppHeader />
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

<style scoped>
.layout { display: flex; gap: 12px; min-height: 500px; }
.main { flex: 1; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
</style>
