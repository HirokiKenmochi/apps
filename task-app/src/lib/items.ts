import type { TodoItem } from '../types'

/** サブ項目を持たない（＝自分でチェックできる）項目か */
export function isLeaf(item: TodoItem): boolean {
  return !item.children || item.children.length === 0
}

/**
 * 項目が完了しているか。
 * サブ項目を持つ項目は、配下の末端項目がすべてチェック済みなら完了扱い。
 */
export function isItemDone(item: TodoItem): boolean {
  if (isLeaf(item)) return item.checked
  return (item.children ?? []).every(isItemDone)
}

/** 配下の末端項目の 完了数 / 総数 を数える */
export function countLeaves(items: TodoItem[]): { done: number; total: number } {
  return items.reduce(
    (acc, item) => {
      if (isLeaf(item)) {
        return {
          done: acc.done + (item.checked ? 1 : 0),
          total: acc.total + 1,
        }
      }
      const child = countLeaves(item.children ?? [])
      return { done: acc.done + child.done, total: acc.total + child.total }
    },
    { done: 0, total: 0 },
  )
}

/** ツリーから ID 一致の項目を探す */
export function findItem(items: TodoItem[], id: string): TodoItem | undefined {
  for (const item of items) {
    if (item.id === id) return item
    const found = findItem(item.children ?? [], id)
    if (found) return found
  }
  return undefined
}

/** ID 一致の項目を updater の戻り値に差し替えた新しいツリーを返す */
export function mapItem(
  items: TodoItem[],
  id: string,
  updater: (item: TodoItem) => TodoItem,
): TodoItem[] {
  return items.map((item) => {
    if (item.id === id) return updater(item)
    if (!item.children) return item
    return { ...item, children: mapItem(item.children, id, updater) }
  })
}

/** ID 一致の項目を（サブ項目ごと）取り除いた新しいツリーを返す */
export function removeItem(items: TodoItem[], id: string): TodoItem[] {
  return items
    .filter((item) => item.id !== id)
    .map((item) =>
      item.children
        ? { ...item, children: removeItem(item.children, id) }
        : item,
    )
}

/** parentId の配下（未指定なら最上位）に項目を追加した新しいツリーを返す */
export function appendItem(
  items: TodoItem[],
  newItem: TodoItem,
  parentId?: string,
): TodoItem[] {
  if (!parentId) return [...items, newItem]
  return mapItem(items, parentId, (parent) => ({
    ...parent,
    children: [...(parent.children ?? []), newItem],
  }))
}
