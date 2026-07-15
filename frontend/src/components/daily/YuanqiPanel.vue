<script setup lang="ts">
import { inject, onMounted, ref, type Ref } from 'vue'
import type { RunStatus } from '../../types'

const addLog = inject<(msg: string) => void>("addLog")!;
const status = inject<Ref<RunStatus>>("status")!;

const characters = ref([
  { id: 'chonggou',   name: '重构兵祸', difficulty: '炼狱',   streak: 1, totalCount: 1, checked: false, doubleStamina: false },
  { id: 'duoqi',      name: '多琪',     difficulty: '炼狱',   streak: 1, totalCount: 1, checked: false, doubleStamina: false },
  { id: 'aoluola',    name: '奥洛拉',   difficulty: '炼狱',   streak: 1, totalCount: 1, checked: false, doubleStamina: false },
  { id: 'weisipeila', name: '维斯佩拉', difficulty: '炼狱',   streak: 1, totalCount: 1, checked: false, doubleStamina: false },
]);

function fixInt(obj: any, field: string) {
  if (!Number.isInteger(obj[field]) || obj[field] < 1) obj[field] = 1;
  else if (obj[field] > 99) obj[field] = 99;
}

const STAMINA_PER_BATTLE = 10;

const registerTask = inject<(order: number, name: string, fn: () => Promise<boolean>) => void>('registerTask', () => {})
function getApi() { return window.pywebview?.api; }

onMounted(() => {
  registerTask(11, '源器', async () => {
    const selected = characters.value.filter(c => c.checked);
    if (selected.length === 0) return true;
    const api = window.pywebview?.api as any;
    if (!api) return false;
    for (const ch of selected) {
      for (let i = 0; i < ch.totalCount; i++) {
        const ok = await api.run_yuanqi_battle(ch.name, ch.difficulty, ch.streak, ch.doubleStamina ?? false);
        if (!ok) return false;
      }
    }
    return true;
  })
})

async function startAll() {
  const selected = characters.value.filter(c => c.checked);
  if (selected.length === 0) { addLog("请至少勾选一项"); return; }
  if (status.value.busy) return;
  status.value = { running: true, busy: true };
  const extra = (ch: any) => ch.doubleStamina ? '·双倍' : '';
  addLog(`源器一键执行: ${selected.map(c => c.name + '·' + c.difficulty + extra(c)).join("、")}...`);
  try {
    for (const ch of selected) {
      if (!status.value.running) break;
      const dbl = ch.doubleStamina ? ' · 双倍' : '';
      addLog(`--- ${ch.name} · ${ch.difficulty}${dbl} · ${ch.streak}场×${ch.totalCount}次 = ${ch.streak * ch.totalCount * STAMINA_PER_BATTLE}体力 ---`);
      const api = getApi();
      if (!api) continue;
      for (let i = 0; i < ch.totalCount; i++) {
        if (!status.value.running) break;
        addLog(`第 ${i + 1}/${ch.totalCount} 次`);
        const ok = await api.run_yuanqi_battle(ch.name, ch.difficulty, ch.streak, ch.doubleStamina ?? false);
        if (!ok) { addLog(`${ch.name} 执行失败`); break; }
        if (i < ch.totalCount - 1) await new Promise(r => setTimeout(r, 3000));
      }
    }
  } catch (e: any) { addLog(`执行异常: ${e}`); }
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
  <div class="yuanqi-root">
    <div class="char-list">
      <label v-for="ch in characters" :key="ch.id" class="char-row">
        <input type="checkbox" v-model="ch.checked" class="char-check" />
        <span class="char-name">{{ ch.name }}</span>
        <div class="char-field">
          <label class="fl">难度</label>
          <select v-model="ch.difficulty" class="char-select">
            <option value="炼狱">炼狱</option>
            <option value="地狱四">地狱四</option>
          </select>
        </div>
        <div class="char-field">
          <label class="fl">场次</label>
          <input type="number" v-model.number="ch.streak" class="char-num" min="1" max="99" @input="fixInt(ch, 'streak')" />
        </div>
        <div class="char-field">
          <label class="fl">总次数</label>
          <input type="number" v-model.number="ch.totalCount" class="char-num" min="1" max="99" @input="fixInt(ch, 'totalCount')" />
        </div>
        <div class="char-field">
          <label class="checkbox-label">
            <input type="checkbox" v-model="ch.doubleStamina" class="char-checkbox" />双倍
          </label>
        </div>
        <div class="char-field stamina">
          <span class="val">{{ ch.streak * ch.totalCount * STAMINA_PER_BATTLE * (ch.doubleStamina ? 2 : 1) }}</span>
          <span class="unit">体力</span>
        </div>
      </label>
    </div>
    <div class="start-area">
      <button class="btn btn-primary" @click="startAll" :disabled="status.busy">{{ status.busy ? "执行中..." : "▶ 开始执行" }}</button>
      <button class="btn btn-danger" @click="stopTask" :disabled="!status.running">停止</button>
      <span v-if="characters.filter(c => c.checked).length === 0 && !status.busy" class="hint">请先勾选要执行的项目</span>
    </div>
  </div>
</template>

<style scoped>
.char-list { display: flex; flex-direction: column; gap: 6px; }
.char-row { display: flex; align-items: center; gap: 12px; padding: 14px 16px; background: #f8f9fa; border: 2px solid transparent; border-radius: 10px; cursor: pointer; transition: all 0.15s; }
.char-row:hover { background: #f0f0f0; }
.char-check { width: 18px; height: 18px; accent-color: #8b5cf6; cursor: pointer; }
.char-name { font-size: 15px; font-weight: 600; color: #333; min-width: 80px; }
.char-field { display: flex; align-items: center; gap: 6px; }
.fl { font-size: 13px; color: #666; }
.char-select { padding: 6px 10px; border: 1px solid #e5e7eb; border-radius: 6px; font-size: 13px; background: white; outline: none; cursor: pointer; }
.char-select:focus { border-color: #8b5cf6; }
.char-num { width: 64px; padding: 6px 10px; border: 1px solid #e5e7eb; border-radius: 6px; font-size: 13px; text-align: center; outline: none; }
.char-num:focus { border-color: #8b5cf6; }
.char-num::-webkit-outer-spin-button, .char-num::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.checkbox-label { display: flex; align-items: center; gap: 4px; font-size: 13px; cursor: pointer; user-select: none; }
.char-checkbox { width: 16px; height: 16px; accent-color: #8b5cf6; cursor: pointer; }
.stamina { margin-left: auto; flex-shrink: 0; }
.val { font-size: 16px; font-weight: 700; color: #f59e0b; }
.unit { font-size: 11px; color: #666; margin-left: 2px; }
.start-area { display: flex; align-items: center; gap: 12px; margin-top: 20px; }
.btn { padding: 10px 20px; border: none; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #8b5cf6; color: white; }
.btn-primary:hover:not(:disabled) { background: #7c3aed; }
.btn-danger { background: #ef4444; color: white; }
.btn-danger:hover:not(:disabled) { background: #dc2626; }
.hint { font-size: 13px; color: #f59e0b; font-weight: 500; }
</style>
