import { useEffect, useRef, useState } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router-dom'
import Header from '../components/Header'
import ItemFormSheet from '../components/ItemFormSheet'
import ConfirmDialog from '../components/ConfirmDialog'
import TodoItemList from '../components/TodoItemList'
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
    updateItem,
    toggleItem,
    deleteItem,
  } = useTaskStore()

  const [editingTitle, setEditingTitle] = useState(false)
  const [titleDraft, setTitleDraft] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  /** サブ項目の追加先。null なら最上位への追加 */
  const [addParent, setAddParent] = useState<TodoItem | null>(null)
  const [editTarget, setEditTarget] = useState<TodoItem | null>(null)
  const [deleteItemTarget, setDeleteItemTarget] = useState<TodoItem | null>(null)
  const [deleteTaskOpen, setDeleteTaskOpen] = useState(false)
  /** 折りたたみ中の項目 ID（表示上の状態なので保存はしない） */
  const [collapsedIds, setCollapsedIds] = useState<Set<string>>(new Set())
  const titleInputRef = useRef<HTMLInputElement>(null)

  const category = getCategory(categoryId)
  const task = getTask(taskId)

  useEffect(() => {
    if (editingTitle) titleInputRef.current?.focus()
  }, [editingTitle])

  if (!category) return <Navigate to="/" replace />
  if (!task) return <Navigate to={`/category/${categoryId}`} replace />

  const theme = getCategoryTheme(category)
  const { done, total } = countItems(task)

  const startTitleEdit = () => {
    setTitleDraft(task.title)
    setEditingTitle(true)
  }

  const commitTitle = () => {
    renameTask(task.id, titleDraft)
    setEditingTitle(false)
  }

  const toggleCollapse = (item: TodoItem) => {
    setCollapsedIds((prev) => {
      const next = new Set(prev)
      if (next.has(item.id)) next.delete(item.id)
      else next.add(item.id)
      return next
    })
  }

  const openAddSheet = (parent: TodoItem | null) => {
    setAddParent(parent)
    setAddOpen(true)
    // 追加先が折りたたまれていると追加した項目が見えないので開いておく
    if (parent) {
      setCollapsedIds((prev) => {
        if (!prev.has(parent.id)) return prev
        const next = new Set(prev)
        next.delete(parent.id)
        return next
      })
    }
  }

  return (
    <div className="flex flex-1 flex-col">
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
          <TodoItemList
            items={task.items}
            theme={theme}
            collapsedIds={collapsedIds}
            onToggleCollapse={toggleCollapse}
            onToggleCheck={(item) => toggleItem(task.id, item.id)}
            onAddChild={(item) => openAddSheet(item)}
            onEdit={(item) => setEditTarget(item)}
            onDelete={(item) => setDeleteItemTarget(item)}
          />
        )}

        {task.items.length > 0 ? (
          <p className="mt-3 px-1 text-xs leading-relaxed text-slate-400">
            ＋ でサブ項目を追加、✎ で内容と説明を編集できます。項目は左スワイプ、または長押しで削除できます。
          </p>
        ) : null}
      </main>

      <div className="pb-safe sticky bottom-0 border-t border-slate-200 bg-white p-4">
        <button
          type="button"
          onClick={() => openAddSheet(null)}
          className="min-h-12 w-full rounded-xl bg-slate-800 text-base font-bold text-white active:bg-slate-700"
        >
          ＋ 項目を追加
        </button>
      </div>

      <ItemFormSheet
        open={addOpen}
        title={
          addParent ? `「${addParent.text}」にサブ項目を追加` : '行う内容を追加'
        }
        submitLabel="追加"
        onSubmit={(text, description) =>
          addItem(task.id, text, {
            description,
            parentId: addParent?.id,
          })
        }
        onClose={() => {
          setAddOpen(false)
          setAddParent(null)
        }}
      />

      <ItemFormSheet
        open={editTarget !== null}
        title="行う内容を編集"
        initialText={editTarget?.text ?? ''}
        initialDescription={editTarget?.description ?? ''}
        onSubmit={(text, description) =>
          editTarget && updateItem(task.id, editTarget.id, { text, description })
        }
        onClose={() => setEditTarget(null)}
      />

      <ConfirmDialog
        open={deleteItemTarget !== null}
        title="項目を削除しますか？"
        message={
          deleteItemTarget
            ? `「${deleteItemTarget.text}」${
                deleteItemTarget.children?.length
                  ? `とそのサブ項目 ${deleteItemTarget.children.length} 件`
                  : ''
              }を削除します。`
            : ''
        }
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
