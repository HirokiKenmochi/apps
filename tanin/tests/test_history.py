"""tanin.history の検証（履歴の集計と JSON 往復）。"""

from __future__ import annotations

import random

import pytest

from tanin import history
from tanin.history import Attempt, by_category, from_json, make_attempt, summarize, to_json, trend
from tanin.quiz import generate_question


def _attempt(category: str = "ohm_basic", correct: bool = True, seconds: float = 1.0) -> Attempt:
    return Attempt(
        category=category,
        difficulty="easy",
        pattern="ohm_voltage",
        prompt=f"{category} の問題 {correct}",
        kind="numeric",
        correct=correct,
        your_answer="6 V",
        correct_answer="6 V",
        seconds=seconds,
    )


def test_summarize_empty() -> None:
    summary = summarize([])
    assert summary.total == 0
    assert summary.accuracy == 0.0
    assert summary.best_streak == 0


def test_summarize_counts_and_streaks() -> None:
    attempts = [
        _attempt(correct=True),
        _attempt(correct=True),
        _attempt(correct=False),
        _attempt(correct=True),
        _attempt(correct=True),
        _attempt(correct=True),
    ]
    summary = summarize(attempts)
    assert summary.total == 6
    assert summary.correct == 5
    assert summary.accuracy == pytest.approx(5 / 6)
    assert summary.best_streak == 3
    assert summary.current_streak == 3
    assert summary.total_seconds == pytest.approx(6.0)


def test_current_streak_breaks_on_last_mistake() -> None:
    attempts = [_attempt(correct=True), _attempt(correct=False)]
    assert summarize(attempts).current_streak == 0


def test_by_category() -> None:
    attempts = [
        _attempt("series", correct=True),
        _attempt("series", correct=False),
        _attempt("power", correct=True),
    ]
    stats = {s.category: s for s in by_category(attempts)}
    assert stats["series"].total == 2
    assert stats["series"].accuracy == pytest.approx(0.5)
    assert stats["power"].accuracy == pytest.approx(1.0)
    assert stats["series"].label == "直列回路"


def test_trend_returns_last_20_with_running_accuracy() -> None:
    attempts = [_attempt(correct=n % 2 == 0) for n in range(30)]
    rows = trend(attempts, 20)
    assert len(rows) == 20
    assert rows[0]["問題番号"] == 11
    assert rows[-1]["問題番号"] == 30
    assert all(0 <= row["正答率(%)"] <= 100 for row in rows)


def test_review_list_collects_mistakes_and_clears_on_success() -> None:
    rng = random.Random(3)
    question = generate_question("ohm_basic", "easy", rng)
    wrong = make_attempt(question, correct=False, your_answer="0 V", seconds=2.0)
    assert [q.prompt for q in history.review_questions([wrong])] == [question.prompt]

    right = make_attempt(question, correct=True, your_answer=question.answer_text, seconds=1.0)
    assert history.review_questions([wrong, right]) == []


def test_review_questions_restores_full_question() -> None:
    rng = random.Random(9)
    question = generate_question("parallel", "normal", rng)
    attempts = [make_attempt(question, correct=False, your_answer="x")]
    restored = history.review_questions(attempts)[0]
    assert restored == question


def test_json_round_trip() -> None:
    rng = random.Random(5)
    attempts = [
        make_attempt(generate_question(c, "normal", rng), correct=n % 2 == 0, your_answer="1", seconds=n)
        for n, c in enumerate(("ohm_basic", "series", "power"))
    ]
    restored = from_json(to_json(attempts))
    assert restored == attempts


def test_from_json_rejects_broken_input() -> None:
    with pytest.raises(ValueError):
        from_json("{ not json")
    with pytest.raises(ValueError):
        from_json('{"version": 1}')
    with pytest.raises(ValueError):
        from_json('{"attempts": "nope"}')


def test_from_json_accepts_bytes() -> None:
    attempts = [_attempt()]
    assert from_json(to_json(attempts).encode("utf-8")) == attempts
