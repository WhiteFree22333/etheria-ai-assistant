<script setup lang="ts">
import { inject, onMounted, ref } from "vue";
import type { Character } from "../types";
import CharacterList from "./CharacterList.vue";
import TemplateCapture from "./TemplateCapture.vue";

const yuanwangRef = ref<any>(null);
const xujinRef = ref<any>(null);
const addLog = inject<(msg: string) => void>("addLog", () => {});
const registerTask = inject<
  (order: number, name: string, fn: () => Promise<boolean>) => void
>("registerTask", () => {});

const subTab = ref("yuanwang");
const subTabs = [
  { id: "yuanwang", label: "源网征令" },
  { id: "xujin", label: "虚烬探索" },
];

// 源网征令角色配置
const yuanwangCharacters: Character[] = [
  {
    id: "yuanwang",
    name: "源网征令",
    difficulty: "普通",
    streak: 1,
    totalCount: 1,
  },
];
// 虚烬探索角色配置
const xujinCharacters: Character[] = [
  {
    id: "xujin",
    name: "虚烬探索",
    difficulty: "普通",
    streak: 1,
    totalCount: 1,
  },
];

onMounted(() => {
  registerTask(21, "源网征令", async () => {
    const list = yuanwangRef.value;
    const ch = yuanwangCharacters.find((c) => c.id === list?.selected);
    if (!ch) return true;
    const api = window.pywebview?.api as any;
    if (!api) return false;
    for (let i = 0; i < ch.totalCount; i++) {
      const ok = await api.run_yuanwang_battle(
        ch.name,
        ch.difficulty,
        ch.streak
      );
      if (!ok) return false;
    }
    return true;
  });
  registerTask(23, "虚烬探索", async () => {
    const list = xujinRef.value;
    const ch = xujinCharacters.find((c) => c.id === list?.selected);
    if (!ch) return true;
    const api = window.pywebview?.api as any;
    if (!api) return false;
    for (let i = 0; i < ch.totalCount; i++) {
      const ok = await api.run_xujin_battle(ch.name, ch.difficulty, ch.streak);
      if (!ok) return false;
    }
    return true;
  });
});

// 截图保存功能 — 保存到 templates/shilian/ 子目录
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
    const result = await api.select_and_save_template(tplName.value, "shilian");
    if (result.success) {
      addLog(
        `模板已保存: shilian/${result.filename} (${result.region[2]}x${result.region[3]})`
      );
      const tpls = await api.list_templates("shilian");
      tplCount.value = (tpls || []).length;
      tplName.value = "";
    } else {
      addLog(result.message || "选取失败");
    }
  } catch (e: any) {
    addLog(`选取失败: ${e}`);
  }
}

// 调试：四路背景截图测试
async function testBgCapture() {
  const api = getApi();
  if (!api) return;
  addLog(
    "🔍 后台截图测试中… 请保持/遮挡游戏窗口后点击，对比 debug_screenshots/ 下的 4 张图"
  );
  try {
    await api.test_background_capture();
    addLog("✅ 测试截图完成 查看 debug_screenshots/bg_test_*.png");
  } catch (e: any) {
    addLog(`失败: ${e}`);
  }
}
</script>

<template>
  <section class="tab-panel">
    <h2>试炼挑战</h2>

    <!-- 子标签：源网征令 | 虚烬探索 -->
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

    <!-- 源网征令 — 每次只执行一次，无需次数选择 -->
    <div v-show="subTab === 'yuanwang'" class="sub-content">
      <CharacterList
        ref="yuanwangRef"
        title="yuanwang"
        :characters="yuanwangCharacters"
        :show-difficulty="false"
        :show-streak="false"
        :show-total-count="false"
        :show-stamina="false"
        :stamina-per-battle="30"
        :max-count="5"
      />
    </div>

    <!-- 虚烬探索 -->
    <div v-show="subTab === 'xujin'" class="sub-content">
      <CharacterList
        ref="xujinRef"
        title="xujin"
        :characters="xujinCharacters"
        :show-difficulty="false"
        :show-streak="false"
        :show-total-count="false"
        :show-stamina="false"
        :stamina-per-battle="30"
        :max-count="5"
      />
    </div>

    <!-- 截图保存模板（隐藏，需要时改 v-if="true"） -->
    <div v-if="true">
      <hr class="divider" />
      <div class="inline-form">
        <span class="hint-dir">→ templates/shilian/</span>
        <input
          type="text"
          v-model="tplName"
          placeholder="模板名称（如：源网征令图标）"
          class="input-name"
        />
        <button class="btn-sm" @click="captureTemplate" :disabled="!tplName">
          🎯 截取图标
        </button>
        <span class="tpl-count" v-if="tplCount">已存 {{ tplCount }} 个</span>
        <button class="btn-sm btn-test" @click="testBgCapture">
          🔍 后台截图测试
        </button>
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

/* 子标签 — 与 DailyPage/EventPage 统一样式 */
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

.sub-content {
  flex: 1;
}

/* 占位 */
.placeholder {
  text-align: center;
  color: #666;
  padding: 60px 0;
}
.icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}
.placeholder p {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}
.sub {
  font-size: 13px;
  color: #666;
  margin-top: 4px;
  font-weight: 400;
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
.btn-test {
  background: #f59e0b;
}
.btn-test:hover {
  background: #d97706;
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
