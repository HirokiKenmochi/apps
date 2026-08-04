/** カテゴリのアクセントカラー */
export type CategoryColor =
  | 'sky'
  | 'emerald'
  | 'amber'
  | 'violet'
  | 'rose'
  | 'slate'

export type Category = {
  id: string
  name: string // "学校" | "仕事" など
  /** 未指定の場合は既定色にフォールバックする */
  color?: CategoryColor
}

export type TodoItem = {
  id: string
  text: string // そのタスクで行う内容
  checked: boolean
}

export type Task = {
  id: string
  categoryId: string
  title: string // タスクタイトル
  items: TodoItem[] // 行う内容のリスト
  createdAt: string
}

export type AppData = {
  categories: Category[]
  tasks: Task[]
}
