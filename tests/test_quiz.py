"""tanin.quiz の検証。

もっとも重要なのは「生成した問題の答えが必ずきれいな値になること」と
「その答えが独立に計算した値と一致すること」の 2 点。
"""

from __future__ import annotations

import random
from fractions import Fraction
from typing import Any

import pytest

from tanin import quiz
from tanin.quiz import Question, generate_question, generate_quiz, grade, is_clean


# --------------------------------------------------------------------------
# 独立検算（tanin.ohm を使わず、テスト内で式を書き下す）
# --------------------------------------------------------------------------
def _parallel(values: tuple[Fraction, ...]) -> Fraction:
    return 1 / sum((1 / v for v in values), Fraction(0))


def _expected(question: Question) -> Fraction:
    g: dict[str, Any] = question.given
    pattern = question.pattern
    if pattern == "ohm_voltage":
        return g["R"] * g["I"]
    if pattern == "ohm_current":
        return g["V"] / g["R"]
    if pattern == "ohm_resistance":
        return g["V"] / g["I"]
    if pattern == "unit_voltage":
        return (g["R_kohm"] * 1000) * (g["I_mA"] / 1000)
    if pattern == "unit_current":
        return g["V"] / g["R"] * 1000
    if pattern == "unit_resistance":
        return g["V"] / (g["I_mA"] / 1000) / 1000
    if pattern == "series_total":
        return sum(g["Rs"], Fraction(0))
    if pattern == "series_current":
        return g["V"] / sum(g["Rs"], Fraction(0))
    if pattern == "series_drop":
        return g["Rs"][g["index"]] * g["V"] / sum(g["Rs"], Fraction(0))
    if pattern == "parallel_total":
        return _parallel(g["Rs"])
    if pattern == "parallel_branch":
        return g["V"] / g["Rs"][g["index"]]
    if pattern == "parallel_total_current":
        return sum((g["V"] / r for r in g["Rs"]), Fraction(0))
    if pattern == "combined_series_parallel":
        return g["R1"] + _parallel((g["R2"], g["R3"]))
    if pattern == "combined_parallel_series":
        return _parallel((g["R1"], g["R2"] + g["R3"]))
    if pattern == "combined_two_pairs":
        rs = g["Rs"]
        return _parallel((rs[0], rs[1])) + _parallel((rs[2], rs[3]))
    if pattern == "power_vi":
        return g["V"] * g["I"]
    if pattern == "power_vr":
        return g["V"] * g["V"] / g["R"]
    if pattern == "power_energy":
        return g["P"] * g["t_s"]
    if pattern == "power_kwh":
        return g["P_W"] * g["t_h"] / 1000
    if pattern == "power_heat":
        return g["V"] * g["I"] * g["t_s"]
    raise AssertionError(f"検算式が未定義のパターン: {pattern}")


def _all_questions(count_per_combo: int, seed: int = 20260731) -> list[Question]:
    rng = random.Random(seed)
    questions: list[Question] = []
    for category in quiz.CATEGORY_KEYS:
        for difficulty in quiz.DIFFICULTIES:
            for _ in range(count_per_combo):
                questions.append(generate_question(category, difficulty, rng))
    return questions


# --------------------------------------------------------------------------
# 中核要件
# --------------------------------------------------------------------------
def test_generate_1000_questions_all_have_clean_answers() -> None:
    """1000 問以上を生成し、すべての答えが小数第 2 位までで割り切れることを確認する。"""
    questions = _all_questions(60)  # 6 カテゴリ × 3 難易度 × 60 = 1080 問
    assert len(questions) >= 1000
    for q in questions:
        assert is_clean(q.answer), f"割り切れない答え: {q.pattern} → {q.answer} ({q.prompt})"
        assert (q.answer * 100).denominator == 1


def test_generated_answers_match_independent_calculation() -> None:
    for q in _all_questions(50, seed=7):
        assert q.answer == _expected(q), f"{q.pattern}: {q.answer} != {_expected(q)}"


def test_every_pattern_is_reachable() -> None:
    """定義したすべての出題パターンが実際に生成されること。"""
    seen = {q.pattern for q in _all_questions(80, seed=99)}
    expected = {
        "ohm_voltage",
        "ohm_current",
        "ohm_resistance",
        "unit_voltage",
        "unit_current",
        "unit_resistance",
        "series_total",
        "series_current",
        "series_drop",
        "parallel_total",
        "parallel_branch",
        "parallel_total_current",
        "combined_series_parallel",
        "combined_parallel_series",
        "combined_two_pairs",
        "power_vi",
        "power_vr",
        "power_energy",
        "power_kwh",
        "power_heat",
    }
    assert expected <= seen


def test_questions_are_random() -> None:
    rng = random.Random(1)
    prompts = {generate_question("ohm_basic", "normal", rng).prompt for _ in range(50)}
    assert len(prompts) > 10, "問題が固定化している"


def test_same_seed_reproduces_same_question() -> None:
    a = generate_question("series", "hard", random.Random(42))
    b = generate_question("series", "hard", random.Random(42))
    assert a == b


# --------------------------------------------------------------------------
# 問題の形式
# --------------------------------------------------------------------------
def test_questions_have_prompt_unit_and_explanation() -> None:
    for q in _all_questions(10, seed=3):
        assert q.prompt.strip()
        assert q.unit.strip()
        assert q.explanation.strip()
        assert q.category in quiz.CATEGORY_KEYS
        assert q.difficulty in quiz.DIFFICULTIES


