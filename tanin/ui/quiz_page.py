"""練習問題ページ。"""

from __future__ import annotations

import random
import time

import streamlit as st

from tanin import history, quiz
from tanin.ui._common import numeric_input, ohm_triangle_svg, render_circuit, render_figure

CHALLENGE_COUNT = 10

# 解説といっしょに「オームの法則の三角形」を出すパターンと、かくす文字
_TRIANGLE_FOR: dict[str, str] = {
    "ohm_voltage": "V",
    "ohm_current": "I",
    "ohm_resistance": "R",
    "unit_voltage": "V",
    "unit_current": "I",
    "unit_resistance": "R",
    "series_current": "I",
    "series_drop": "V",
    "parallel_branch": "I",
}
_TRIANGLE_HINT: dict[str, str] = {
    "V": "もとめるのは **電圧 V**。かくすと `I` と `R` が横ならび → **V = I × R**",
    "I": "もとめるのは **電流 I**。かくすと `V` が上・`R` が下 → **I = V ÷ R**",
    "R": "もとめるのは **抵抗 R**。かくすと `V` が上・`I` が下 → **R = V ÷ I**",
}

_MODES = {
    "practice": "ふつうに練習",
    "challenge": f"{CHALLENGE_COUNT}問チャレンジ",
    "review": "復習リストから",
}


def _answer_key() -> str:
    return f"quiz_answer_{st.session_state['quiz_serial']}"


def _reset_question() -> None:
    st.session_state["quiz_current"] = None
    st.session_state["quiz_grade"] = None


def _next_question() -> None:
    """次の問題を用意する。復習モードでリストが尽きたら None のままにする。"""
    st.session_state["quiz_serial"] += 1
    st.session_state["quiz_grade"] = None
    st.session_state["quiz_started_at"] = time.time()

    if st.session_state["quiz_mode"] == "review":
        queue: list = st.session_state.get("review_queue") or []
        st.session_state["quiz_current"] = queue.pop(0) if queue else None
        st.session_state["review_queue"] = queue
        return

    categories = list(st.session_state["quiz_categories"]) or ["ohm_basic"]
    category = random.choice(categories)
    st.session_state["quiz_current"] = quiz.generate_question(
        category, st.session_state["quiz_difficulty"]
    )


def _start_challenge() -> None:
    st.session_state["quiz_mode"] = "challenge"
    st.session_state["challenge_index"] = 0
    st.session_state["challenge_correct"] = 0
    st.session_state["challenge_started_at"] = time.time()
    st.session_state["challenge_finished"] = False
    st.session_state["challenge_seconds"] = 0.0
    _next_question()


def _start_review() -> None:
    st.session_state["quiz_mode"] = "review"
    st.session_state["review_queue"] = history.review_questions(st.session_state["attempts"])
    _next_question()


def _on_mode_change() -> None:
    _reset_question()
    if st.session_state["quiz_mode"] == "review":
        st.session_state["review_queue"] = history.review_questions(st.session_state["attempts"])


def _submit(question: quiz.Question) -> None:
    response = st.session_state.get(_answer_key())
    result = quiz.grade(question, response)
    started = st.session_state.get("quiz_started_at") or time.time()
    seconds = max(0.0, time.time() - started)

    st.session_state["attempts"].append(
        history.make_attempt(question, result.correct, result.your_answer, seconds)
    )
    st.session_state["quiz_grade"] = result

    if st.session_state["quiz_mode"] == "challenge":
        st.session_state["challenge_index"] += 1
        if result.correct:
            st.session_state["challenge_correct"] += 1
        if st.session_state["challenge_index"] >= CHALLENGE_COUNT:
            st.session_state["challenge_finished"] = True
            start = st.session_state.get("challenge_started_at") or time.time()
            st.session_state["challenge_seconds"] = max(0.0, time.time() - start)


