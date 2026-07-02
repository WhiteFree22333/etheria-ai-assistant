<script setup lang="ts">
import { inject, onMounted, ref } from 'vue'
import type { Character } from '../../types'
import CharacterList from '../CharacterList.vue'

const charListRef = ref<any>(null)
const registerTask = inject<(order: number, name: string, fn: () => Promise<boolean>) => void>('registerTask', () => {})

onMounted(() => {
  registerTask(11, '源器', async () => {
    const list = charListRef.value
    const ch = characters.find(c => c.id === list?.selected)
    if (!ch) return true
    const api = window.pywebview?.api as any
    if (!api) return false
    for (let i = 0; i < ch.totalCount; i++) {
      const ok = await api.run_yuanqi_battle(ch.name, ch.difficulty, ch.streak, ch.doubleStamina ?? false)
      if (!ok) return false
    }
    return true
  })
})

const characters: Character[] = [
  { id: 'chonggou', name: '重构兵祸', difficulty: '炼狱', streak: 1, totalCount: 1, doubleStamina: false },
  { id: 'duoqi', name: '多琪',     difficulty: '炼狱', streak: 1, totalCount: 1, doubleStamina: false },
  { id: 'aoluola', name: '奥洛拉',  difficulty: '炼狱', streak: 1, totalCount: 1, doubleStamina: false },
  { id: 'weisipeila', name: '维斯佩拉', difficulty: '炼狱', streak: 1, totalCount: 1, doubleStamina: false },
]
</script>

<template>
  <CharacterList ref="charListRef"
    title="yuanqi"
    :characters="characters"
    :difficulty-options="['炼狱', '地狱四']"
    :stamina-per-battle="10"
    :show-double-stamina="true"
  />
</template>
