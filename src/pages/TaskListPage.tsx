import { useState } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router-dom'
import Header from '../components/Header'
import TextInputSheet from '../components/TextInputSheet'
import ConfirmDialog from '../components/ConfirmDialog'
import SwipeToDeleteRow from '../components/SwipeToDeleteRow'
import { getCategoryTheme } from '../data/initialData'
import { countItems, isTaskDone, useTaskStore } from '../store/context'
import type { Task } from '../types'

export default function TaskListPage() {
  const { categoryId = '' } = useParams()
  const navigate = useNavigate()
  const { getCategory, getTasksByCategory, addTask, deleteTask } = useTaskStore()

  const [addOpen, setAddOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Task | null>(null)

  const category = getCategory(categoryId)
  if (!category) return <Navigate to="/" replace />

  const tasks = getTasksByCategory(categoryId)
  const theme = getCategoryTheme(categoryId)

  return (
    <div className="flex flex-1 flex-col">
      <Header title={category.name} backTo="/" />

      <main className="flex-1 p-4">
        {tasks.length === 0 ? (
          <p className="py-20 text-center text-sm leading-relaxed text-slate-500">
            タスクがまだありません。
            <br />
            下の「＋ タスクを追加」から追加できます。
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {tasks.map((task) => {
              const { done, total } = countItems(task)
              const completed = isTaskDone(task)

              return (
                <li key={task.id}>
                  <SwipeToDeleteRow onRequestDelete={() => setDeleteTarget(task)}>
                    <button
                      type="button"
                      onClick={() =>
                        navigate(`/category/${categoryId}/task/${task.id}`)
                      }
                      className="flex min-h-14 w-full items-center gap-3 bg-white px-4 py-3 text-left active:bg-slate-50"
                    >
                      <span
                        className={`min-w-0 flex-1 truncate ${
                          completed
                            ? 'text-slate-400 line-through'
                            : 'text-slate-800'
                        }`}
                      >
                        {task.title}
                      </span>
                      <span
                        className={`shrink-0 text-sm font-medium ${
                          completed ? 'text-slate-400' : theme.text
                        }`}
                      >
                        {done}/{total}
                      </span>
                    </button>
                  </SwipeToDeleteRow>
                </li>
              )
            })}
          </ul>
        )}
      </main>

      <div className="pb-safe sticky bottom-0 border-t border-slate-200 bg-white p-4">
        <button
          type="button"
          onClick={() => setAddOpen(true)}
          className="min-h-12 w-full rounded-xl bg-slate-800 text-base font-bold text-white active:bg-slate-700"
        >
          ＋ タスクを追加
        </button>
      </div>

      <TextInputSheet
        open={addOpen}
        title="タスクを追加"
        placeholder="タスクのタイトル"
        submitLabel="追加"
        onSubmit={(value) => {
          const task = addTask(categoryId, value)
          navigate(`/category/${categoryId}/task/${task.id}`)
        }}
        onClose={() => setAddOpen(false)}
      />

      <ConfirmDialog
        open={deleteTarget !== null}
        title="タスクを削除しますか？"
        message={deleteTarget ? `「${deleteTarget.title}」を削除します。` : ''}
        onConfirm={() => deleteTarget && deleteTask(deleteTarget.id)}
        onClose={() => setDeleteTarget(null)}
      />
    </div>
  )
}
