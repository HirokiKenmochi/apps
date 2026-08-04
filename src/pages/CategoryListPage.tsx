import { Link } from 'react-router-dom'
import Header from '../components/Header'
import { getCategoryTheme } from '../data/initialData'
import { isTaskDone, useTaskStore } from '../store/context'

export default function CategoryListPage() {
  const { categories, getTasksByCategory } = useTaskStore()

  return (
    <div className="flex min-h-full flex-col">
      <Header title="タスク管理" />

      <main className="flex-1 p-4">
        <p className="mb-3 px-1 text-sm text-slate-500">
          カテゴリを選んでタスクを確認できます。
        </p>

        {categories.length === 0 ? (
          <p className="py-20 text-center text-sm text-slate-500">
            カテゴリがありません。
          </p>
        ) : (
          <ul className="flex flex-col gap-3">
            {categories.map((category) => {
              const tasks = getTasksByCategory(category.id)
              const done = tasks.filter(isTaskDone).length
              const total = tasks.length
              const percent = total === 0 ? 0 : Math.round((done / total) * 100)
              const theme = getCategoryTheme(category.id)

              return (
                <li key={category.id}>
                  <Link
                    to={`/category/${category.id}`}
                    className={`flex min-h-20 items-center gap-3 overflow-hidden rounded-2xl border ${theme.border} ${theme.soft} active:opacity-80`}
                  >
                    <span
                      aria-hidden="true"
                      className={`h-20 w-1.5 shrink-0 ${theme.bar}`}
                    />
                    <span className="min-w-0 flex-1 py-3">
                      <span className="block truncate text-base font-bold text-slate-800">
                        {category.name}
                      </span>
                      <span
                        className={`mt-1 block text-sm font-medium ${theme.text}`}
                      >
                        完了 {done} / {total}
                      </span>
                      <span className="mt-2 block h-1.5 w-full overflow-hidden rounded-full bg-white">
                        <span
                          className={`block h-full rounded-full ${theme.bar} transition-[width] duration-300`}
                          style={{ width: `${percent}%` }}
                        />
                      </span>
                    </span>
                    <svg
                      viewBox="0 0 24 24"
                      className="mr-4 h-5 w-5 shrink-0 text-slate-400"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={2}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M9 6l6 6-6 6" />
                    </svg>
                  </Link>
                </li>
              )
            })}
          </ul>
        )}
      </main>
    </div>
  )
}
