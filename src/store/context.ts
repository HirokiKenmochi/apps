import { createContext, useContext } from 'react'
import type { Category, Task } from '../types'

export type TaskStore = {
  categories: Category[]
  tasks: Task[]
  /** カテゴリを ID で取得（存在しなければ undefined） */
  getCategory: (categoryId: string) => Category | undefined
  /** カテゴリに属するタスクを作成日時の古い順で取得 */
  getTasksByCategory: (categoryId: string) => Task[]
  /** タスクを ID で取得（存在しなければ undefined） */
  getTask: (taskId: string) => Task | undefined

  addTask: (categoryId: string, title: string) => Task
  renameTask: (taskId: string, title: string) => void
  deleteTask: (taskId: string) => void

  addItem: (taskId: string, text: string) => void
  updateItemText: (taskId: string, itemId: string, text: string) => void
  toggleItem: (taskId: string, itemId: string) => void
  deleteItem: (taskId: string, itemId: string) => void
}

export const TaskStoreContext = createContext<TaskStore | null>(null)

export function useTaskStore(): TaskStore {
  const store = useContext(TaskStoreContext)
  if (!store) {
    throw new Error('useTaskStore は TaskProvider の内側で使用してください')
  }
  return store
}

/** チェック済み / 全体 の件数を返す */
export function countItems(task: Task) {
  const total = task.items.length
  const done = task.items.filter((item) => item.checked).length
  return { done, total }
}

/** すべての項目がチェック済みなら完了扱い（項目が 0 件のタスクは未完了） */
export function isTaskDone(task: Task) {
  return task.items.length > 0 && task.items.every((item) => item.checked)
}
