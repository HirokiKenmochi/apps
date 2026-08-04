import { useEffect, useRef, useState } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router-dom'
import Header from '../components/Header'
import TextInputSheet from '../components/TextInputSheet'
import ConfirmDialog from '../components/ConfirmDialog'
import SwipeToDeleteRow from '../components/SwipeToDeleteRow'
import { getCategoryTheme } from '../data/initialData'
import { countItems, useTaskStore } from '../store/context'
import type { TodoItem } from '../types'

export default function TaskDetailPage() {
  const { categoryId = '', taskId = '' } = useParams()
  const navigate = useNavigate()
  const {
    getCategory,
    getTask,
    renameTask,
    deleteTask,
    addItem,
    updateItemText,
    toggleItem,
    deleteItem,
  } = useTaskStore()

  const [editingTitle, setEditingTitle] = useState(false)
  const [titleDraft, setTitleDraft] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<TodoItem | null>(null)
  const [deleteItemTarget, setDeleteItemTarget] = useState<TodoItem | null>(null)
  const [deleteTaskOpen, setDeleteTaskOpen] = useState(false)
  const titleInputRef = useRef<HTMLInputElement>(null)

  const category = getCategory(categoryId)
  const task = getTask(taskId)

  useEffect(() => {
    if (editingTitle) titleInputRef.current?.focus()
  }, [editingTitle])

  if (!category) return <Navigate to="/" replace />
  if (!task) return <Navigate to={`/category/${categoryId}`} replace />

  const theme = getCategoryTheme(categoryId)
  const { done, total } = countItems(task)

  const startTitleEdit = () => {
    setTitleDraft(task.title)
    setEditingTitle(true)
  }

  const commitTitle = () => {
    renameTask(task.id, titleDraft)
    setEditingTitle(false)
  }

  return (
    <div className="flex min-h-full flex-col">
      <Header
        title={category.name}
        backTo={`/category/${categoryId}`}
        right={
          <button
            type="button"
            aria-label="このタスクを削除"
            onClick={() => setDeleteTaskOpen(true)}
            className="flex h-11 min-w-11 items-center justify-center rounded-lg text-slate-500 active:bg-slate-100"
          >
            <svg
              viewBox="0 0 24 24"
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14" />
            </svg>
          </button>
        }
      />

      <main className="flex-1 p-4">
        <section className={`mb-5 rounded-xl ${theme.soft} p-4`}>
          {editingTitle ? (
            <input
              ref={titleInputRef}
              value={titleDraft}
              onChange={(event) => setTitleDraft(event.target.value)}
              onBlur={commitTitle}
              onKeyDown={(event) => {
                if (event.key === 'Enter') commitTitle()
                if (event.key === 'Escape') setEditingTitle(false)
              }}
              enterKeyHint="done"
              className="min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-lg font-bold text-slate-800 outline-none"
            />
          ) : (
            <button
              type="button"
              onClick={startTitleEdit}
              className="flex min-h-11 w-full items-center text-left text-lg font-bold text-slate-800"
            >
              {task.title}
            </button>
          )}
          <p className={`mt-1 text-sm font-medium ${theme.text}`}>
            {total === 0 ? '項目なし' : `完了 ${done} / ${total}`}
            <span className="ml-2 text-xs font-normal text-slate-500">
              タイトルをタップで編集
            </span>
          </p>
        </section>

        <p className="mb-2 px-1 text-xs font-bold text-slate-500">行う内容</p>

        {task.items.length === 0 ? (
          <p className="py-16 text-center text-sm leading-relaxed text-slate-500">
            行う内容がまだありません。
            <br />
            下の「＋ 項目を追加」から追加できます。
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {task.items.map((item) => (
              <li key={item.id}>
                <SwipeToDeleteRow onRequestDelete={() => setDeleteItemTarget(item)}>
                  <div className="flex items-center border border-slate-200 bg-white">
                    <button
                      type="button"
                      role="checkbox"
                      aria-checked={item.checked}
                      onClick={() => toggleItem(task.id, item.id)}
                      className="flex min-h-12 flex-1 items-center gap-3 px-3 py-2 text-left active:bg-slate-50"
                    >
                      <span
                        className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-md border-2 ${
                          item.checked
                            ? `${theme.bar} border-transparent text-white`
                            : 'border-slate-300 bg-white'
                        }`}
                      >
                        {item.checked ? (
                          <svg
                            viewBox="0 0 24 24"
                            className="h-4 w-4"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth={3}
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            aria-hidden="true"
                          >
                            <path d="M5 13l4 4L19 7" />
                          </svg>
                        ) : null}
                      </span>
                      <span
                        className={`min-w-0 flex-1 break-words ${
                          item.checked
                            ? 'text-slate-400 line-through'
                            : 'text-slate-800'
                        }`}
                      >
                        {item.text}
                      </span>
                    </button>
                    <button
                      type="button"
                      aria-label="この項目を編集"
                      onClick={() => setEditTarget(item)}
                      className="flex h-12 min-w-11 items-center justify-center text-slate-400 active:bg-slate-100"
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
            ))}
          </ul>
        )}

        {task.items.length > 0 ? (
          <p className="mt-3 px-1 text-xs text-slate-400">
            項目は左スワイプ、または長押しで削除できます。
          </p>
        ) : null}
      </main>

      <div className="sticky bottom-0 border-t border-slate-200 bg-white p-4">
        <button
          type="button"
          onClick={() => setAddOpen(true)}
          className="min-h-12 w-full rounded-xl bg-slate-800 text-base font-bold text-white active:bg-slate-700"
        >
          ＋ 項目を追加
        </button>
      </div>

      <TextInputSheet
        open={addOpen}
        title="行う内容を追加"
        placeholder="例: 資料をまとめる"
        submitLabel="追加"
        onSubmit={(value) => addItem(task.id, value)}
        onClose={() => setAddOpen(false)}
      />

      <TextInputSheet
        open={editTarget !== null}
        title="行う内容を編集"
        initialValue={editTarget?.text ?? ''}
        onSubmit={(value) =>
          editTarget && updateItemText(task.id, editTarget.id, value)
        }
        onClose={() => setEditTarget(null)}
      />

      <ConfirmDialog
        open={deleteItemTarget !== null}
        title="項目を削除しますか？"
        message={deleteItemTarget ? `「${deleteItemTarget.text}」を削除します。` : ''}
        onConfirm={() =>
          deleteItemTarget && deleteItem(task.id, deleteItemTarget.id)
        }
        onClose={() => setDeleteItemTarget(null)}
      />

      <ConfirmDialog
        open={deleteTaskOpen}
        title="タスクを削除しますか？"
        message={`「${task.title}」を項目ごと削除します。`}
        onConfirm={() => {
          deleteTask(task.id)
          navigate(`/category/${categoryId}`, { replace: true })
        }}
        onClose={() => setDeleteTaskOpen(false)}
      />
    </div>
  )
}