def _render_settings() -> None:
    with st.expander("出題の設定", expanded=st.session_state["quiz_current"] is None):
        st.multiselect(
            "出題カテゴリ（複数選べます）",
            options=list(quiz.CATEGORY_KEYS),
            key="quiz_categories",
            format_func=quiz.category_label,
        )
        st.radio(
            "難易度",
            options=list(quiz.DIFFICULTIES),
            key="quiz_difficulty",
            format_func=lambda k: quiz.DIFFICULTY_LABELS[k],
            horizontal=True,
        )
        st.radio(
            "モード",
            options=list(_MODES),
            key="quiz_mode",
            format_func=lambda k: _MODES[k],
            on_change=_on_mode_change,
        )
        if not st.session_state["quiz_categories"]:
            st.caption("カテゴリを 1 つ以上選んでください。")


def _render_challenge_result() -> None:
    correct = st.session_state["challenge_correct"]
    seconds = st.session_state["challenge_seconds"]
    st.success(f"{CHALLENGE_COUNT}問チャレンジ終了！")
    left, right = st.columns(2)
    left.metric("スコア", f"{correct} / {CHALLENGE_COUNT}")
    right.metric("所要時間", f"{seconds:.1f} 秒")
    st.caption(f"1問あたり平均 {seconds / CHALLENGE_COUNT:.1f} 秒")
    st.button("もう一度チャレンジする", on_click=_start_challenge, use_container_width=True)


def _render_question(question: quiz.Question) -> None:
    mode = st.session_state["quiz_mode"]
    if mode == "challenge":
        done = st.session_state["challenge_index"]
        st.progress(done / CHALLENGE_COUNT, text=f"{done + 1} 問目 / {CHALLENGE_COUNT}")

    st.caption(f"{quiz.category_label(question.category)} ・ {quiz.DIFFICULTY_LABELS[question.difficulty]}")
    st.markdown(f'<div class="tanin-question">{question.prompt}</div>', unsafe_allow_html=True)
    render_circuit(question.circuit)

    grade = st.session_state["quiz_grade"]
    key = _answer_key()

    if question.kind == "choice":
        st.radio(
            "答えを選んでください",
            options=list(question.choices),
            key=key,
            index=None,
            disabled=grade is not None,
        )
    else:
        numeric_input(
            f"答え（{question.unit}）",
            key=key,
            example="12.5",
            help_text="答えは、小数第2位までのきりのいい数になるよ。",
        )

    if grade is None:
        st.button("答え合わせ", on_click=_submit, args=(question,), use_container_width=True)
        return

    if grade.correct:
        st.success(f"正解！　{grade.correct_answer}")
    else:
        st.error(f"不正解　あなたの答え：{grade.your_answer}／正解：{grade.correct_answer}")
    with st.container(border=True):
        st.markdown("**解きかた**")
        st.markdown(grade.explanation)
        highlight = _TRIANGLE_FOR.get(question.pattern)
        if highlight:
            st.markdown(_TRIANGLE_HINT[highlight])
            render_figure(ohm_triangle_svg(highlight))

    if st.session_state["quiz_mode"] == "challenge" and st.session_state["challenge_finished"]:
        _render_challenge_result()
    else:
        st.button("次の問題へ", on_click=_next_question, use_container_width=True)


def render() -> None:
    st.subheader("練習問題")
    _render_settings()

    mode = st.session_state["quiz_mode"]
    question = st.session_state["quiz_current"]

    if mode == "challenge" and st.session_state["challenge_finished"] and question is None:
        _render_challenge_result()
        return

    if question is None:
        if mode == "challenge":
            st.write(f"連続 {CHALLENGE_COUNT} 問を解いて、スコアと所要時間を記録しましょう。")
            st.button("チャレンジを始める", on_click=_start_challenge, use_container_width=True)
        elif mode == "review":
            pending = history.review_questions(st.session_state["attempts"])
            if not pending:
                st.info("復習リストは空です。間違えた問題がここに貯まります。")
            else:
                st.write(f"復習できる問題が {len(pending)} 問あります。")
                st.button("復習を始める", on_click=_start_review, use_container_width=True)
        else:
            if not st.session_state["quiz_categories"]:
                st.info("出題カテゴリを 1 つ以上選んでください。")
            else:
                st.button("問題を出す", on_click=_next_question, use_container_width=True)
        return

    _render_question(question)
