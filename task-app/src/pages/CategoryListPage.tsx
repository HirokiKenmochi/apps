import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import CategoryFormSheet from '../components/CategoryFormSheet'
import ConfirmDialog from '../components/ConfirmDialog'
import SwipeToDeleteRow from '../components/SwipeToDeleteRow'
import { getCategoryTheme, resolveCategoryColor } from '../data/initialData'
import { isTaskDone, useTaskStore } from '../store/context'
import type { Category } from '../types'

export default function CategoryListPage() {
  const navigate = useNavigate()
  const {
    categories,
    getTasksByCategory,
    addCategory,
    updateCategory,
    deleteCategory,
  } = useTaskStore()

  const [addOpen, setAddOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Category | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Category | null>(null)

  const deleteTargetTaskCount = deleteTarget
    ? getTasksByCategory(deleteTarget.id).length
    : 0

  return (
    <div className="flex flex-1 flex-col">
      <Header title="タスク管理" />

      <main className="flex-1 p-4">
        {categories.length === 0 ? (
          <p className="py-20 text-center text-sm leading-relaxed text-slate-500">
            カテゴリがまだありません。
            <br />
            下の「＋ カテゴリを追加」から追加できます。
          </p>
        ) : (
          <>
            <p className="mb-3 px-1 text-sm text-slate-500">
              カテゴリを選んでタスクを確認できます。
            </p>
            <ul className="flex flex-col gap-3">
              {categories.map((category) => {
                const tasks = getTasksByCategory(category.id)
                const done = tasks.filter(isTaskDone).length
                const total = tasks.length
                const percent =
                  total === 0 ? 0 : Math.round((done / total) * 100)
                const theme = getCategoryTheme(category)

                return (
                  <li key={category.id}>
                    <SwipeToDeleteRow
                      onRequestDelete={() => setDeleteTarget(category)}
                    >
                      <div
                        className={`flex items-center gap-3 ${theme.soft} ${theme.border} border`}
                      >
                        <button
                          type="button"
                          onClick={() => navigate(`/category/${category.id}`)}
                          className="flex min-h-20 flex-1 items-center gap-3 text-left active:opacity-80"
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
                        </button>
                        <button
                          type="button"
                          aria-label={`${category.name}を編集`}
                          onClick={() => setEditTarget(category)}
                          className="mr-2 flex h-11 min-w-11 items-center justify-center rounded-lg text-slate-400 active:bg-white/60"
                        >
                          <svg
                            viewBox="0 0 24 24"
                            className="h-4 w-4"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth={2}
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            aria-hidden="true"
                          >
                            <path d="M4 20h4l10-10-4-4L4 16v4zM14 6l4 4" />
                          </svg>
                        </button>
                      </div>
                    </SwipeToDeleteRow>
                  </li>
                )
              })}
            </ul>
            <p className="mt-3 px-1 text-xs text-slate-400">
              カテゴリは左スワイプ、または長押しで削除できます。
            </p>
          </>
        )}
      </main>

      <div className="pb-safe sticky bottom-0 border-t border-slate-200 bg-white p-4">
        <button
          type="button"
          onClick={() => setAddOpen(true)}
          className="min-h-12 w-full rounded-xl bg-slate-800 text-base font-bold text-white active:bg-slate-700"
        >
          ＋ カテゴリを追加
        </button>
      </div>

      <CategoryFormSheet
        open={addOpen}
        title="カテゴリを追加"
        submitLabel="追加"
        onSubmit={(name, color) => addCategory(name, color)}
        onClose={() => setAddOpen(false)}
      />

      <CategoryFormSheet
        open={editTarget !== null}
        title="カテゴリを編集"
        initialName={editTarget?.name ?? ''}
        initialColor={editTarget ? resolveCategoryColor(editTarget) : 'sky'}
        onSubmit={(name, color) => {
          if (!editTarget) return
          updateCategory(editTarget.id, { name, color })
        }}
        onClose={() => setEditTarget(null)}
      />

      <ConfirmDialog
        open={deleteTarget !== null}
        title="カテゴリを削除しますか？"
        message={
          deleteTarget
            ? `「${deleteTarget.name}」${
                deleteTargetTaskCount > 0
                  ? `とその中のタスク ${deleteTargetTaskCount} 件`
                  : ''
              }を削除します。`
            : ''
        }
        onConfirm={() => deleteTarget && deleteCategory(deleteTarget.id)}
        onClose={() => setDeleteTarget(null)}
      />
    </div>
  )
}
