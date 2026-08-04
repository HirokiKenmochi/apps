import { useEffect, useRef, useState } from 'react'

type Props = {
  open: boolean
  title: string
  initialText?: string
  initialDescription?: string
  submitLabel?: string
  onSubmit: (text: string, description: string) => void
  onClose: () => void
}

/** 「行う内容」と、その説明を入力するシート（追加・編集で共用） */
export default function ItemFormSheet({
  open,
  title,
  initialText = '',
  initialDescription = '',
  submitLabel = '保存',
  onSubmit,
  onClose,
}: Props) {
  const [text, setText] = useState(initialText)
  const [description, setDescription] = useState(initialDescription)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!open) return
    setText(initialText)
    setDescription(initialDescription)
    const timer = window.setTimeout(() => inputRef.current?.focus(), 50)
    return () => window.clearTimeout(timer)
  }, [open, initialText, initialDescription])

  if (!open) return null

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    const trimmed = text.trim()
    if (!trimmed) return
    onSubmit(trimmed, description.trim())
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

        <label className="mb-1 block text-xs font-bold text-slate-500">
          行う内容
        </label>
        <input
          ref={inputRef}
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="例: 資料をまとめる"
          enterKeyHint="done"
          className="mb-3 min-h-12 w-full rounded-xl border border-slate-300 px-3 text-base text-slate-800 outline-none focus:border-slate-500"
        />

        <label className="mb-1 block text-xs font-bold text-slate-500">
          説明（任意）
        </label>
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="補足やメモを書けます"
          rows={3}
          className="mb-4 w-full resize-none rounded-xl border border-slate-300 px-3 py-2 text-sm leading-relaxed text-slate-800 outline-none focus:border-slate-500"
        />

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
            disabled={!text.trim()}
            className="min-h-12 flex-1 rounded-xl bg-slate-800 font-bold text-white disabled:bg-slate-300"
          >
            {submitLabel}
          </button>
        </div>
      </form>
    </div>
  )
}
