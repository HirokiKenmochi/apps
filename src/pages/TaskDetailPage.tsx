import { Navigate, useParams } from 'react-router-dom'
import Header from '../components/Header'
import { useTaskStore } from '../store/context'

export default function TaskDetailPage() {
  const { categoryId = '', taskId = '' } = useParams()
  const { getCategory, getTask, toggleItem } = useTaskStore()
  const category = getCategory(categoryId)
  const task = getTask(taskId)

  if (!category) return <Navigate to="/" replace />
  if (!task) return <Navigate to={`/category/${categoryId}`} replace />

  return (
    <div className="flex min-h-full flex-col">
      <Header title={category.name} backTo={`/category/${categoryId}`} />

      <main className="flex-1 p-4">
        <h2 className="mb-4 text-xl font-bold text-slate-800">{task.title}</h2>

        <p className="mb-2 text-xs font-bold text-slate-500">行う内容</p>

        {task.items.length === 0 ? (
          <p className="py-12 text-center text-sm text-slate-500">
            行う内容がまだありません。
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {task.items.map((item) => (
              <li
                key={item.id}
                className="flex min-h-12 items-center gap-3 rounded-xl border border-slate-200 px-4 py-2"
              >
                <input
                  type="checkbox"
                  checked={item.checked}
                  onChange={() => toggleItem(task.id, item.id)}
                  className="h-5 w-5"
                />
                <span
                  className={
                    item.checked ? 'text-slate-400 line-through' : 'text-slate-800'
                  }
                >
                  {item.text}
                </span>
              </li>
            ))}
          </ul>
        )}
      </main>

      <div className="p-4">
        <button
          type="button"
          className="min-h-12 w-full rounded-xl bg-slate-800 font-bold text-white"
        >
          ＋ 項目を追加
        </button>
      </div>
    </div>
  )
}
