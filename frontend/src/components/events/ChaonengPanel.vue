<script setup lang="ts">
import { inject, onMounted, ref } from "vue";
import type { Character } from "../../types";
import CharacterList from "../CharacterList.vue";

const charListRef = ref<any>(null);
const registerTask = inject<
  (order: number, name: string, fn: () => Promise<boolean>) => void
>("registerTask", () => {});

onMounted(() => {
  registerTask(22, "超能二十一", async () => {
    const list = charListRef.value;
    const ch = characters.find((c) => c.id === list?.selected);
    if (!ch) return true;
    const api = window.pywebview?.api as any;
    if (!api) return false;
    // streak 即局数
    return api.run_chaoneng_battle(ch.name, ch.difficulty, ch.streak);
  });
});

const characters: Character[] = [
  {
    id: "chaoneng_boss",
    name: "超能二十一",
    difficulty: "普通",
    streak: 1,
    totalCount: 1,
  },
];
</script>

<template>
  <CharacterList
    ref="charListRef"
    title="chaoneng"
    :characters="characters"
    :show-difficulty="false"
    :show-total-count="false"
    :show-stamina="false"
    :stamina-per-battle="30"
    :max-count="500"
  />
</template>
