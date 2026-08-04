"""TanIn（たんいん）— 単位換算とオームの法則の練習アプリ。

このファイルはページ切り替えだけを担当する。
計算ロジックは tanin/units.py・ohm.py・quiz.py に、画面は tanin/ui/ にある。
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="TanIn（たんいん）",
    page_icon="🔌",
    layout="centered",
    initial_sidebar_state="collapsed",
)


def _source_fingerprint() -> float:
    """tanin パッケージの中で、いちばん新しいファイルの更新時刻。"""
    package = Path(__file__).parent / "tanin"
    return max((path.stat().st_mtime for path in package.rglob("*.py")), default=0.0)


# Streamlit Community Cloud は git pull のあと、読み込み済みモジュールをメモリに
# 残したままスクリプトだけ再実行する。そのままだと、新しく追加した関数が見つからず
# ImportError でアプリが止まってしまう。ファイルが新しくなっていたら読み込み直す。
_fingerprint = _source_fingerprint()
if st.session_state.get("_source_fingerprint") != _fingerprint:
    for _name in [name for name in sys.modules if name == "tanin" or name.startswith("tanin.")]:
        del sys.modules[_name]
    st.session_state["_source_fingerprint"] = _fingerprint

from tanin.ui import converter, quiz_page, reference, stats  # noqa: E402
from tanin.ui._common import init_state, inject_css, render_update_button  # noqa: E402
from tanin.ui._storage import sync_history  # noqa: E402
from tanin.version import current_version  # noqa: E402

inject_css()
init_state()
sync_history()  # ブラウザに保存した学習履歴を読み込む（以降は自動で保存される）

st.title("TanIn（たんいん）")
st.caption("単位換算とオームの法則を、スマホでもPCでも練習できる理科学習アプリ")

# サイドバーはスマホだと隠れて気づかれないため、画面上部のタブで切り替える
tab_converter, tab_quiz, tab_reference, tab_stats = st.tabs(
    ["🔁 単位換算", "✏️ 練習問題", "📖 早見表", "📊 成績"]
)

with tab_converter:
    converter.render()

with tab_quiz:
    quiz_page.render()

with tab_reference:
    reference.render()

with tab_stats:
    stats.render()

# いま動いているバージョンの表示と、開きっぱなしの画面を最新にするボタン
st.divider()
render_update_button(current_version().label)
