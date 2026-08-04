import { createContext, useContext } from 'react'
import { countLeaves } from '../lib/items'
import type { Category, CategoryColor, Task } from '../types'

export type TaskStore = {
  categories: Category[]
  tasks: Task[]
  /** カテゴリを ID で取得（存在しなければ undefined） */
  getCategory: (categoryId: string) => Category | undefined
  /** カテゴリに属するタスクを作成日時の古い順で取得 */
  getTasksByCategory: (categoryId: string) => Task[]
  /** タスクを ID で取得（存在しなければ undefined） */
  getTask: (taskId: string) => Task | undefined

  addCategory: (name: string, color: CategoryColor) => Category
  updateCategory: (
    categoryId: string,
    patch: { name?: string; color?: CategoryColor },
  ) => void
  /** カテゴリと、それに属するタスクをまとめて削除する */
  deleteCategory: (categoryId: string) => void

  addTask: (categoryId: string, title: string) => Task
  renameTask: (taskId: string, title: string) => void
  deleteTask: (taskId: string) => void

  /** parentId を渡すとその項目のサブ項目として追加する */
  addItem: (
    taskId: string,
    text: string,
    options?: { description?: string; parentId?: string },
  ) => void
  updateItem: (
    taskId: string,
    itemId: string,
    patch: { text?: string; description?: string },
  ) => void
  /** 末端の項目のみ切り替わる（サブ項目を持つ項目は子から算出される） */
  toggleItem: (taskId: string, itemId: string) => void
  /** サブ項目ごと削除する */
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

/** 完了 / 全体 の件数を返す（数えるのは末端の項目のみ） */
export function countItems(task: Task) {
  return countLeaves(task.items)
}

/** 末端の項目がすべてチェック済みなら完了扱い（項目が 0 件のタスクは未完了） */
export function isTaskDone(task: Task) {
  const { done, total } = countLeaves(task.items)
  return total > 0 && done === total
}
