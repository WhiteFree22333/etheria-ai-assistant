import { ref, inject, type Ref } from 'vue'
import type { RunStatus } from '../types'

type TaskFn = () => Promise<boolean>

interface RegisteredTask {
  order: number
  name: string
  fn: TaskFn
}

const tasks = ref<RegisteredTask[]>([])

export function useGlobalRun() {
  const status = inject<Ref<RunStatus>>('status')!
  const addLog = inject<(msg: string) => void>('addLog')!

  function registerTask(order: number, name: string, fn: TaskFn) {
    // Remove any existing task with same name, then add
    tasks.value = tasks.value.filter(t => t.name !== name)
    tasks.value.push({ order, name, fn })
    tasks.value.sort((a, b) => a.order - b.order)
  }

  async function runAll() {
    if (status.value.busy) return

    const ordered = tasks.value.filter(t => t.fn)
    if (ordered.length === 0) {
      addLog('⚠ 没有可执行的任务（请勾选选项）')
      return
    }

    status.value = { running: true, busy: true }
    addLog(`=== 一键执行开始（共 ${ordered.length} 项） ===`)

    for (const task of ordered) {
      if (!status.value.running) break
      addLog(`--- ${task.name} ---`)
      try {
        const ok = await task.fn()
        if (!ok) {
          addLog(`✗ ${task.name} 失败，跳过，继续下一个...`)
          continue
        }
        addLog(`✓ ${task.name} 完成`)
      } catch (e: any) {
        addLog(`✗ ${task.name} 异常: ${e}，跳过，继续下一个...`)
        continue
      }
    }

    status.value = { running: false, busy: false }
    addLog('=== 一键执行结束 ===')
  }

  async function stopAll() {
    const api = window.pywebview?.api
    if (!api) return
    await api.stop_task()
    status.value = { running: false, busy: false }
    addLog('已请求停止')
  }

  return { registerTask, runAll, stopAll }
}
