// 角色数据模型
export interface Character {
  id: string
  name: string
  difficulty: string
  streak: number
  totalCount: number
  doubleStamina?: boolean   // 源器专用：是否双倍消耗
}

// 运行状态
export interface RunStatus {
  running: boolean
  busy: boolean
}
