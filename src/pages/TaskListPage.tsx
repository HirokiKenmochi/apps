import { Link, Navigate, useParams } from 'react-router-dom'
import Header from '../components/Header'
import { countItems, isTaskDone, useTaskStore } from '../store/context'

export default function TaskListPage() {
  const { categoryId = '' } = useParams()
  const { getCategory, getTasksByCategory } = useTaskStore()
  const category = getCategory(categoryId)

  if (!category) return <Navigate to="/" replace />

  const tasks = getTasksByCategory(categoryId)

  return (
    <div className="flex min-h-full flex-col">
      <Header title={category.name} backTo="/" />

      <main className="flex-1 p-4">
        {tasks.length === 0 ? (
          <p className="py-16 text-center text-sm text-slate-500">
            タスクがまだありません。
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {tasks.map((task) => {
              const { done, total } = countItems(task)
              const completed = isTaskDone(task)

              return (
                <li key={task.id}>
                  <Link
                    to={`/category/${categoryId}/task/${task.id}`}
                    className="flex min-h-14 items-center gap-3 rounded-xl border border-slate-200 px-4 py-3"
                  >
                    <span
                      className={`flex-1 ${completed ? 'text-slate-400 line-through' : 'text-slate-800'}`}
                    >
                      {task.title}
                    </span>
                    <span className="text-sm text-slate-500">
                      {done}/{total}
                    </span>
                  </Link>
                </li>
              )
            })}
          </ul>
        )}
      </main>

      <div className="p-4">
        <button
          type="button"
          className="min-h-12 w-full rounded-xl bg-slate-800 font-bold text-white"
        >
          ＋ タスクを追加
        </button>
      </div>
    </div>
  )
}
