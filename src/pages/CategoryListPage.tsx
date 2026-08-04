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
        <ul className="flex flex-col gap-3">
          {categories.map((category) => {
            const tasks = getTasksByCategory(category.id)
            const done = tasks.filter(isTaskDone).length
            const theme = getCategoryTheme(category.id)

            return (
              <li key={category.id}>
                <Link
                  to={`/category/${category.id}`}
                  className={`flex min-h-16 items-center gap-3 rounded-xl border ${theme.border} ${theme.soft} px-4 py-3`}
                >
                  <span className="flex-1 text-base font-bold text-slate-800">
                    {category.name}
                  </span>
                  <span className={`text-sm font-medium ${theme.text}`}>
                    完了 {done} / {tasks.length}
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
      </main>
    </div>
  )
}
