"""学習履歴の集計（Streamlit 非依存の純粋 Python モジュール）。

履歴はアプリの ``st.session_state`` に置かれる :class:`Attempt` のリストで、
サーバーには保存しない。JSON に書き出してブラウザにダウンロードし、
あとから読み込んで復元できる。
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from tanin.quiz import Question, category_label

__all__ = [
    "Attempt",
    "CategoryStat",
    "Summary",
    "by_category",
    "make_attempt",
    "recent",
    "review_questions",
    "summarize",
    "to_json",
    "trend",
    "from_json",
]

FORMAT_VERSION = 1


@dataclass(frozen=True)
class Attempt:
    """1 問分の解答記録。"""

    category: str
    difficulty: str
    pattern: str
    prompt: str
    kind: str
    correct: bool
    your_answer: str
    correct_answer: str
    seconds: float = 0.0
    question: dict[str, Any] | None = None

    @property
    def category_label(self) -> str:
        return category_label(self.category)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "difficulty": self.difficulty,
            "pattern": self.pattern,
            "prompt": self.prompt,
            "kind": self.kind,
            "correct": self.correct,
            "your_answer": self.your_answer,
            "correct_answer": self.correct_answer,
            "seconds": self.seconds,
            "question": self.question,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Attempt:
        return cls(
            category=str(data.get("category", "")),
            difficulty=str(data.get("difficulty", "")),
            pattern=str(data.get("pattern", "")),
            prompt=str(data.get("prompt", "")),
            kind=str(data.get("kind", "numeric")),
            correct=bool(data.get("correct", False)),
            your_answer=str(data.get("your_answer", "")),
            correct_answer=str(data.get("correct_answer", "")),
            seconds=float(data.get("seconds", 0.0) or 0.0),
            question=data.get("question"),
        )


def make_attempt(question: Question, correct: bool, your_answer: str, seconds: float = 0.0) -> Attempt:
    """問題と採点結果から履歴レコードを作る。"""
    return Attempt(
        category=question.category,
        difficulty=question.difficulty,
        pattern=question.pattern,
        prompt=question.prompt,
        kind=question.kind,
        correct=correct,
        your_answer=your_answer,
        correct_answer=question.answer_text,
        seconds=float(seconds),
        question=question.to_dict(),
    )


# --------------------------------------------------------------------------
# 集計
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Summary:
    total: int
    correct: int
    accuracy: float
    current_streak: int
    best_streak: int
    total_seconds: float

    @property
    def accuracy_percent(self) -> float:
        return self.accuracy * 100


def summarize(attempts: Sequence[Attempt]) -> Summary:
    """全体の成績。``accuracy`` は 0.0〜1.0。"""
    total = len(attempts)
    correct = sum(1 for a in attempts if a.correct)
    best = streak = 0
    for a in attempts:
        streak = streak + 1 if a.correct else 0
        best = max(best, streak)
    current = 0
    for a in reversed(attempts):
        if not a.correct:
            break
        current += 1
    return Summary(
        total=total,
        correct=correct,
        accuracy=correct / total if total else 0.0,
        current_streak=current,
        best_streak=best,
        total_seconds=sum(a.seconds for a in attempts),
    )


@dataclass(frozen=True)
class CategoryStat:
    category: str
    label: str
    total: int
    correct: int
    accuracy: float

    @property
    def accuracy_percent(self) -> float:
        return self.accuracy * 100


def by_category(attempts: Sequence[Attempt]) -> list[CategoryStat]:
    """カテゴリ別の正答率（出題数の多い順）。"""
    buckets: dict[str, list[Attempt]] = {}
    for a in attempts:
        buckets.setdefault(a.category, []).append(a)
    stats = [
        CategoryStat(
            category=key,
            label=category_label(key),
            total=len(items),
            correct=sum(1 for x in items if x.correct),
            accuracy=sum(1 for x in items if x.correct) / len(items),
        )
        for key, items in buckets.items()
    ]
    return sorted(stats, key=lambda s: (-s.total, s.category))


def recent(attempts: Sequence[Attempt], count: int = 20) -> list[Attempt]:
    """直近 ``count`` 問（古い順）。"""
    return list(attempts[-count:])


def trend(attempts: Sequence[Attempt], count: int = 20) -> list[dict[str, Any]]:
    """直近 ``count`` 問の推移（グラフ用）。

    ``正解=1 / 不正解=0`` と、そこまでの累積正答率（％）を返す。
    """
    latest = recent(attempts, count)
    offset = len(attempts) - len(latest)
    rows: list[dict[str, Any]] = []
    correct = 0
    for n, attempt in enumerate(latest, start=1):
        correct += 1 if attempt.correct else 0
        rows.append(
            {
                "問題番号": offset + n,
                "正誤": 1 if attempt.correct else 0,
                "正答率(%)": round(correct / n * 100, 1),
                "カテゴリ": attempt.category_label,
            }
        )
    return rows


def review_questions(attempts: Sequence[Attempt]) -> list[Question]:
    """復習リスト：同じ問題文の最後の解答が不正解だったものを返す。

    復習で正解すればリストから自動的に消える。
    """
    latest: dict[str, Attempt] = {}
    order: list[str] = []
    for a in attempts:
        if a.question is None:
            continue
        if a.prompt not in latest:
            order.append(a.prompt)
        latest[a.prompt] = a
    questions: list[Question] = []
    for prompt in order:
        attempt = latest[prompt]
        if attempt.correct or attempt.question is None:
            continue
        try:
            questions.append(Question.from_dict(attempt.question))
        except (KeyError, ValueError, TypeError):
            continue
    return questions


# --------------------------------------------------------------------------
# 保存・復元
# --------------------------------------------------------------------------
def to_json(attempts: Iterable[Attempt], *, indent: int = 2) -> str:
    """履歴を JSON 文字列にする（ダウンロード用）。"""
    payload = {
        "app": "TanIn",
        "version": FORMAT_VERSION,
        "attempts": [a.to_dict() for a in attempts],
    }
    return json.dumps(payload, ensure_ascii=False, indent=indent)


def from_json(text: str | bytes) -> list[Attempt]:
    """JSON 文字列から履歴を復元する。壊れていれば ValueError。"""
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON として読めません: {exc}") from exc
    if not isinstance(payload, dict) or "attempts" not in payload:
        raise ValueError("TanIn の履歴ファイルではありません")
    raw = payload.get("attempts")
    if not isinstance(raw, list):
        raise ValueError("attempts が配列ではありません")
    attempts: list[Attempt] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("履歴の要素が壊れています")
        attempts.append(Attempt.from_dict(item))
    return attempts
