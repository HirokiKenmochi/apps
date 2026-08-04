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
  /** 項目の説明（任意） */
  description?: string
  /** 末端の項目のチェック状態。サブ項目を持つ項目では参照しない */
  checked: boolean
  /** サブ項目。入れ子は何段でも可 */
  children?: TodoItem[]
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
