<script setup lang="ts">
import { ref, inject } from "vue";
import AnlongPanel from "./events/AnlongPanel.vue";
import ChaonengPanel from "./events/ChaonengPanel.vue";
const addLog = inject<(msg: string) => void>("addLog", () => {});

const subTab = ref("chaoneng");
const subTabs = [
  { id: "chaoneng", label: "超能二十一" },
  { id: "anlong", label: "暗笼激斗" },
];

// 截图保存功能 — 保存到 templates/huodong/
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
    const result = await api.select_and_save_template(tplName.value, "huodong");
    if (result.success) {
      addLog(
        `模板已保存: huodong/${result.filename} (${result.region[2]}x${result.region[3]})`
      );
      const tpls = await api.list_templates("huodong");
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
    <h2>活动</h2>
    <div class="sub-tabs">
      <button
        v-for="st in subTabs"
        :key="st.id"
        :class="['sub-tab', { active: subTab === st.id }]"
        @click="subTab = st.id"
      >
        {{ st.label }}
      </button>
    </div>
    <AnlongPanel v-show="subTab === 'anlong'" />
    <ChaonengPanel v-show="subTab === 'chaoneng'" />

    <div v-if="false" style="display:none">
    <hr class="divider" />
    <div class="inline-form">
      <span class="hint-dir">→ templates/huodong/</span>
      <input
        type="text"
        v-model="tplName"
        placeholder="模板名称（如：超能二十一图标）"
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
}
.tab-panel h2 {
  font-size: 18px;
  margin-bottom: 16px;
  color: #333;
}
.sub-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  background: #f3f4f6;
  border-radius: 8px;
  padding: 4px;
}
.sub-tab {
  flex: 1;
  padding: 8px 16px;
  border: none;
  background: transparent;
  color: #666;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
}
.sub-tab:hover {
  background: #e5e7eb;
}
.sub-tab.active {
  background: #8b5cf6;
  color: white;
}
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
