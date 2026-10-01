<script setup lang="ts">
import { inject, onMounted, ref } from "vue";
import type { Character } from "../types";
import CharacterList from "./CharacterList.vue";

const zhuxianRef = ref<any>(null);
const addLog = inject<(msg: string) => void>("addLog", () => {});
const registerTask = inject<
  (order: number, name: string, fn: () => Promise<boolean>) => void
>("registerTask", () => {});

// 主线一次只推一关，没有次数选择
// doubleStamina：体力不足时是否自动用稳定值兑换体力（对应「是否自动使用体力」勾选框）
const zhuxianCharacters = ref<Character[]>([
  {
    id: "zhuxian",
    name: "主线剧情",
    difficulty: "普通",
    streak: 1,
    totalCount: 1,
    doubleStamina: false,
  },
]);

onMounted(() => {
  registerTask(20, "主线", async () => {
    const list = zhuxianRef.value;
    const ch = zhuxianCharacters.value.find((c) => c.id === list?.selected);
    if (!ch) return true;
    const api = window.pywebview?.api as any;
    if (!api) return false;
    // 不循环次数，跑一次就结束
    return await api.run_zhuxian_battle(
      ch.name,
      ch.difficulty,
      ch.streak,
      ch.doubleStamina ?? false
    );
  });
});

// 截图保存功能 — 保存到 templates/zhuxian/ 子目录
const tplName = ref("");
const tplCount = ref(0);
function getApi() {
  return window.pywebview?.api;
}

async function captureTemplate() {
  const api = getApi();
  if (!tplName.value || !api) return;
  addLog("正在截取游戏画面...");
  try {
    const result = await api.select_and_save_template(tplName.value, "zhuxian");
    if (result.success) {
      addLog(
        `模板已保存: zhuxian/${result.filename} (${result.region[2]}x${result.region[3]})`
      );
      const tpls = await api.list_templates("zhuxian");
      tplCount.value = (tpls || []).length;
      tplName.value = "";
    } else {
      addLog(result.message || "选取失败");
    }
  } catch (e: any) {
    addLog(`选取失败: ${e}`);
  }
}
</script>

<template>
  <section class="tab-panel">
    <h2>主线剧情</h2>

    <!-- 一次一关，无需次数选择 -->
    <div class="sub-content">
      <CharacterList
        ref="zhuxianRef"
        title="zhuxian"
        :characters="zhuxianCharacters"
        :show-difficulty="false"
        :show-streak="false"
        :show-total-count="false"
        :show-stamina="false"
        :stamina-per-battle="0"
        :show-double-stamina="true"
        :max-count="1"
        :doubleStaminaLabel="'是否自动使用体力'"
      />
    </div>

    <!-- 截图保存模板（隐藏，需要时改 v-if="true"） -->
    <div v-if="false">
      <hr class="divider" />
      <div class="inline-form">
        <span class="hint-dir">→ templates/zhuxian/</span>
        <input
          type="text"
          v-model="tplName"
          placeholder="模板名称（如：主线入口）"
          class="input-name"
        />
        <button class="btn-sm" @click="captureTemplate" :disabled="!tplName">
          🎯 截取图标
        </button>
        <span class="tpl-count" v-if="tplCount">已存 {{ tplCount }} 个</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.tab-panel {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  flex: 1;
  display: flex;
  flex-direction: column;
}
h2 {
  font-size: 18px;
  color: #333;
  margin: 0 0 16px 0;
}

.sub-content {
  flex: 1;
}

/* 模板截取工具 */
.divider {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 20px 0;
}
.inline-form {
  display: flex;
  gap: 8px;
  align-items: center;
}
.hint-dir {
  font-size: 11px;
  color: #999;
  white-space: nowrap;
}
.input-name {
  flex: 1;
  max-width: 220px;
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
}
.input-name:focus {
  border-color: #8b5cf6;
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
.btn-sm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.tpl-count {
  font-size: 12px;
  color: #666;
  white-space: nowrap;
}
</style>
