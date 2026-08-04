import { useCallback, useMemo, type ReactNode } from 'react'
import { useLocalStorage } from '../hooks/useLocalStorage'
import { initialData } from '../data/initialData'
import { createId } from '../lib/id'
import type { AppData, Task, TodoItem } from '../types'
import { TaskStoreContext, type TaskStore } from './context'

const STORAGE_KEY = 'task-app:data:v1'

/** localStorage から読み込んだ値が想定する形かを判定する */
function isAppData(value: unknown): value is AppData {
  if (typeof value !== 'object' || value === null) return false
  const data = value as Partial<AppData>
  return Array.isArray(data.categories) && Array.isArray(data.tasks)
}

export function TaskProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useLocalStorage<AppData>(
    STORAGE_KEY,
    initialData,
    isAppData,
  )

  /** 指定タスクだけを差し替える共通処理 */
  const updateTask = useCallback(
    (taskId: string, updater: (task: Task) => Task) => {
      setData((prev) => ({
        ...prev,
        tasks: prev.tasks.map((task) =>
          task.id === taskId ? updater(task) : task,
        ),
      }))
    },
    [setData],
  )

  /** 指定タスクの項目リストだけを差し替える共通処理 */
  const updateItems = useCallback(
    (taskId: string, updater: (items: TodoItem[]) => TodoItem[]) => {
      updateTask(taskId, (task) => ({ ...task, items: updater(task.items) }))
    },
    [updateTask],
  )

  const store = useMemo<TaskStore>(() => {
    return {
      categories: data.categories,
      tasks: data.tasks,

      getCategory: (categoryId) =>
        data.categories.find((category) => category.id === categoryId),

      getTasksByCategory: (categoryId) =>
        data.tasks
          .filter((task) => task.categoryId === categoryId)
          .sort((a, b) => a.createdAt.localeCompare(b.createdAt)),

      getTask: (taskId) => data.tasks.find((task) => task.id === taskId),

      addTask: (categoryId, title) => {
        const task: Task = {
          id: createId('task'),
          categoryId,
          title: title.trim(),
          items: [],
          createdAt: new Date().toISOString(),
        }
        setData((prev) => ({ ...prev, tasks: [...prev.tasks, task] }))
        return task
      },

      renameTask: (taskId, title) => {
        const trimmed = title.trim()
        if (!trimmed) return
        updateTask(taskId, (task) => ({ ...task, title: trimmed }))
      },

      deleteTask: (taskId) => {
        setData((prev) => ({
          ...prev,
          tasks: prev.tasks.filter((task) => task.id !== taskId),
        }))
      },

      addItem: (taskId, text) => {
        const trimmed = text.trim()
        if (!trimmed) return
        updateItems(taskId, (items) => [
          ...items,
          { id: createId('item'), text: trimmed, checked: false },
        ])
      },

      updateItemText: (taskId, itemId, text) => {
        const trimmed = text.trim()
        if (!trimmed) return
        updateItems(taskId, (items) =>
          items.map((item) =>
            item.id === itemId ? { ...item, text: trimmed } : item,
          ),
        )
      },

      toggleItem: (taskId, itemId) => {
        updateItems(taskId, (items) =>
          items.map((item) =>
            item.id === itemId ? { ...item, checked: !item.checked } : item,
          ),
        )
      },

      deleteItem: (taskId, itemId) => {
        updateItems(taskId, (items) =>
          items.filter((item) => item.id !== itemId),
        )
      },
    }
  }, [data, setData, updateTask, updateItems])

  return (
    <TaskStoreContext.Provider value={store}>
      {children}
    </TaskStoreContext.Provider>
  )
}
