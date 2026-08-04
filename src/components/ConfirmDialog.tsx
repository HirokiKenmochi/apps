type Props = {
  open: boolean
  title: string
  message?: string
  confirmLabel?: string
  onConfirm: () => void
  onClose: () => void
}

/** 削除など、取り消せない操作の確認ダイアログ */
export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = '削除する',
  onConfirm,
  onClose,
}: Props) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <button
        type="button"
        aria-label="閉じる"
        onClick={onClose}
        className="absolute inset-0 bg-slate-900/40"
      />
      <div className="relative w-full max-w-[360px] rounded-2xl bg-white p-5 shadow-xl">
        <p className="mb-1 text-base font-bold text-slate-800">{title}</p>
        {message ? (
          <p className="mb-4 text-sm text-slate-600">{message}</p>
        ) : (
          <div className="mb-4" />
        )}
        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="min-h-12 flex-1 rounded-xl border border-slate-300 font-bold text-slate-600 active:bg-slate-100"
          >
            キャンセル
          </button>
          <button
            type="button"
            onClick={() => {
              onConfirm()
              onClose()
            }}
            className="min-h-12 flex-1 rounded-xl bg-rose-600 font-bold text-white active:bg-rose-700"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
