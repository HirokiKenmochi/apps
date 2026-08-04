import { useEffect, useRef, useState } from 'react'

type Props = {
  open: boolean
  /** シートの見出し */
  title: string
  /** 編集時の初期値 */
  initialValue?: string
  placeholder?: string
  submitLabel?: string
  onSubmit: (value: string) => void
  onClose: () => void
}

/**
 * 画面下部から出るテキスト入力シート。
 * ブラウザ標準の prompt を使わず、モバイルで扱いやすい形にしている。
 */
export default function TextInputSheet({
  open,
  title,
  initialValue = '',
  placeholder = '入力してください',
  submitLabel = '保存',
  onSubmit,
  onClose,
}: Props) {
  const [value, setValue] = useState(initialValue)
  const inputRef = useRef<HTMLInputElement>(null)

  // 開くたびに初期値へ戻し、入力欄にフォーカスする
  useEffect(() => {
    if (!open) return
    setValue(initialValue)
    const timer = window.setTimeout(() => inputRef.current?.focus(), 50)
    return () => window.clearTimeout(timer)
  }, [open, initialValue])

  if (!open) return null

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    const trimmed = value.trim()
    if (!trimmed) return
    onSubmit(trimmed)
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
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder={placeholder}
          enterKeyHint="done"
          className="mb-4 min-h-12 w-full rounded-xl border border-slate-300 px-3 text-base text-slate-800 outline-none focus:border-slate-500"
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
            disabled={!value.trim()}
            className="min-h-12 flex-1 rounded-xl bg-slate-800 font-bold text-white disabled:bg-slate-300"
          >
            {submitLabel}
          </button>
        </div>
      </form>
    </div>
  )
}
