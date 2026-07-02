import { ref, type Ref } from 'vue'

const api: Ref<Record<string, (...args: any[]) => Promise<any>> | null> = ref(null)
const logs: Ref<string[]> = ref([])

export function usePywebview() {
  async function init(maxRetries = 10) {
    let retries = 0
    while (retries < maxRetries) {
      if (window.pywebview?.api) {
        api.value = window.pywebview.api
        addLog('已连接后端')
        return true
      }
      await new Promise(r => setTimeout(r, 200))
      retries++
    }
    addLog('⚠ 浏览器模式，Python API 不可用')
    return false
  }

  function addLog(msg: string) {
    logs.value.push(`[${new Date().toLocaleTimeString()}] ${msg}`)
    // 检测错误标记，弹窗提示
    if (msg.includes('PRESET_MISSING')) {
      setTimeout(() => alert('亲，您没有设置预设阵容哦，请设置后回到主页重新开始。'), 100)
    } else if (msg.includes('STAMINA_MISSING')) {
      setTimeout(() => alert('亲，您的体力不足请先使用体力后再开始哦！'), 100)
    }
  }

  function clearLogs() {
    logs.value = []
  }

  return { api, logs, init, addLog, clearLogs }
}
