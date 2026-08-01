"""TanIn（たんいん）— 単位換算とオームの法則の練習アプリ。

このファイルはページ切り替えだけを担当する。
計算ロジックは tanin/units.py・ohm.py・quiz.py に、画面は tanin/ui/ にある。
"""

from __future__ import annotations

import streamlit as st

from tanin.ui import converter, quiz_page, reference, stats
from tanin.ui._common import init_state, inject_css

st.set_page_config(
    page_title="TanIn（たんいん）",
    page_icon="🔌",
    layout="centered",
    initial_sidebar_state="collapsed",
)

inject_css()
init_state()

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