def test_both_numeric_and_choice_are_generated() -> None:
    kinds = {q.kind for q in _all_questions(20, seed=5)}
    assert kinds == {"numeric", "choice"}


def test_choice_questions_are_well_formed() -> None:
    for q in _all_questions(30, seed=11):
        if q.kind != "choice":
            continue
        assert len(q.choices) == 4
        assert len(set(q.choices)) == 4, f"選択肢が重複: {q.choices}"
        assert 0 <= q.answer_index < 4
        assert q.choices[q.answer_index] == q.answer_text


def test_series_and_parallel_questions_carry_circuit_data() -> None:
    for q in _all_questions(15, seed=13):
        if q.category in {"series", "parallel"}:
            assert q.circuit is not None
            assert q.circuit["kind"] in {"series", "parallel"}
            assert len(q.circuit["resistors"]) >= 2


def test_difficulty_changes_the_number_of_resistors() -> None:
    rng = random.Random(2)
    easy = [generate_question("series", "easy", rng) for _ in range(30)]
    hard = [generate_question("series", "hard", rng) for _ in range(30)]
    easy_max = max(len(q.given["Rs"]) for q in easy)
    hard_max = max(len(q.given["Rs"]) for q in hard)
    assert easy_max <= 2 < hard_max


# --------------------------------------------------------------------------
# 再抽選とフォールバック
# --------------------------------------------------------------------------
def test_falls_back_when_every_pattern_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """すべてのパターンが 200 回失敗しても、きれいな答えの問題が返る。"""
    calls = {"n": 0}

    def always_fail(rng: random.Random, difficulty: str) -> None:
        calls["n"] += 1
        return None

    monkeypatch.setitem(quiz._PATTERNS, "series", (always_fail, always_fail))
    question = generate_question("series", "normal", random.Random(0))
    assert calls["n"] == 2 * quiz.MAX_ATTEMPTS  # パターンごとに 200 回まで再抽選した
    assert is_clean(question.answer)
    assert question.answer == _expected(question)


@pytest.mark.parametrize("category", quiz.CATEGORY_KEYS)
def test_fallback_is_clean_for_every_category(category: str) -> None:
    for seed in range(20):
        question = quiz._fallback(random.Random(seed), category, "normal")
        assert is_clean(question.answer)
        assert question.answer == _expected(question)


def test_unknown_category_or_difficulty_raises() -> None:
    with pytest.raises(ValueError):
        generate_question("magnetism", "normal")
    with pytest.raises(ValueError):
        generate_question("ohm_basic", "impossible")


# --------------------------------------------------------------------------
# 10 問チャレンジ
# --------------------------------------------------------------------------
def test_generate_quiz_returns_requested_count() -> None:
    questions = generate_quiz(["ohm_basic", "power"], "normal", 10, random.Random(4))
    assert len(questions) == 10
    assert {q.category for q in questions} == {"ohm_basic", "power"}
    assert all(is_clean(q.answer) for q in questions)


def test_generate_quiz_requires_categories() -> None:
    with pytest.raises(ValueError):
        generate_quiz([], "normal", 10)


# --------------------------------------------------------------------------
# 採点
# --------------------------------------------------------------------------
def test_grade_numeric_accepts_exact_and_rounded_answers() -> None:
    q = Question(
        category="ohm_basic",
        difficulty="easy",
        pattern="ohm_voltage",
        prompt="?",
        answer=Fraction(6),
        unit="V",
        explanation="",
    )
    assert grade(q, "6").correct
    assert grade(q, " 6.00 ").correct
    assert grade(q, "６").correct  # 全角
    assert not grade(q, "60").correct
    assert not grade(q, "").correct
    assert not grade(q, "abc").correct


def test_grade_numeric_tolerance() -> None:
    q = Question(
        category="ohm_basic",
        difficulty="easy",
        pattern="ohm_current",
        answer=Fraction(33, 100),
        prompt="?",
        unit="A",
        explanation="",
    )
    assert grade(q, "0.33").correct
    assert grade(q, "0.334").correct  # 許容誤差 ±0.005 以内
    assert not grade(q, "0.34").correct


def test_grade_choice() -> None:
    q = Question(
        category="series",
        difficulty="easy",
        pattern="series_total",
        prompt="?",
        answer=Fraction(30),
        unit="Ω",
        explanation="",
        kind="choice",
        choices=("10 Ω", "30 Ω", "20 Ω", "5 Ω"),
        answer_index=1,
    )
    assert grade(q, 1).correct
    assert grade(q, "30 Ω").correct
    assert not grade(q, 0).correct
    assert grade(q, None).your_answer == "（未回答）"


def test_grade_reports_correct_answer_and_explanation() -> None:
    q = generate_question("power", "easy", random.Random(8))
    result = grade(q, "-1")
    assert not result.correct
    assert result.correct_answer == q.answer_text
    assert result.explanation == q.explanation


# --------------------------------------------------------------------------
# JSON 往復（復習リストの保存・復元に使う）
# --------------------------------------------------------------------------
def test_question_json_round_trip() -> None:
    for q in _all_questions(5, seed=17):
        restored = Question.from_dict(q.to_dict())
        assert restored == q
        assert restored.answer == q.answer
        assert restored.given == q.given
