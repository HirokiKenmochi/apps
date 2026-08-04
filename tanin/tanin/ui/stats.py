"""成績ページ。"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from tanin import history
from tanin.quiz import DIFFICULTY_LABELS
from tanin.ui._storage import clear_saved_history

_HISTORY_FILENAME = "tanin_history.json"


def _clear_history() -> None:
    clear_saved_history()  # ブラウザに保存したぶんも消す


def _start_review() -> None:
    st.session_state["quiz_mode"] = "review"
    st.session_state["review_queue"] = history.review_questions(st.session_state["attempts"])
    st.session_state["quiz_current"] = None
    st.session_state["quiz_grade"] = None


def render() -> None:
    st.subheader("成績")
    attempts: list[history.Attempt] = st.session_state["attempts"]

    if not attempts:
        st.info("まだ記録がありません。「練習問題」タブで解くと、ここに成績がたまります。")
    else:
        summary = history.summarize(attempts)
        col1, col2, col3 = st.columns(3)
        col1.metric("解いた問題", f"{summary.total} 問")
        col2.metric("正答率", f"{summary.accuracy_percent:.0f}%")
        col3.metric("連続正解", f"{summary.current_streak}")
        st.caption(
            f"正解 {summary.correct} / {summary.total} 問 ・ 最高連続正解 {summary.best_streak} ・ "
            f"解答にかけた時間の合計 {summary.total_seconds:.0f} 秒"
        )

        st.markdown("**カテゴリ別の正答率**")
        rows = [
            {
                "カテゴリ": stat.label,
                "出題数": stat.total,
                "正解数": stat.correct,
                "正答率(%)": round(stat.accuracy_percent, 1),
            }
            for stat in history.by_category(attempts)
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("**直近20問の推移**")
        trend = history.trend(attempts, 20)
        chart_data = pd.DataFrame(trend).set_index("問題番号")[["正答率(%)"]]
        st.line_chart(chart_data, use_container_width=True)
        marks = "".join("○" if row["正誤"] else "×" for row in trend)
        st.caption(f"直近の正誤（古い順）：{marks}")

    st.divider()

    st.markdown("**復習リスト**")
    pending = history.review_questions(attempts)
    if not pending:
        st.caption("間違えた問題はありません。")
    else:
        st.caption(f"{len(pending)} 問たまっています。正解すると自動で消えます。")
        for question in pending[:10]:
            st.markdown(f"- {question.prompt}（正解：{question.answer_text}）")
        if len(pending) > 10:
            st.caption(f"ほか {len(pending) - 10} 問")
        st.button("この問題を復習する", on_click=_start_review, use_container_width=True)
        st.caption("ボタンを押したあと「練習問題」タブを開いてください。")

    st.divider()

    st.markdown("**履歴の保存・復元**")
    st.caption("履歴はこの端末のブラウザに保存されます（サーバーには送られません）。\n"
           "別の端末に移すときは、JSONに書き出して読み込んでください。")
    st.download_button(
        "履歴をJSONでダウンロード",
        data=history.to_json(attempts),
        file_name=_HISTORY_FILENAME,
        mime="application/json",
        use_container_width=True,
        disabled=not attempts,
    )

    uploaded = st.file_uploader("履歴JSONを読み込む", type=["json"], key="history_upload")
    if uploaded is not None:
        try:
            restored = history.from_json(uploaded.getvalue())
        except ValueError as exc:
            st.error(f"読み込めませんでした：{exc}")
        else:
            left, right = st.columns(2)
            if left.button(f"{len(restored)}件で置きかえる", use_container_width=True):
                st.session_state["attempts"] = restored
                st.rerun()
            if right.button(f"{len(restored)}件を追加する", use_container_width=True):
                st.session_state["attempts"] = attempts + restored
                st.rerun()

    if attempts:
        with st.expander("解答の履歴（新しい順）"):
            table = [
                {
                    "カテゴリ": a.category_label,
                    "難易度": DIFFICULTY_LABELS.get(a.difficulty, a.difficulty),
                    "正誤": "○" if a.correct else "×",
                    "あなたの答え": a.your_answer,
                    "正解": a.correct_answer,
                    "秒": round(a.seconds, 1),
                    "問題": a.prompt,
                }
                for a in reversed(attempts)
            ]
            st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)
        st.button("履歴をすべて消す", on_click=_clear_history, use_container_width=True)
