<script setup lang="ts">
import { inject, onMounted, ref } from "vue"
import type { Character } from "../../types"
import CharacterList from "../CharacterList.vue"

const charListRef = ref<any>(null)
const registerTask = inject<(order: number, name: string, fn: () => Promise<boolean>) => void>('registerTask', () => {})

onMounted(() => {
  registerTask(20, '暗笼激斗', async () => {
    const list = charListRef.value
    const ch = characters.find(c => c.id === list?.selected)
    if (!ch) return true  // nothing selected
    if (!ch) return true
    const api = window.pywebview?.api as any
    if (!api) return false
    for (let i = 0; i < ch.totalCount; i++) {
      const ok = await api.run_anlong_battle(ch.name, ch.difficulty, ch.streak)
      if (!ok) return false
    }
    return true
  })
})

const characters: Character[] = [
  { id: "anlong_boss", name: "暗笼激斗", difficulty: "普通", streak: 1, totalCount: 1 },
]
</script>

<template>
  <CharacterList ref="charListRef"
    title="anlong"
    :characters="characters"
    :show-difficulty="false"
    :show-streak="false"
    :show-stamina="false"
    :stamina-per-battle="30"
    :max-count="5"
  />
</template>
