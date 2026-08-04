import type { AppData, Category, CategoryColor } from '../types'

/** 初回起動時に投入するカテゴリと動作確認用のサンプルタスク */
export const initialData: AppData = {
  categories: [
    { id: 'school', name: '学校', color: 'sky' },
    { id: 'work', name: '仕事', color: 'emerald' },
  ],
  tasks: [
    {
      id: 'task-sample-1',
      categoryId: 'school',
      title: 'レポート課題',
      items: [
        { id: 'item-sample-1', text: 'テーマを決める', checked: true },
        { id: 'item-sample-2', text: '資料を集める', checked: true },
        { id: 'item-sample-3', text: '本文を書く', checked: false },
        { id: 'item-sample-4', text: '提出する', checked: false },
      ],
      createdAt: '2026-01-05T09:00:00.000Z',
    },
    {
      id: 'task-sample-2',
      categoryId: 'school',
      title: '期末テストの勉強',
      items: [
        { id: 'item-sample-5', text: '出題範囲を確認する', checked: true },
        { id: 'item-sample-6', text: '過去問を解く', checked: true },
      ],
      createdAt: '2026-01-06T09:00:00.000Z',
    },
    {
      id: 'task-sample-3',
      categoryId: 'work',
      title: '定例ミーティングの準備',
      items: [
        { id: 'item-sample-7', text: 'アジェンダを作る', checked: false },
        { id: 'item-sample-8', text: '共有資料をまとめる', checked: false },
        { id: 'item-sample-9', text: '参加者に連絡する', checked: true },
      ],
      createdAt: '2026-01-07T09:00:00.000Z',
    },
  ],
}

/** カテゴリごとのアクセントカラー（未登録のカテゴリはグレー系にフォールバック） */
export type CategoryTheme = {
  /** カード左端のバー・進捗バーなどの塗り */
  bar: string
  /** 淡い背景 */
  soft: string
  /** 文字色 */
  text: string
  /** 枠線 */
  border: string
  /** チェックボックスの色 */
  accent: string
}

/** カテゴリ追加時に選べる色 */
export const CATEGORY_COLORS: { key: CategoryColor; label: string }[] = [
  { key: 'sky', label: '青' },
  { key: 'emerald', label: '緑' },
  { key: 'amber', label: 'オレンジ' },
  { key: 'violet', label: '紫' },
  { key: 'rose', label: 'ピンク' },
  { key: 'slate', label: 'グレー' },
]

// Tailwind はクラス名を静的に読み取るため、色ごとに全クラスを書き出しておく
const themes: Record<CategoryColor, CategoryTheme> = {
  sky: {
    bar: 'bg-sky-500',
    soft: 'bg-sky-50',
    text: 'text-sky-700',
    border: 'border-sky-200',
    accent: 'accent-sky-600',
  },
  emerald: {
    bar: 'bg-emerald-500',
    soft: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
    accent: 'accent-emerald-600',
  },
  amber: {
    bar: 'bg-amber-500',
    soft: 'bg-amber-50',
    text: 'text-amber-700',
    border: 'border-amber-200',
    accent: 'accent-amber-600',
  },
  violet: {
    bar: 'bg-violet-500',
    soft: 'bg-violet-50',
    text: 'text-violet-700',
    border: 'border-violet-200',
    accent: 'accent-violet-600',
  },
  rose: {
    bar: 'bg-rose-500',
    soft: 'bg-rose-50',
    text: 'text-rose-700',
    border: 'border-rose-200',
    accent: 'accent-rose-600',
  },
  slate: {
    bar: 'bg-slate-500',
    soft: 'bg-slate-50',
    text: 'text-slate-700',
    border: 'border-slate-200',
    accent: 'accent-slate-600',
  },
}

/** 色未設定の古いデータ向けのフォールバック */
const legacyColorById: Record<string, CategoryColor> = {
  school: 'sky',
  work: 'emerald',
}

export function getTheme(color: CategoryColor): CategoryTheme {
  return themes[color]
}

/** 色未設定のカテゴリも含めて、実際に使う色を返す */
export function resolveCategoryColor(category: Category): CategoryColor {
  return category.color ?? legacyColorById[category.id] ?? 'slate'
}

export function getCategoryTheme(category?: Category): CategoryTheme {
  if (!category) return themes.slate
  return themes[resolveCategoryColor(category)]
}
