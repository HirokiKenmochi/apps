import { useEffect, useRef, useState } from 'react'
import { CATEGORY_COLORS, getTheme } from '../data/initialData'
import type { CategoryColor } from '../types'

type Props = {
  open: boolean
  title: string
  initialName?: string
  initialColor?: CategoryColor
  submitLabel?: string
  onSubmit: (name: string, color: CategoryColor) => void
  onClose: () => void
}

/** カテゴリ名とアクセントカラーを入力するシート（追加・編集で共用） */
export default function CategoryFormSheet({
  open,
  title,
  initialName = '',
  initialColor = 'sky',
  submitLabel = '保存',
  onSubmit,
  onClose,
}: Props) {
  const [name, setName] = useState(initialName)
  const [color, setColor] = useState<CategoryColor>(initialColor)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!open) return
    setName(initialName)
    setColor(initialColor)
    const timer = window.setTimeout(() => inputRef.current?.focus(), 50)
    return () => window.clearTimeout(timer)
  }, [open, initialName, initialColor])

  if (!open) return null

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    onSubmit(trimmed, color)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center">
      <button
        type="button"
        aria-label="閉じる"
        onClick={onClose}
        className="absolute inset-0 bg-slate-900/40"
      />
      <form
        onSubmit={handleSubmit}
        className="pb-safe relative w-full max-w-[480px] rounded-t-2xl bg-white p-4 shadow-xl"
      >
        <p className="mb-3 text-base font-bold text-slate-800">{title}</p>

        <input
          ref={inputRef}
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="カテゴリ名（例: 家事）"
          enterKeyHint="done"
          className="mb-4 min-h-12 w-full rounded-xl border border-slate-300 px-3 text-base text-slate-800 outline-none focus:border-slate-500"
        />

        <p className="mb-2 text-xs font-bold text-slate-500">アクセントカラー</p>
        <div className="mb-4 flex flex-wrap gap-2">
          {CATEGORY_COLORS.map((option) => {
            const theme = getTheme(option.key)
            const selected = option.key === color
            return (
              <button
                key={option.key}
                type="button"
                aria-label={option.label}
                aria-pressed={selected}
                onClick={() => setColor(option.key)}
                className={`flex h-11 min-w-11 items-center justify-center rounded-xl border-2 px-2 ${
                  selected ? 'border-slate-800' : 'border-transparent'
                }`}
              >
                <span className={`h-7 w-7 rounded-full ${theme.bar}`} />
              </button>
            )
          })}
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="min-h-12 flex-1 rounded-xl border border-slate-300 font-bold text-slate-600 active:bg-slate-100"
          >
            キャンセル
          </button>
          <button
            type="submit"
            disabled={!name.trim()}
            className="min-h-12 flex-1 rounded-xl bg-slate-800 font-bold text-white disabled:bg-slate-300"
          >
            {submitLabel}
          </button>
        </div>
      </form>
    </div>
  )
}
