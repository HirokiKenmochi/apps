# タスク管理アプリ

カテゴリごとにタスクを管理する、スマホ利用を想定したモバイルファーストの Web アプリです。
データはブラウザの localStorage にのみ保存します（バックエンド不要）。

## 技術スタック

- React 19 + TypeScript（Vite）
- Tailwind CSS v4（`@tailwindcss/vite` プラグイン）
- React Router v7
- localStorage（キー: `task-app:data:v1`）

## 起動方法

```bash
npm install
npm run dev     # http://localhost:5173/
npm run build   # 本番ビルド
npm run preview # ビルド結果の確認
```

## 画面構成

| パス | 画面 | 内容 |
| --- | --- | --- |
| `/` | カテゴリ一覧 | カテゴリをカード表示。カテゴリごとの完了タスク数と進捗バー。カテゴリの追加・編集・削除もここから |
| `/category/:categoryId` | タスク一覧 | タスクのタイトルとチェック項目の進捗（例: 3/4）。全項目チェック済みは取り消し線＋グレーアウト |
| `/category/:categoryId/task/:taskId` | タスク詳細 | タイトル（タップで編集）と「行う内容」のチェックリスト。各項目に説明を書け、サブ項目を何段でも入れ子にできる |

## 操作

- カテゴリ追加: カテゴリ一覧の「＋ カテゴリを追加」（名前とアクセントカラー6色から選択）
- カテゴリの名前・色の変更: カードの右端のペンアイコン
- カテゴリ削除: カードを左スワイプ または 長押し（そのカテゴリのタスクも一緒に削除、確認ダイアログあり）
- タスク追加: タスク一覧の「＋ タスクを追加」（追加後はそのタスクの詳細画面へ移動）
- タスクのタイトル編集: 詳細画面のタイトルをタップ → Enter または入力欄の外をタップで確定（Esc で取り消し）
- タスク削除: タスク一覧の行を左スワイプ または 長押し／詳細画面ヘッダーのゴミ箱アイコン
- 項目の追加: 詳細画面の「＋ 項目を追加」（内容と説明を入力。説明は任意）
- サブ項目の追加: 行の ＋ アイコン。サブ項目のさらに下にも追加でき、階層に制限はありません
- 項目のチェック切り替え: 行をタップ（再タップで解除）
- 項目の編集: 行の ✎ アイコン（内容と説明を編集。説明を空にすると削除されます）
- 項目の削除: 行を左スワイプ または 長押し（サブ項目も一緒に削除、確認ダイアログあり）
- サブ項目の折りたたみ: サブ項目を持つ行をタップ

### チェックと進捗の数え方

- サブ項目を持つ項目は自分ではチェックできず、配下の末端項目がすべて完了した時点で自動的に完了（取り消し線＋グレーアウト）になります
- 進捗（`3/4` や 完了 2/5）は**末端の項目のみ**を数えます。途中の親項目は数に含めません

## データモデル

`src/types.ts` を参照。`Category` / `Task` / `TodoItem` の 3 つで構成しています。
`TodoItem` は `description`（説明・任意）と `children`（サブ項目・任意）を持つ再帰構造で、`children` を持たない末端の項目だけが `checked` を使います。
ツリーの操作・集計は `src/lib/items.ts` にまとめています。
`Category.color` は任意項目で、未設定の場合は既定色（学校＝青系、仕事＝緑系、それ以外＝グレー）にフォールバックします。
初期データと配色の定義は `src/data/initialData.ts` にあります。

## ディレクトリ構成

```
src/
  components/   Header, TextInputSheet, ItemFormSheet, CategoryFormSheet,
                ConfirmDialog, SwipeToDeleteRow, TodoItemList（再帰レンダリング）
  data/         initialData.ts（初期カテゴリ・サンプルタスク・配色）
  hooks/        useLocalStorage.ts
  lib/          id.ts, items.ts（項目ツリーの操作と集計）
  pages/        CategoryListPage / TaskListPage / TaskDetailPage
  store/        TaskProvider.tsx（状態と更新処理）, context.ts（型と補助関数）
```

## メモ

- 保存データを初期状態に戻したいときは、DevTools のコンソールで
  `localStorage.removeItem('task-app:data:v1')` を実行してリロードしてください。
- 画面幅 375px を基準に設計し、PC では中央に最大 480px 幅で表示します。タップ領域は最低 44px を確保しています。
