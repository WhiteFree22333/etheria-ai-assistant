<script setup lang="ts">
import { inject, onMounted, ref } from 'vue'
import type { Character } from '../../types'
import CharacterList from '../CharacterList.vue'

const charListRef = ref<any>(null)
const registerTask = inject<(order: number, name: string, fn: () => Promise<boolean>) => void>('registerTask', () => {})

const characters: Character[] = [
  { id: 'nikenana',  name: '尼可娜娜', difficulty: '炼狱', streak: 1, totalCount: 1 },
  { id: 'shalun',    name: '莎朗',     difficulty: '炼狱', streak: 1, totalCount: 1 },
  { id: 'heyan',     name: '赫妍',     difficulty: '炼狱', streak: 1, totalCount: 1 },
  { id: 'lianyujin', name: '炼狱津',   difficulty: '炼狱', streak: 1, totalCount: 1 },
  { id: 'keluoluo',  name: '柯洛罗',   difficulty: '炼狱', streak: 1, totalCount: 1 },
  { id: 'heerjide',  name: '赫尔基德', difficulty: '炼狱', streak: 1, totalCount: 1 },
]

function staminaPerBattle(ch: Character): number {
  return ch.difficulty === '修罗' ? 50 : 10
}

onMounted(() => {
  registerTask(10, '智壳', async () => {
    const list = charListRef.value
    const ch = characters.find(c => c.id === list?.selected)
    if (!ch) return true  // nothing selected, skip
    const api = window.pywebview?.api as any
    if (!api) return false
    for (let i = 0; i < ch.totalCount; i++) {
      const ok = await api.run_zhike_battle(ch.name, ch.difficulty, ch.streak)
      if (!ok) return false
    }
    return true
  })
})
</script>

<template>
  <CharacterList ref="charListRef"
    title="zhike"
    :characters="characters"
    :difficulty-options="['炼狱', '修罗']"
    :stamina-per-battle="staminaPerBattle"
  />
</template>
