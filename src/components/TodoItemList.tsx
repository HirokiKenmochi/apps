import SwipeToDeleteRow from './SwipeToDeleteRow'
import { countLeaves, isItemDone, isLeaf } from '../lib/items'
import type { CategoryTheme } from '../data/initialData'
import type { TodoItem } from '../types'

/** 深すぎる階層で文字が読めなくならないよう、インデントは頭打ちにする */
const INDENT_PER_DEPTH = 18
const MAX_INDENT_DEPTH = 6

type Props = {
  items: TodoItem[]
  theme: CategoryTheme
  /** 表示上の階層（最上位は 0） */
  depth?: number
  collapsedIds: Set<string>
  onToggleCollapse: (item: TodoItem) => void
  onToggleCheck: (item: TodoItem) => void
  onAddChild: (item: TodoItem) => void
  onEdit: (item: TodoItem) => void
  onDelete: (item: TodoItem) => void
}

export default function TodoItemList({
  items,
  theme,
  depth = 0,
  collapsedIds,
  onToggleCollapse,
  onToggleCheck,
  onAddChild,
  onEdit,
  onDelete,
}: Props) {
  const indent = Math.min(depth, MAX_INDENT_DEPTH) * INDENT_PER_DEPTH

  return (
    <ul className="flex flex-col gap-2">
      {items.map((item) => {
        const leaf = isLeaf(item)
        const done = isItemDone(item)
        const collapsed = collapsedIds.has(item.id)
        const childCount = leaf ? null : countLeaves(item.children ?? [])

        return (
          <li key={item.id} className="flex flex-col gap-2">
            <div style={{ marginLeft: indent }}>
              <SwipeToDeleteRow onRequestDelete={() => onDelete(item)}>
                <div className="flex items-stretch bg-white">
                  <button
                    type="button"
                    {...(leaf
                      ? { role: 'checkbox', 'aria-checked': item.checked }
                      : { 'aria-expanded': !collapsed })}
                    onClick={() =>
                      leaf ? onToggleCheck(item) : onToggleCollapse(item)
                    }
                    className="flex min-h-12 flex-1 items-start gap-3 px-3 py-2 text-left active:bg-slate-50"
                  >
                    {leaf ? (
                      <span
                        className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border-2 ${
                          item.checked
                            ? `${theme.bar} border-transparent text-white`
                            : 'border-slate-300 bg-white'
                        }`}
                      >
                        {item.checked ? <CheckIcon /> : null}
                      </span>
                    ) : (
                      // サブ項目を持つ行は開閉の矢印。完了は取り消し線と件数で表す
                      <span
                        aria-hidden="true"
                        className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center ${
                          done ? theme.text : 'text-slate-400'
                        }`}
                      >
                        <svg
                          viewBox="0 0 24 24"
                          className={`h-4 w-4 transition-transform ${
                            collapsed ? '' : 'rotate-90'
                          }`}
                          fill="none"
                          stroke="currentColor"
                          strokeWidth={2.5}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M9 6l6 6-6 6" />
                        </svg>
                      </span>
                    )}

                    <span className="min-w-0 flex-1">
                      <span
                        className={`block break-words ${
                          done ? 'text-slate-400 line-through' : 'text-slate-800'
                        }`}
                      >
                        {item.text}
                      </span>
                      {item.description ? (
                        <span
                          className={`mt-0.5 block text-xs leading-relaxed break-words whitespace-pre-wrap ${
                            done ? 'text-slate-300' : 'text-slate-500'
                          }`}
                        >
                          {item.description}
                        </span>
                      ) : null}
                      {childCount ? (
                        <span
                          className={`mt-1 block text-xs font-medium ${
                            done ? 'text-slate-400' : theme.text
                          }`}
                        >
                          {done ? '完了 ' : 'サブ項目 '}
                          {childCount.done}/{childCount.total}
                          {collapsed ? '（折りたたみ中）' : ''}
                        </span>
                      ) : null}
                    </span>
                  </button>

                  <button
                    type="button"
                    aria-label={`${item.text}にサブ項目を追加`}
                    onClick={() => onAddChild(item)}
                    className="flex min-h-12 min-w-11 items-center justify-center text-slate-400 active:bg-slate-100"
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
                      <path d="M12 5v14M5 12h14" />
                    </svg>
                  </button>

                  <button
                    type="button"
                    aria-label={`${item.text}を編集`}
                    onClick={() => onEdit(item)}
                    className="flex min-h-12 min-w-11 items-center justify-center text-slate-400 active:bg-slate-100"
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
            </div>

            {!leaf && !collapsed ? (
              <TodoItemList
                items={item.children ?? []}
                theme={theme}
                depth={depth + 1}
                collapsedIds={collapsedIds}
                onToggleCollapse={onToggleCollapse}
                onToggleCheck={onToggleCheck}
                onAddChild={onAddChild}
                onEdit={onEdit}
                onDelete={onDelete}
              />
            ) : null}
          </li>
        )
      })}
    </ul>
  )
}

function CheckIcon() {
  return (
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
  )
}
