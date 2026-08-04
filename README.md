# apps

個人で作ったアプリを 1 つのリポジトリにまとめています。
**アプリごとにフォルダが独立していて、コード・設定・依存関係・デプロイ手順はすべてそのフォルダの中で完結します。**
別のアプリのファイルを参照している箇所はありません。

| フォルダ | アプリ | 技術 | 起動 |
| --- | --- | --- | --- |
| [`tanin/`](tanin/) | TanIn（たんいん）— 単位換算とオームの法則の学習アプリ | Python / Streamlit | `cd tanin && .venv/bin/streamlit run app.py` |
| [`task-app/`](task-app/) | タスク管理 — カテゴリごとにタスクを管理するモバイル向け Web アプリ | React + TypeScript / Vite | `cd task-app && npm install && npm run dev` |

各アプリの詳細はフォルダ内の README を参照してください。

## 作業するときの約束

- 作業は必ずアプリのフォルダに入ってから行う（`cd tanin` または `cd task-app`）
- 依存関係・ビルド成果物・仮想環境はそのフォルダの中に置く（`tanin/.venv`、`task-app/node_modules` など）
- 除外設定は各フォルダの `.gitignore` に書く。リポジトリ直下の `.gitignore` は共通のもの（`.DS_Store`）だけ
- コミットは片方のアプリ単位でまとめる（例: `git add -A tanin`）
