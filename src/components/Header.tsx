import { useNavigate } from 'react-router-dom'
import type { ReactNode } from 'react'

type Props = {
  title: string
  /** 戻り先のパス。指定がなければブラウザ履歴を 1 つ戻る */
  backTo?: string
  /** ヘッダー右端に置く要素（削除ボタンなど） */
  right?: ReactNode
}

export default function Header({ title, backTo, right }: Props) {
  const navigate = useNavigate()

  return (
    <header className="pt-safe sticky top-0 z-10 flex min-h-14 items-center gap-1 border-b border-slate-200 bg-white/95 px-1 backdrop-blur">
      {backTo !== undefined || window.history.length > 1 ? (
        <button
          type="button"
          aria-label="戻る"
          onClick={() => (backTo ? navigate(backTo) : navigate(-1))}
          className="flex h-11 min-w-11 items-center justify-center rounded-lg px-2 text-slate-600 active:bg-slate-100"
        >
          <svg
            viewBox="0 0 24 24"
            className="h-6 w-6"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
      ) : null}
      <h1 className="min-w-0 flex-1 truncate text-lg font-bold text-slate-800">
        {title}
      </h1>
      {right}
    </header>
  )
}
