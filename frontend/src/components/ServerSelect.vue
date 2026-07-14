<script setup lang="ts">
import { ref } from "vue";

const emit = defineEmits<{ selected: [key: string] }>();
const selected = ref("");
const errorMsg = ref("");

function getApi() {
  return (window as any).pywebview?.api;
}

async function selectServer(key: string) {
  selected.value = key;
  errorMsg.value = "";
  const api = getApi();
  if (!api) return;
  const result = await api.set_server(key);
  if (result?.success) {
    emit("selected", key);
  } else {
    errorMsg.value = result?.message || "选择失败";
    selected.value = ""; // reset so user can re-try
  }
}
</script>

<template>
  <div class="server-select-overlay">
    <div class="bg-layer">
      <img src="../assets/server_bg.jpeg" class="bg-gif" />
    </div>
    <div class="server-select-card">
      <h1>瑞玛丽小助手</h1>
      <p class="sub">请选择区服</p>
      <p v-if="errorMsg" class="error-msg">⚠️ {{ errorMsg }}</p>
      <div class="server-buttons">
        <button
          :class="['server-btn', 'cn', { active: selected === 'cn' }]"
          @click="selectServer('cn')"
          :disabled="!!selected"
        >
          🇨🇳 国服
        </button>
        <button
          :class="['server-btn', 'global', { active: selected === 'global' }]"
          @click="selectServer('global')"
          :disabled="!!selected"
        >
          🌍 Etheria Global
        </button>
        <button
          :class="['server-btn', 'asia', { active: selected === 'asia' }]"
          @click="selectServer('asia')"
          :disabled="!!selected"
        >
          🌏 東亞服
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.server-select-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
  background: #000;
}
.bg-layer {
  position: absolute;
  inset: 0;
  overflow: hidden;
}
.bg-gif {
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.35;
}
.server-select-card {
  position: relative;
  text-align: center;
  padding: 48px;
  border-radius: 16px;
  background: #16213ecc;
  backdrop-filter: blur(6px);
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.4);
}
h1 {
  color: #fff;
  font-size: 28px;
  margin-bottom: 8px;
}
.sub {
  color: #aaa;
  font-size: 14px;
  margin-bottom: 20px;
}
.error-msg {
  color: #f59e0b;
  font-size: 13px;
  margin-bottom: 20px;
  max-width: 320px;
}
.server-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
}
.server-btn {
  padding: 14px 32px;
  border: 2px solid #444;
  border-radius: 10px;
  background: #1a1a2ecc;
  color: #ccc;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s;
}
.server-btn:hover:not(:disabled) {
  border-color: #8b5cf6;
  color: #fff;
}
.server-btn.active {
  border-color: #8b5cf6;
  background: #8b5cf6;
  color: #fff;
}
.server-btn:disabled {
  opacity: 0.5;
  cursor: default;
}
</style>
