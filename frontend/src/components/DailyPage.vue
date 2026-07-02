<script setup lang="ts">
import { ref, inject } from "vue";
import ZhikePanel from "./daily/ZhikePanel.vue";
import YuanqiPanel from "./daily/YuanqiPanel.vue";
import GuildPanel from "./daily/GuildPanel.vue";
import QiannengPanel from "./daily/QiannengPanel.vue";
import TemplateCapture from "./TemplateCapture.vue";

const addLog = inject<(msg: string) => void>("addLog", () => {});

const subTab = ref("zhike");
const subTabs = [
  { id: "zhike", label: "智壳" },
  { id: "yuanqi", label: "源器" },
  { id: "guild", label: "公会/竞技场" },
  { id: "qianneng", label: "潜能/经验" },
];

const gwWidth = ref(960);
const gwHeight = ref(540);

async function resizeGame() {
  const api = window.pywebview?.api;
  if (!api) return;
  const result = await api.resize_game_window(gwWidth.value, gwHeight.value);
  addLog(result?.message || (result?.success ? "窗口已优化" : "缩放失败"));
}
</script>

<template>
  <section class="tab-panel">
    <div class="title-row">
      <h2>每日任务</h2>
      <div class="resize-group">
        <input
          type="number"
          v-model.number="gwWidth"
          class="rsz"
          min="640"
          max="1920"
        />
        <span class="rsz-x">×</span>
        <input
          type="number"
          v-model.number="gwHeight"
          class="rsz"
          min="360"
          max="1080"
        />
        <button class="btn-rsz" @click="resizeGame">📐 窗口缩放</button>
      </div>
    </div>
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
    <ZhikePanel v-show="subTab === 'zhike'" />
    <YuanqiPanel v-show="subTab === 'yuanqi'" />
    <GuildPanel v-show="subTab === 'guild'" />
    <QiannengPanel v-show="subTab === 'qianneng'" />
    <TemplateCapture v-if="false" />
  </section>
</template>

<style scoped>
.tab-panel {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  flex: 1;
}
.title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.title-row h2 {
  font-size: 18px;
  color: #333;
  margin: 0;
}
.resize-group {
  display: flex;
  align-items: center;
  gap: 4px;
}
.rsz {
  width: 52px;
  padding: 4px 6px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  font-size: 12px;
  text-align: center;
  outline: none;
}
.rsz:focus {
  border-color: #8b5cf6;
}
.rsz-x {
  color: #999;
  font-size: 12px;
}
.btn-rsz {
  padding: 4px 12px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  background: #10b981;
  color: white;
  white-space: nowrap;
}
.btn-rsz:hover {
  background: #059669;
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
</style>
