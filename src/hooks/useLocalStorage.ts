import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * localStorage に値を保存し、リロード後も復元する useState 互換のフック。
 * 保存済みの値が壊れている場合は初期値にフォールバックする。
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T,
  /** 読み込んだ値が期待する形かどうかを判定する（任意） */
  validate?: (value: unknown) => value is T,
) {
  const [value, setValue] = useState<T>(() => {
    try {
      const raw = window.localStorage.getItem(key)
      if (raw === null) return initialValue
      const parsed: unknown = JSON.parse(raw)
      if (validate && !validate(parsed)) return initialValue
      return parsed as T
    } catch {
      return initialValue
    }
  })

  // 初回レンダー直後の書き込みは不要（読み込んだ値をそのまま書き戻すだけのため）
  const isFirstRender = useRef(true)

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false
      // 保存領域が空のときだけ初期値を書き込む
      if (window.localStorage.getItem(key) !== null) return
    }
    try {
      window.localStorage.setItem(key, JSON.stringify(value))
    } catch {
      // 容量オーバーなどで保存できない場合は無視する
    }
  }, [key, value])

  const update = useCallback((updater: T | ((prev: T) => T)) => {
    setValue(updater)
  }, [])

  return [value, update] as const
}
