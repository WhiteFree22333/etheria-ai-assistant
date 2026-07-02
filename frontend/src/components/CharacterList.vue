<script setup lang="ts">
import { ref, inject, type Ref } from "vue";
import type { Character, RunStatus } from "../types";

const addLog = inject<(msg: string) => void>("addLog")!;
const status = inject<Ref<RunStatus>>("status")!;

const props = withDefaults(
  defineProps<{
    characters: Character[];
    title: string;
    difficultyOptions?: string[];
    showDifficulty?: boolean;
    showStreak?: boolean;
    showTotalCount?: boolean;
    showStamina?: boolean;
    showDoubleStamina?: boolean;
    staminaPerBattle?: number | ((ch: Character) => number);
    maxCount?: number;
  }>(),
  {
    difficultyOptions: () => ["炼狱"],
    showDifficulty: true,
    showStreak: true,
    showTotalCount: true,
    showStamina: true,
    showDoubleStamina: false,
    staminaPerBattle: 10,
    maxCount: 99,
  }
);

const selected = ref("");

function toggleChar(id: string) {
  selected.value = selected.value === id ? "" : id;
}

function calcStamina(ch: Character): number {
  const per =
    typeof props.staminaPerBattle === "function"
      ? props.staminaPerBattle(ch)
      : props.staminaPerBattle;
  return per * (ch.streak || 1) * (ch.totalCount || 1);
}

function fixInt(ch: Character, field: "streak" | "totalCount") {
  if (!Number.isInteger(ch[field]) || ch[field] < 1) ch[field] = 1;
  else if (ch[field] > props.maxCount) ch[field] = props.maxCount;
}

function getApi() {
  return window.pywebview?.api;
}

async function doBattle(ch: Character): Promise<boolean> {
  const api = getApi();
  if (!api) return false;
  const methodName = `run_${props.title}_battle`;
  const fn = api[methodName] as (...args: any[]) => Promise<boolean>;
  if (typeof fn !== "function") {
    addLog(`⚠ API 方法不存在: ${methodName}`);
    return false;
  }
  return props.showDoubleStamina
    ? fn(ch.name, ch.difficulty, ch.streak, ch.doubleStamina ?? false)
    : fn(ch.name, ch.difficulty, ch.streak);
}

async function start() {
  if (!selected.value) {
    addLog("⚠ 请先选择一个副本");
    return;
  }
  if (status.value.busy) return;
  const ch = props.characters.find((c) => c.id === selected.value);
  if (!ch) return;

  status.value = { running: true, busy: true };
  const extra = ch.doubleStamina ? " · 双倍" : "";
  addLog(
    `开始执行${props.title}: ${ch.name} · ${ch.difficulty}${extra} · ${
      ch.streak
    }场×${ch.totalCount}次 = ${calcStamina(ch)}体力`
  );

  try {
    for (let i = 0; i < ch.totalCount; i++) {
      if (!status.value.running) break;
      addLog(`--- 第 ${i + 1}/${ch.totalCount} 次执行 ---`);
      const ok = await doBattle(ch);
      if (!ok) {
        addLog(`✗ 第 ${i + 1} 次执行失败，停止`);
        break;
      }
      if (i < ch.totalCount - 1) {
        addLog("等待结算...");
        await new Promise((r) => setTimeout(r, 3000));
      }
    }
  } catch (e: any) {
    addLog(`执行异常: ${e}`);
  }

  status.value = { running: false, busy: false };
  addLog("任务结束");
}

async function stopTask() {
  const api = getApi();
  if (!api) return;
  await api.stop_task();
  status.value = { running: false, busy: false };
  addLog("已请求停止");
}

defineExpose({ selected });
</script>

<template>
  <div class="char-list-root">
    <div class="char-list">
      <div
        v-for="ch in characters"
        :key="ch.id"
        :class="['char-row', { selected: selected === ch.id }]"
        @click="toggleChar(ch.id)"
      >
        <span class="char-dot">{{ selected === ch.id ? "●" : "○" }}</span>
        <span class="char-name">{{ ch.name }}</span>

        <div v-if="showDifficulty" class="char-field">
          <label class="fl">难度</label>
          <select v-model="ch.difficulty" class="char-select">
            <option v-for="opt in difficultyOptions" :key="opt" :value="opt">
              {{ opt }}
            </option>
          </select>
        </div>

        <div v-if="showDoubleStamina" class="char-field">
          <label class="checkbox-label">
            <input
              type="checkbox"
              v-model="ch.doubleStamina"
              class="char-check"
            />
            双倍
          </label>
        </div>

        <div v-if="showStreak" class="char-field">
          <label class="fl">场次</label>
          <input
            type="number"
            v-model.number="ch.streak"
            class="char-num"
            min="1"
            :max="maxCount"
            @input="fixInt(ch, 'streak')"
          />
        </div>

        <div v-if="showTotalCount" class="char-field">
          <label class="fl">总次数</label>
          <input
            type="number"
            v-model.number="ch.totalCount"
            class="char-num"
            min="1"
            :max="maxCount"
            @input="fixInt(ch, 'totalCount')"
          />
        </div>

        <div v-if="showStamina" class="char-field stamina">
          <span class="val">{{ calcStamina(ch) }}</span>
          <span class="unit">体力</span>
        </div>
      </div>
    </div>

    <div class="start-area">
      <button class="btn btn-primary" @click="start" :disabled="status.busy">
        {{ status.busy ? "执行中..." : "▶ 开始执行" }}
      </button>
      <button
        class="btn btn-danger"
        @click="stopTask"
        :disabled="!status.running"
      >
        ⏹ 停止
      </button>
      <span v-if="!selected && !status.busy" class="hint"
        >⬅ 请先选择一个副本</span
      >
    </div>
  </div>
</template>

<style scoped>
.char-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.char-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: #f8f9fa;
  border: 2px solid transparent;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s;
}
.char-row:hover {
  background: #f0f0f0;
}
.char-row.selected {
  border-color: #8b5cf6;
  background: #f5f3ff;
}
.char-dot {
  font-size: 18px;
  color: #8b5cf6;
  user-select: none;
  flex-shrink: 0;
  width: 22px;
  text-align: center;
}
.char-name {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  min-width: 80px;
}
.char-field {
  display: flex;
  align-items: center;
  gap: 6px;
}
.fl {
  font-size: 13px;
  color: #666;
}
.char-select {
  padding: 6px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 13px;
  background: white;
  outline: none;
  cursor: pointer;
}
.char-select:focus {
  border-color: #8b5cf6;
}
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  cursor: pointer;
  user-select: none;
}
.char-check {
  width: 16px;
  height: 16px;
  accent-color: #8b5cf6;
  cursor: pointer;
}
.char-num {
  width: 64px;
  padding: 6px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 13px;
  text-align: center;
  outline: none;
}
.char-num:focus {
  border-color: #8b5cf6;
}
.char-num::-webkit-outer-spin-button,
.char-num::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.stamina {
  margin-left: auto;
  flex-shrink: 0;
}
.val {
  font-size: 16px;
  font-weight: 700;
  color: #f59e0b;
}
.unit {
  font-size: 11px;
  color: #666;
  margin-left: 2px;
}
.start-area {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 20px;
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
.hint {
  font-size: 13px;
  color: #f59e0b;
  font-weight: 500;
}
</style>
