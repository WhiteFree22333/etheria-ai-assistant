<script setup lang="ts">
import { ref, inject, type Ref, onMounted } from "vue";
import type { RunStatus } from "../../types";

const addLog = inject<(msg: string) => void>("addLog")!;
const status = inject<Ref<RunStatus>>("status")!;

const tasks = ref([
  { id: "arena", label: "竞技场自动", checked: false },
  { id: "arena_claim", label: "竞技场一键领取", checked: false },
  { id: "signin", label: "公会签到", checked: false },
  { id: "anchor", label: "锚点勘测", checked: false },
  { id: "weekly", label: "公会每周任务领取", checked: false },
  { id: "assist", label: "协会共助", checked: false },
  { id: "theater", label: "幻音剧场", checked: false },
  { id: "remind", label: "提醒成员签到", checked: false, hidden: true },
  { id: "claim_all", label: "任务一键领取", checked: false },
  { id: "anchor_claim", label: "锚点勘测一键领取", checked: false },
]);

function toggleAll() {
  const visible = tasks.value.filter((t: any) => !t.hidden);
  const allChecked = visible.every((t) => t.checked);
  visible.forEach((t) => (t.checked = !allChecked));
}

const registerTask = inject<
  (order: number, name: string, fn: () => Promise<boolean>) => void
>("registerTask", () => {});

function getApi() {
  return window.pywebview?.api;
}

const GUILD_TASK_ORDERS: Record<string, number> = {
  arena: 1,
  arena_claim: 2,
  signin: 3,
  anchor: 4,
  anchor_claim: 6,
  weekly: 7,
  theater: 8,
  claim_all: 5,
  assist: 9,
};

onMounted(() => {
  for (const t of tasks.value) {
    const order = GUILD_TASK_ORDERS[t.id];
    if (!order || (t as any).hidden) continue;
    registerTask(order, t.label, async () => {
      if (!t.checked) return true; // skip unchecked
      const api = getApi();
      if (!api) return false;
      const fn = api[`run_guild_${t.id}`] as
        | (() => Promise<boolean>)
        | undefined;
      if (typeof fn !== "function") {
        addLog(`API ${t.id} 不存在`);
        return false;
      }
      return fn();
    });
  }
});

async function startAll() {
  const selected = tasks.value.filter((t) => t.checked);
  if (selected.length === 0) {
    addLog("请至少勾选一项");
    return;
  }
  if (status.value.busy) return;

  status.value = { running: true, busy: true };
  addLog(`一键执行: ${selected.map((t) => t.label).join("、")}...`);

  try {
    for (const task of selected) {
      if (!status.value.running) break;
      addLog(`--- 执行: ${task.label} ---`);
      const api = getApi();
      if (!api) continue;
      const methodName = `run_guild_${task.id}`;
      const fn = api[methodName] as (() => Promise<boolean>) | undefined;
      if (typeof fn !== "function") {
        addLog(`API 方法不存在: ${methodName}`);
        continue;
      }
      const ok = await fn();
      if (!ok) {
        addLog(`${task.label} 失败，跳过，继续下一个...`);
        continue;
      }
      addLog(`${task.label} 完成`);
      await new Promise((r) => setTimeout(r, 500));
    }
  } catch (e: any) {
    addLog(`执行异常: ${e}`);
  }

  status.value = { running: false, busy: false };
  addLog("一键执行结束");
}

async function stopTask() {
  const api = getApi();
  if (!api) return;
  await api.stop_task();
  status.value = { running: false, busy: false };
  addLog("已请求停止");
}
</script>

<template>
  <div class="guild-root">
    <div class="guild-list">
      <label
        v-for="t in tasks.filter((x: any) => !x.hidden)"
        :key="t.id"
        class="guild-row"
      >
        <input type="checkbox" v-model="t.checked" class="guild-check" />
        <span class="guild-label">{{ t.label }}</span>
      </label>
    </div>

    <div class="guild-actions">
      <button class="btn btn-sm" @click="toggleAll">全选/反选</button>
    </div>

    <div class="start-area">
      <button class="btn btn-primary" @click="startAll" :disabled="status.busy">
        {{ status.busy ? "执行中..." : "▶ 开始执行" }}
      </button>
      <button
        class="btn btn-danger"
        @click="stopTask"
        :disabled="!status.running"
      >
        停止
      </button>
      <span
        v-if="tasks.filter((t) => t.checked).length === 0 && !status.busy"
        class="hint"
      >
        请先勾选要执行的任务
      </span>
    </div>
  </div>
</template>

<style scoped>
.guild-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.guild-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
}
.guild-row:hover {
  background: #f0f0f0;
}
.guild-check {
  width: 18px;
  height: 18px;
  accent-color: #8b5cf6;
  cursor: pointer;
}
.guild-label {
  font-size: 15px;
  font-weight: 500;
}
.guild-actions {
  margin-top: 10px;
}
.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-primary {
  background: #8b5cf6;
  color: white;
}
.btn-primary:hover:not(:disabled) {
  background: #7c3aed;
}
.btn-danger {
  background: #ef4444;
  color: white;
}
.btn-danger:hover:not(:disabled) {
  background: #dc2626;
}
.btn-sm {
  padding: 4px 12px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  background: #8b5cf6;
  color: white;
}
.btn-sm:hover {
  background: #7c3aed;
}
.start-area {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
}
.hint {
  font-size: 13px;
  color: #f59e0b;
  font-weight: 500;
}
</style>
