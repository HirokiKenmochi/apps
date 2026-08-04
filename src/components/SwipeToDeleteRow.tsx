import { useRef, useState, type ReactNode } from 'react'

const REVEAL = 88 // 削除ボタンの幅(px)
const OPEN_THRESHOLD = 40 // ここまで引いたら開いたままにする
const MOVE_TOLERANCE = 8 // これ以上動いたらスワイプとみなす
const LONG_PRESS_MS = 550

type Props = {
  children: ReactNode
  /** 左スワイプの削除ボタン、または長押しで呼ばれる */
  onRequestDelete: () => void
}

/** 左スワイプ、または長押しで削除できる行 */
export default function SwipeToDeleteRow({ children, onRequestDelete }: Props) {
  const [offset, setOffset] = useState(0) // 0 〜 -REVEAL
  const [open, setOpen] = useState(false)
  const [dragging, setDragging] = useState(false)

  const startX = useRef(0)
  const startY = useRef(0)
  const active = useRef(false)
  const moved = useRef(false)
  const timer = useRef<number | null>(null)

  const clearTimer = () => {
    if (timer.current !== null) {
      window.clearTimeout(timer.current)
      timer.current = null
    }
  }

  const close = () => {
    setOpen(false)
    setOffset(0)
  }

  const handlePointerDown = (event: React.PointerEvent) => {
    if (event.pointerType === 'mouse' && event.button !== 0) return
    startX.current = event.clientX
    startY.current = event.clientY
    active.current = true
    moved.current = false
    clearTimer()
    timer.current = window.setTimeout(() => {
      // 長押し: そのまま削除確認へ
      active.current = false
      moved.current = true // 直後の click を無効化する
      close()
      onRequestDelete()
    }, LONG_PRESS_MS)
  }

  const handlePointerMove = (event: React.PointerEvent) => {
    if (!active.current) return
    const dx = event.clientX - startX.current
    const dy = event.clientY - startY.current

    // 縦方向の動きが優勢ならスクロールとみなして中断する
    if (Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > MOVE_TOLERANCE) {
      active.current = false
      clearTimer()
      setDragging(false)
      setOffset(open ? -REVEAL : 0)
      return
    }

    if (Math.abs(dx) > MOVE_TOLERANCE) {
      moved.current = true
      clearTimer()
      setDragging(true)
    }

    const base = open ? -REVEAL : 0
    setOffset(Math.min(0, Math.max(-REVEAL, base + dx)))
  }

  const handlePointerUp = () => {
    clearTimer()
    setDragging(false)
    if (!active.current) return
    active.current = false
    const shouldOpen = offset <= -OPEN_THRESHOLD
    setOpen(shouldOpen)
    setOffset(shouldOpen ? -REVEAL : 0)
  }

  return (
    <div className="relative overflow-hidden rounded-xl">
      <button
        type="button"
        onClick={() => {
          close()
          onRequestDelete()
        }}
        tabIndex={open ? 0 : -1}
        aria-hidden={!open}
        style={{ width: REVEAL }}
        className="absolute inset-y-0 right-0 flex items-center justify-center bg-rose-600 text-sm font-bold text-white"
      >
        削除
      </button>

      <div
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onContextMenu={(event) => event.preventDefault()}
        onClickCapture={(event) => {
          // スワイプ・長押しの直後は行のタップ操作を発火させない
          if (moved.current) {
            event.preventDefault()
            event.stopPropagation()
            moved.current = false
          }
        }}
        style={{
          transform: `translateX(${offset}px)`,
          transition: dragging ? 'none' : 'transform 0.18s ease-out',
          touchAction: 'pan-y',
        }}
        className="no-touch-callout relative bg-white"
      >
        {children}
      </div>
    </div>
  )
}
