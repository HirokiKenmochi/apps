"""問題の自動生成と採点（Streamlit 非依存の純粋 Python モジュール）。

生成方針
--------
* 問題は毎回ランダムに作る。固定の問題リストは持たない。
* **答えがきれいな値になること**を最優先する。候補となる抵抗値・電圧値・電流値の
  集合からパラメータを選び、計算結果が「小数第 2 位までで割り切れる」ものだけを
  採用する（条件を満たすまで再抽選）。
* 再抽選が :data:`MAX_ATTEMPTS` 回を超えたらそのパターンは諦め、
  同じカテゴリの別パターンにフォールバックする。すべて失敗した場合は
  「構成上かならずきれいな値になる」フォールバック問題を返す。
* 4 択の誤答は「単位換算を忘れた値」「掛け算と割り算を逆にした値」など、
  ありがちな間違いから作る。
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from typing import Any

from tanin import ohm, units
from tanin.ohm import fmt
from tanin.units import parse_number

__all__ = [
    "CATEGORIES",
    "CATEGORY_KEYS",
    "DIFFICULTIES",
    "DIFFICULTY_LABELS",
    "MAX_ATTEMPTS",
    "TOLERANCE",
    "Category",
    "Grade",
    "LEARNING_STEPS",
    "LearningStep",
    "Question",
    "STEP_GOAL_CORRECT",
    "category_label",
    "generate_question",
    "generate_quiz",
    "grade",
    "is_clean",
    "labelled",
]

MAX_ATTEMPTS = 200
"""1 つの出題パターンで許す再抽選の上限。"""

TOLERANCE = Fraction(1, 200)
"""数値入力の許容誤差（±0.005）。答えは小数第 2 位までなので四捨五入を許す。"""


# --------------------------------------------------------------------------
# カテゴリと難易度
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Category:
    key: str
    label: str
    description: str


CATEGORIES: tuple[Category, ...] = (
    Category("even_odd", "偶数と奇数", "2でわり切れる数の見分け方（小学生向け）"),
    Category("multiplication", "かけ算の筆算", "整数・小数のかけ算（小学生向け）"),
    Category("division", "わり算の筆算", "整数・小数のわり算（小学生向け）"),
    Category("decimal_point", "小数点の動かし方", "10倍・100倍・1000倍と、10・100・1000でわる計算"),
    Category("unit_convert", "単位の変換", "cm と m、g と kg、mL と L、分と秒など（小学生向け）"),
    Category("ohm_basic", "オームの法則の基本", "V=RI / I=V÷R / R=V÷I"),
    Category("unit_calc", "単位の換算", "mA・kΩ を含む計算"),
    Category("series", "直列回路", "合成抵抗・電流・各抵抗の電圧"),
    Category("parallel", "並列回路", "各枝の電流・全体の電流・合成抵抗"),
    Category("combined", "合成抵抗", "直列・並列・直並列の組み合わせ"),
    Category("power", "電力・電力量・熱量", "P=VI、J=Pt、kWh"),
)
CATEGORY_KEYS: tuple[str, ...] = tuple(c.key for c in CATEGORIES)

DIFFICULTIES: tuple[str, ...] = ("easy", "normal", "hard")
DIFFICULTY_LABELS: dict[str, str] = {
    "easy": "やさしい",
    "normal": "ふつう",
    "hard": "むずかしい",
}


@dataclass(frozen=True)
class LearningStep:
    """学習の順番（やさしい順）。UI はこの順にボタンを並べる。"""

    order: int
    title: str
    category: str
    difficulty: str
    goal: str


LEARNING_STEPS: tuple[LearningStep, ...] = (
    LearningStep(1, "偶数と奇数を見分ける", "even_odd", "easy", "一の位を見れば、2 でわり切れるかわかる"),
    LearningStep(2, "かけ算の筆算", "multiplication", "easy", "一の位から順に、くり上がりに気をつける"),
    LearningStep(3, "わり算の筆算", "division", "easy", "上の位から「たてる・かける・ひく・おろす」"),
    LearningStep(4, "小数点の動かし方", "decimal_point", "easy", "10倍・100倍・1000倍で小数点が動く"),
    LearningStep(5, "単位の変換", "unit_convert", "easy", "cm と m、g と kg、mL と L、分と秒"),
    LearningStep(6, "オームの法則", "ohm_basic", "easy", "三角形で V＝R×I を使えるようにする"),
    LearningStep(7, "mA・kΩ の計算", "unit_calc", "normal", "単位をそろえてから計算する"),
    LearningStep(8, "直列回路", "series", "normal", "合成抵抗は足し算。電流はどこでも同じ"),
    LearningStep(9, "並列回路", "parallel", "normal", "どの道にも同じ電圧。電流は分かれる"),
    LearningStep(10, "合成抵抗（直列＋並列）", "combined", "normal", "まとめられるところからまとめる"),
    LearningStep(11, "電力・電力量・熱量", "power", "normal", "P＝V×I、熱量＝P×時間（秒）"),
)

STEP_GOAL_CORRECT = 5
"""1 つのステップを「できた」とみなす正解数。"""


def category_label(key: str) -> str:
    for c in CATEGORIES:
        if c.key == key:
            return c.label
    return key


# --------------------------------------------------------------------------
# 問題
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Question:
    """1 問分のデータ。UI から独立していて、JSON にも書き出せる。"""

    category: str
    difficulty: str
    pattern: str
    prompt: str
    answer: Fraction
    unit: str
    explanation: str
    kind: str = "numeric"  # "numeric" | "choice"
    choices: tuple[str, ...] = ()
    answer_index: int = -1
    given: dict[str, Any] = field(default_factory=dict)
    circuit: dict[str, Any] | None = None

    @property
    def answer_text(self) -> str:
        return labelled(self.answer, self.unit)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "difficulty": self.difficulty,
            "pattern": self.pattern,
            "prompt": self.prompt,
            "answer": str(self.answer),
            "unit": self.unit,
            "explanation": self.explanation,
            "kind": self.kind,
            "choices": list(self.choices),
            "answer_index": self.answer_index,
            "given": {k: _encode(v) for k, v in self.given.items()},
            "circuit": self.circuit,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Question:
        return cls(
            category=str(data["category"]),
            difficulty=str(data["difficulty"]),
            pattern=str(data["pattern"]),
            prompt=str(data["prompt"]),
            answer=Fraction(str(data["answer"])),
            unit=str(data["unit"]),
            explanation=str(data["explanation"]),
            kind=str(data.get("kind", "numeric")),
            choices=tuple(data.get("choices") or ()),
            answer_index=int(data.get("answer_index", -1)),
            given={k: _decode(v) for k, v in (data.get("given") or {}).items()},
            circuit=data.get("circuit"),
        )


def _encode(value: Any) -> Any:
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, (tuple, list)):
        return [_encode(v) for v in value]
    return value


def _decode(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_decode(v) for v in value)
    if isinstance(value, str) and (value.isdigit() or "/" in value or _looks_numeric(value)):
        try:
            return Fraction(value)
        except (ValueError, ZeroDivisionError):
            return value
    return value


def _looks_numeric(text: str) -> bool:
    try:
        Fraction(text)
    except (ValueError, ZeroDivisionError):
        return False
    return True


# --------------------------------------------------------------------------
# きれいな値の判定
# --------------------------------------------------------------------------
def labelled(value: Fraction, unit: str) -> str:
    """「12.5 cm」のように値と単位をつなぐ（単位なしの問題では数だけ）。"""
    return f"{fmt(value)} {unit}".strip()


def is_clean(value: Fraction, max_decimals: int = 2) -> bool:
    """指定した小数位までで割り切れ、学習に使える大きさの正の値か。

    ふつうの問題は小数第 2 位まで。小数点の練習だけは第 3 位まで許す
    （1000 でわると 0.003 のように 3 けたになるため）。
    """
    if value <= 0:
        return False
    if (value * 10 ** max_decimals).denominator != 1:
        return False
    return value <= 10_000_000


def _round2(value: Fraction) -> Fraction:
    """誤答候補を小数第 2 位に丸める。"""
    return Fraction(round(value * 100), 100)


# --------------------------------------------------------------------------
# 解説文
#
# 小学生でも読めるように、次の順番で短く書く。
#   ① つかう式（ことばの式 → 記号の式）
#   ② 数を入れる
#   ③ 答え
#   ポイント：なぜそうなるかを、ひとことで
# --------------------------------------------------------------------------
def _steps(*lines: str) -> str:
    return "\n\n".join(line for line in lines if line)


_SHIFT_WORDS: dict[int, str] = {1: "10", 2: "100", 3: "1000"}


def _decimal_places(value: Fraction) -> int:
    """小数第何位まであるか（10 の累乗で表せない値は 0 を返す）。"""
    text = fmt(value)
    if "." not in text or "e" in text:
        return 0
    return len(text.split(".")[1])


def _power_of_ten(ratio: Fraction) -> int | None:
    """10 の何乗かを返す（10・100・1000 … でないときは None）。"""
    for power in range(-6, 7):
        if ratio == Fraction(10) ** power:
            return power
    return None


def _shift_note(before: Fraction, after: Fraction, power: int) -> str:
    """10倍・100倍・1000倍のときに、小数点をどちらへいくつ動かすかを説明する。"""
    n = abs(power)
    if n not in _SHIFT_WORDS:
        return ""
    side = "右" if power > 0 else "左"
    how = f"{_SHIFT_WORDS[n]} をかける" if power > 0 else f"{_SHIFT_WORDS[n]} でわる"
    return f"（{how}ので、小数点を{side}に {n} つ動かす：{fmt(before)} → {fmt(after)}）"


def _division_note(a: Fraction, b: Fraction) -> str:
    """わる数が小数のとき、筆算できる形（整数でわる形）に直す言い方を返す。"""
    places = _decimal_places(b)
    if places == 0 or places > 3:
        return ""
    factor = 10 ** places
    return (
        f"わる数が小数のときは、わる数とわられる数を同じだけ {factor} 倍する"
        f"（小数点を右に {places} つ）。{fmt(a)} ÷ {fmt(b)} → **{fmt(a * factor)} ÷ {fmt(b * factor)}** "
        "にすれば筆算できるよ。答えは変わらない。"
    )


def _exp_voltage(r: Fraction, i: Fraction, v: Fraction) -> str:
    return _steps(
        "① つかう式は **電圧 ＝ 抵抗 × 電流**（V = R × I）",
        f"② 数を入れる：{fmt(r)} × {fmt(i)}",
        f"③ 計算すると **{fmt(v)} V**",
        "ポイント：電流が同じなら、抵抗が大きいほど電圧も大きくなるよ。",
    )


def _exp_current(v: Fraction, r: Fraction, i: Fraction) -> str:
    return _steps(
        "① つかう式は **電流 ＝ 電圧 ÷ 抵抗**（I = V ÷ R）",
        f"② 数を入れる：{fmt(v)} ÷ {fmt(r)}",
        _division_note(v, r),
        f"③ 筆算すると **{fmt(i)} A**",
        "ポイント：抵抗は電気の「通りにくさ」。大きいほど電流は少なくなるよ。",
    )


def _exp_resistance(v: Fraction, i: Fraction, r: Fraction) -> str:
    return _steps(
        "① つかう式は **抵抗 ＝ 電圧 ÷ 電流**（R = V ÷ I）",
        f"② 数を入れる：{fmt(v)} ÷ {fmt(i)}",
        _division_note(v, i),
        f"③ 筆算すると **{fmt(r)} Ω**",
        "ポイント：同じ電圧でも、流れる電流が少ないほど抵抗は大きいよ。",
    )


def _exp_unit_voltage(r_k: Fraction, i_ma: Fraction, v: Fraction) -> str:
    return _steps(
        "① まず単位をそろえる。"
        f"1 kΩ = 1000 Ω なので {fmt(r_k)} kΩ = {fmt(r_k * 1000)} Ω"
        + _shift_note(r_k, r_k * 1000, 3),
        f"　1 mA = 0.001 A なので {fmt(i_ma)} mA = {fmt(i_ma / 1000)} A"
        + _shift_note(i_ma, i_ma / 1000, -3),
        "② つかう式は **電圧 ＝ 抵抗 × 電流**",
        f"③ {fmt(r_k * 1000)} × {fmt(i_ma / 1000)} = **{fmt(v)} V**",
        "ポイント：kΩ と mA はそのままかけ算しても V になるよ"
        "（1000倍と1000分の1で打ち消し合うから）。",
    )


def _exp_unit_current(v: Fraction, r: Fraction, i_ma: Fraction) -> str:
    return _steps(
        f"① まず A（アンペア）で計算する。電流 ＝ 電圧 ÷ 抵抗 → "
        f"{fmt(v)} ÷ {fmt(r)} = {fmt(i_ma / 1000)} A",
        _division_note(v, r),
        "② mA に直す。1 A = 1000 mA だから 1000 をかける"
        + _shift_note(i_ma / 1000, i_ma, 3),
        f"③ 答えは **{fmt(i_ma)} mA**",
        "ポイント：A から mA は 1000倍、mA から A は 1000でわる。",
    )


def _exp_unit_resistance(v: Fraction, i_ma: Fraction, r_k: Fraction) -> str:
    return _steps(
        f"① mA を A に直す。{fmt(i_ma)} mA = {fmt(i_ma / 1000)} A"
        + _shift_note(i_ma, i_ma / 1000, -3),
        f"② 抵抗 ＝ 電圧 ÷ 電流 → {fmt(v)} ÷ {fmt(i_ma / 1000)} = {fmt(r_k * 1000)} Ω",
        _division_note(v, i_ma / 1000),
        f"③ kΩ に直す。**{fmt(r_k)} kΩ**" + _shift_note(r_k * 1000, r_k, -3),
        "ポイント：V ÷ mA でそのまま kΩ が出るよ。",
    )


def _exp_series_total(rs: Sequence[Fraction], total: Fraction) -> str:
    return _steps(
        "① 直列（一本道）のつなぎ方では、抵抗はぜんぶ足すだけ。",
        "② " + " + ".join(fmt(r) for r in rs) + f" = **{fmt(total)} Ω**",
        "ポイント：道が長くなるほど通りにくいので、合計はどの抵抗よりも大きくなるよ。",
    )


def _exp_series_current(v: Fraction, rs: Sequence[Fraction], total: Fraction, i: Fraction) -> str:
    return _steps(
        "① まず合成抵抗を出す。直列は足し算 → "
        + " + ".join(fmt(r) for r in rs)
        + f" = {fmt(total)} Ω",
        f"② 電流 ＝ 電圧 ÷ 合成抵抗 → {fmt(v)} ÷ {fmt(total)} = **{fmt(i)} A**",
        _division_note(v, total),
        "ポイント：直列は一本道だから、電流はどこで測っても同じ大きさだよ。",
    )


def _exp_series_drop(
    v: Fraction, rs: Sequence[Fraction], total: Fraction, i: Fraction, index: int
) -> str:
    return _steps(
        "① 合成抵抗を出す。直列は足し算 → " + " + ".join(fmt(r) for r in rs) + f" = {fmt(total)} Ω",
        f"② 回路に流れる電流を出す。{fmt(v)} ÷ {fmt(total)} = {fmt(i)} A（一本道なのでどこでも同じ）",
        f"③ R{index + 1} にかかる電圧 ＝ 抵抗 × 電流 → "
        f"{fmt(rs[index])} × {fmt(i)} = **{fmt(rs[index] * i)} V**",
        "ポイント：直列では、抵抗が大きいところほど電圧をたくさん使うよ。",
    )


def _exp_parallel_total(rs: Sequence[Fraction], total: Fraction) -> str:
    shortcut = ""
    if len(rs) == 2:
        a, b = rs
        shortcut = (
            f"かんたんな方法（2本のとき）：かけ算 ÷ 足し算 → "
            f"({fmt(a)} × {fmt(b)}) ÷ ({fmt(a)} + {fmt(b)}) = {fmt(total)} Ω"
        )
    return _steps(
        "① 並列（分かれ道）は、逆数（1 ÷ その数）を足してから、また 1 でわる。",
        "② 1/R = " + " + ".join(f"1/{fmt(r)}" for r in rs),
        f"③ 計算すると **{fmt(total)} Ω**",
        shortcut,
        "ポイント：道が増えると電気は通りやすくなるので、答えはどの抵抗よりも小さくなるよ。",
    )


def _exp_parallel_branch(v: Fraction, r: Fraction, i: Fraction, index: int) -> str:
    return _steps(
        f"① 並列（分かれ道）では、どの道にも電源と同じ {fmt(v)} V がかかる。",
        f"② 電流 ＝ 電圧 ÷ 抵抗 → {fmt(v)} ÷ {fmt(r)} = **{fmt(i)} A**",
        _division_note(v, r),
        f"ポイント：R{index + 1} の道だけを見て計算すればよいよ。",
    )


def _exp_parallel_total_current(
    v: Fraction, rs: Sequence[Fraction], branches: Sequence[Fraction], total_i: Fraction
) -> str:
    return _steps(
        "① 道ごとの電流を出す。"
        + "、".join(f"{fmt(v)} ÷ {fmt(r)} = {fmt(b)} A" for r, b in zip(rs, branches, strict=True)),
        "② ぜんぶ足す。" + " + ".join(fmt(b) for b in branches) + f" = **{fmt(total_i)} A**",
        "ポイント：分かれ道の電流を合わせたものが、電池から出ていく電流だよ。",
    )


def _exp_combined(first: str, second: str, answer: Fraction) -> str:
    return _steps(
        f"① {first}",
        f"② {second}",
        f"③ 答えは **{fmt(answer)} Ω**",
        "ポイント：ふくざつな回路は、まとめられるところから 1 つの抵抗にまとめていくよ。",
    )


def _exp_power_vi(v: Fraction, i: Fraction, p: Fraction) -> str:
    return _steps(
        "① つかう式は **電力 ＝ 電圧 × 電流**（P = V × I）",
        f"② 数を入れる：{fmt(v)} × {fmt(i)}",
        f"③ 計算すると **{fmt(p)} W**",
        "ポイント：W（ワット）は「1秒でどれだけ電気を使うか」を表す数だよ。",
    )


def _exp_power_vr(v: Fraction, r: Fraction, p: Fraction) -> str:
    return _steps(
        f"① まず電流を出す。電流 ＝ 電圧 ÷ 抵抗 → {fmt(v)} ÷ {fmt(r)} = {fmt(v / r)} A",
        _division_note(v, r),
        f"② 電力 ＝ 電圧 × 電流 → {fmt(v)} × {fmt(v / r)} = **{fmt(p)} W**",
        "ポイント：P = 電圧 × 電圧 ÷ 抵抗 で一気に出しても同じ答えになるよ。",
    )


def _exp_power_energy(p: Fraction, minutes: Fraction, seconds: Fraction, joules: Fraction) -> str:
    return _steps(
        f"① 時間を秒に直す。{fmt(minutes)} 分 × 60 = {fmt(seconds)} 秒",
        f"② 熱量 ＝ 電力 × 時間（秒）→ {fmt(p)} × {fmt(seconds)} = **{fmt(joules)} J**",
        "ポイント：J（ジュール）は「ワット × 秒」。分のままかけるとまちがいだよ。",
    )


def _exp_power_kwh(p: Fraction, hours: Fraction, kwh: Fraction) -> str:
    return _steps(
        f"① W を kW に直す。1 kW = 1000 W だから {fmt(p)} ÷ 1000 = {fmt(p / 1000)} kW"
        + _shift_note(p, p / 1000, -3),
        f"② 電力量 ＝ kW × 時間 → {fmt(p / 1000)} × {fmt(hours)} = **{fmt(kwh)} kWh**",
        "ポイント：電気料金の計算に使う単位。W のままかけると 1000倍まちがえるよ。",
    )


def _exp_power_heat(
    v: Fraction, i: Fraction, p: Fraction, minutes: Fraction, seconds: Fraction, joules: Fraction
) -> str:
    return _steps(
        f"① 電力を出す。電力 ＝ 電圧 × 電流 → {fmt(v)} × {fmt(i)} = {fmt(p)} W",
        f"② 時間を秒に直す。{fmt(minutes)} 分 × 60 = {fmt(seconds)} 秒",
        f"③ 熱量 ＝ 電力 × 秒 → {fmt(p)} × {fmt(seconds)} = **{fmt(joules)} J**",
        "ポイント：電気で出る熱の量も、電力に時間をかけるだけで求められるよ。",
    )


# --------------------------------------------------------------------------
# 候補値（難易度別）
# --------------------------------------------------------------------------
def _f(*values: str) -> tuple[Fraction, ...]:
    return tuple(Fraction(Decimal(v)) for v in values)


_RESISTANCES: dict[str, tuple[Fraction, ...]] = {
    "easy": _f("2", "4", "5", "10", "15", "20", "25", "30", "50", "100"),
    "normal": _f(
        "2", "3", "4", "5", "6", "8", "10", "12", "15", "20",
        "24", "25", "30", "40", "50", "60", "80", "100", "120",
    ),
    "hard": _f(
        "1.5", "2.5", "3", "4", "6", "7.5", "8", "12", "15", "16", "18", "20",
        "24", "30", "36", "40", "45", "48", "60", "75", "90", "120", "150", "200",
    ),
}

_CURRENTS: dict[str, tuple[Fraction, ...]] = {
    "easy": _f("0.1", "0.2", "0.5", "1", "2"),
    "normal": _f("0.05", "0.1", "0.2", "0.25", "0.3", "0.4", "0.5", "0.8", "1", "1.5", "2", "3"),
    "hard": _f(
        "0.02", "0.04", "0.05", "0.12", "0.15", "0.25", "0.35",
        "0.45", "0.6", "0.75", "1.2", "1.6", "2.5", "4",
    ),
}

_VOLTAGES: dict[str, tuple[Fraction, ...]] = {
    "easy": _f("3", "6", "9", "12"),
    "normal": _f("1.5", "3", "4.5", "6", "9", "12", "15", "20", "24", "30", "100"),
    "hard": _f("1.5", "4.5", "7.5", "12", "18", "24", "36", "48", "60", "100", "110", "200"),
}

_KILOHMS: dict[str, tuple[Fraction, ...]] = {
    "easy": _f("1", "2", "5", "10"),
    "normal": _f("0.5", "1", "1.2", "2", "2.5", "3", "4", "5", "10"),
    "hard": _f("0.1", "0.25", "0.5", "1.5", "2.2", "3.3", "4.7", "6.8", "8.2", "12"),
}

_MILLIAMPS: dict[str, tuple[Fraction, ...]] = {
    "easy": _f("1", "2", "5", "10"),
    "normal": _f("0.5", "1", "2", "4", "5", "8", "10", "20", "25"),
    "hard": _f("0.2", "1.5", "2.5", "3", "6", "12", "15", "30", "40", "50", "120"),
}

_POWERS: dict[str, tuple[Fraction, ...]] = {
    "easy": _f("10", "20", "40", "60", "100"),
    "normal": _f("15", "20", "40", "60", "80", "100", "250", "500", "600", "1000"),
    "hard": _f("35", "45", "75", "120", "350", "450", "750", "800", "1200", "1500"),
}

_RESISTOR_COUNT: dict[str, tuple[int, ...]] = {
    "easy": (2,),
    "normal": (2, 3),
    "hard": (3, 4),
}


def _pick(rng: random.Random, values: Sequence[Fraction]) -> Fraction:
    return rng.choice(list(values))


def _pick_resistances(rng: random.Random, difficulty: str, count: int | None = None) -> tuple[Fraction, ...]:
    pool = _RESISTANCES[difficulty]
    n = count if count is not None else rng.choice(_RESISTOR_COUNT[difficulty])
    n = min(n, len(pool))
    return tuple(rng.sample(list(pool), n))


# --------------------------------------------------------------------------
# 問題の組み立て
# --------------------------------------------------------------------------
def _choices(
    rng: random.Random,
    answer: Fraction,
    distractors: Sequence[Fraction],
    unit: str,
) -> tuple[tuple[str, ...], int] | None:
    """ありがちな間違いから 4 択を作る。3 つ集まらなければ None。"""
    pool: list[Fraction] = []
    for raw in distractors:
        try:
            candidate = _round2(Fraction(raw))
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        if candidate <= 0 or candidate == answer or candidate in pool:
            continue
        if candidate > 100_000_000:
            continue
        pool.append(candidate)

    for factor in (Fraction(10), Fraction(1, 10), Fraction(2), Fraction(1, 2), Fraction(100)):
        if len(pool) >= 3:
            break
        candidate = _round2(answer * factor)
        if candidate <= 0 or candidate == answer or candidate in pool:
            continue
        pool.append(candidate)

    if len(pool) < 3:
        return None
    options = [*pool[:3], answer]
    rng.shuffle(options)
    texts = tuple(labelled(o, unit) for o in options)
    return texts, options.index(answer)


def _build(
    rng: random.Random,
    *,
    category: str,
    difficulty: str,
    pattern: str,
    prompt: str,
    answer: Fraction,
    unit: str,
    explanation: str,
    given: dict[str, Any],
    distractors: Sequence[Fraction] = (),
    circuit: dict[str, Any] | None = None,
    force_numeric: bool = False,
    force_choice: bool = False,
    max_decimals: int = 2,
) -> Question | None:
    """答えがきれいなら Question を作る。そうでなければ None（＝再抽選）。"""
    if not is_clean(answer, max_decimals):
        return None

    base = {
        "category": category,
        "difficulty": difficulty,
        "pattern": pattern,
        "prompt": prompt,
        "answer": answer,
        "unit": unit,
        "explanation": explanation,
        "given": given,
        "circuit": circuit,
    }
    if force_choice or (not force_numeric and rng.random() < 0.5):
        built = _choices(rng, answer, distractors, unit)
        if built is not None:
            texts, index = built
            return Question(**base, kind="choice", choices=texts, answer_index=index)
        if force_choice:  # 4 択にできない組み合わせは再抽選する
            return None
    return Question(**base, kind="numeric")


# --------------------------------------------------------------------------
# 出題パターン：オームの法則の基本
# --------------------------------------------------------------------------
Pattern = Callable[[random.Random, str], "Question | None"]


def _p_ohm_voltage(rng: random.Random, difficulty: str) -> Question | None:
    r = _pick(rng, _RESISTANCES[difficulty])
    i = _pick(rng, _CURRENTS[difficulty])
    v = ohm.voltage(r, i)
    return _build(
        rng,
        category="ohm_basic",
        difficulty=difficulty,
        pattern="ohm_voltage",
        prompt=f"{fmt(r)} Ω の抵抗に {fmt(i)} A の電流が流れています。抵抗の両端の電圧は何 V ですか。",
        answer=v,
        unit="V",
        explanation=_exp_voltage(r, i, v),
        given={"R": r, "I": i},
        distractors=[r / i, i / r, r + i],
    )


def _p_ohm_current(rng: random.Random, difficulty: str) -> Question | None:
    v = _pick(rng, _VOLTAGES[difficulty])
    r = _pick(rng, _RESISTANCES[difficulty])
    i = ohm.current(v, r)
    return _build(
        rng,
        category="ohm_basic",
        difficulty=difficulty,
        pattern="ohm_current",
        prompt=f"{fmt(v)} V の電源に {fmt(r)} Ω の抵抗をつなぎました。流れる電流は何 A ですか。",
        answer=i,
        unit="A",
        explanation=_exp_current(v, r, i),
        given={"V": v, "R": r},
        distractors=[v * r, r / v, v - r if v > r else r - v],
    )


def _p_ohm_resistance(rng: random.Random, difficulty: str) -> Question | None:
    v = _pick(rng, _VOLTAGES[difficulty])
    i = _pick(rng, _CURRENTS[difficulty])
    r = ohm.resistance(v, i)
    return _build(
        rng,
        category="ohm_basic",
        difficulty=difficulty,
        pattern="ohm_resistance",
        prompt=f"{fmt(v)} V を加えると {fmt(i)} A の電流が流れました。この抵抗は何 Ω ですか。",
        answer=r,
        unit="Ω",
        explanation=_exp_resistance(v, i, r),
        given={"V": v, "I": i},
        distractors=[v * i, i / v, v + i],
    )


# --------------------------------------------------------------------------
# 出題パターン：単位の換算（mA・kΩ）
# --------------------------------------------------------------------------
def _p_unit_voltage(rng: random.Random, difficulty: str) -> Question | None:
    r_k = _pick(rng, _KILOHMS[difficulty])
    i_ma = _pick(rng, _MILLIAMPS[difficulty])
    v = r_k * i_ma  # kΩ × mA = V
    return _build(
        rng,
        category="unit_calc",
        difficulty=difficulty,
        pattern="unit_voltage",
        prompt=f"{fmt(r_k)} kΩ の抵抗に {fmt(i_ma)} mA の電流が流れています。電圧は何 V ですか。",
        answer=v,
        unit="V",
        explanation=_exp_unit_voltage(r_k, i_ma, v),
        given={"R_kohm": r_k, "I_mA": i_ma},
        distractors=[r_k * i_ma * 1000, r_k * i_ma / 1000, r_k / i_ma],
    )


def _p_unit_current(rng: random.Random, difficulty: str) -> Question | None:
    v = _pick(rng, _VOLTAGES[difficulty])
    r = _pick(rng, _RESISTANCES[difficulty])
    i_ma = ohm.current(v, r) * 1000
    return _build(
        rng,
        category="unit_calc",
        difficulty=difficulty,
        pattern="unit_current",
        prompt=f"{fmt(v)} V の電源に {fmt(r)} Ω の抵抗をつなぎました。流れる電流は何 mA ですか。",
        answer=i_ma,
        unit="mA",
        explanation=_exp_unit_current(v, r, i_ma),
        given={"V": v, "R": r},
        distractors=[i_ma / 1000, r / v * 1000, v * r],
    )


def _p_unit_resistance(rng: random.Random, difficulty: str) -> Question | None:
    v = _pick(rng, _VOLTAGES[difficulty])
    i_ma = _pick(rng, _MILLIAMPS[difficulty])
    r_k = v / i_ma  # V ÷ mA = kΩ
    return _build(
        rng,
        category="unit_calc",
        difficulty=difficulty,
        pattern="unit_resistance",
        prompt=f"{fmt(v)} V を加えたとき {fmt(i_ma)} mA が流れました。抵抗は何 kΩ ですか。",
        answer=r_k,
        unit="kΩ",
        explanation=_exp_unit_resistance(v, i_ma, r_k),
        given={"V": v, "I_mA": i_ma},
        distractors=[r_k * 1000, i_ma / v, v * i_ma],
    )


# --------------------------------------------------------------------------
# 出題パターン：直列回路
# --------------------------------------------------------------------------
def _series_circuit_data(v: Fraction | None, rs: Sequence[Fraction]) -> dict[str, Any]:
    return {
        "kind": "series",
        "source": None if v is None else f"{fmt(v)} V",
        "resistors": [f"R{n + 1} = {fmt(r)} Ω" for n, r in enumerate(rs)],
    }


def _p_series_total(rng: random.Random, difficulty: str) -> Question | None:
    rs = _pick_resistances(rng, difficulty)
    total = ohm.series_resistance(rs)
    listed = "、".join(f"{fmt(r)} Ω" for r in rs)
    return _build(
        rng,
        category="series",
        difficulty=difficulty,
        pattern="series_total",
        prompt=f"{listed} の抵抗を直列につなぎました。合成抵抗は何 Ω ですか。",
        answer=total,
        unit="Ω",
        explanation=_exp_series_total(rs, total),
        given={"Rs": tuple(rs)},
        distractors=[ohm.parallel_resistance(rs), total / len(rs), min(rs)],
        circuit=_series_circuit_data(None, rs),
    )


def _p_series_current(rng: random.Random, difficulty: str) -> Question | None:
    rs = _pick_resistances(rng, difficulty)
    v = _pick(rng, _VOLTAGES[difficulty])
    circuit = ohm.series_circuit(v, rs)
    listed = "、".join(f"{fmt(r)} Ω" for r in rs)
    return _build(
        rng,
        category="series",
        difficulty=difficulty,
        pattern="series_current",
        prompt=f"{fmt(v)} V の電源に {listed} の抵抗を直列につなぎました。回路に流れる電流は何 A ですか。",
        answer=circuit.current,
        unit="A",
        explanation=_exp_series_current(v, rs, circuit.total_resistance, circuit.current),
        given={"V": v, "Rs": tuple(rs)},
        distractors=[v / rs[0], circuit.total_resistance / v, v * circuit.total_resistance],
        circuit=_series_circuit_data(v, rs),
    )


def _p_series_drop(rng: random.Random, difficulty: str) -> Question | None:
    rs = _pick_resistances(rng, difficulty)
    v = _pick(rng, _VOLTAGES[difficulty])
    circuit = ohm.series_circuit(v, rs)
    index = rng.randrange(len(rs))
    drop = circuit.voltage_drops[index]
    if not is_clean(circuit.current):  # 途中の電流も割り切れる問題だけにする
        return None
    listed = "、".join(f"R{n + 1} = {fmt(r)} Ω" for n, r in enumerate(rs))
    return _build(
        rng,
        category="series",
        difficulty=difficulty,
        pattern="series_drop",
        prompt=(
            f"{fmt(v)} V の電源に {listed} を直列につなぎました。"
            f"R{index + 1}（{fmt(rs[index])} Ω）にかかる電圧は何 V ですか。"
        ),
        answer=drop,
        unit="V",
        explanation=_exp_series_drop(v, rs, circuit.total_resistance, circuit.current, index),
        given={"V": v, "Rs": tuple(rs), "index": index},
        distractors=[v / len(rs), v - drop, rs[index] * v / 100],
        circuit=_series_circuit_data(v, rs),
    )


# --------------------------------------------------------------------------
# 出題パターン：並列回路
# --------------------------------------------------------------------------
def _parallel_circuit_data(v: Fraction | None, rs: Sequence[Fraction]) -> dict[str, Any]:
    return {
        "kind": "parallel",
        "source": None if v is None else f"{fmt(v)} V",
        "resistors": [f"R{n + 1} = {fmt(r)} Ω" for n, r in enumerate(rs)],
    }


def _p_parallel_total(rng: random.Random, difficulty: str) -> Question | None:
    rs = _pick_resistances(rng, difficulty)
    total = ohm.parallel_resistance(rs)
    listed = "、".join(f"{fmt(r)} Ω" for r in rs)
    return _build(
        rng,
        category="parallel",
        difficulty=difficulty,
        pattern="parallel_total",
        prompt=f"{listed} の抵抗を並列につなぎました。合成抵抗は何 Ω ですか。",
        answer=total,
        unit="Ω",
        explanation=_exp_parallel_total(rs, total),
        given={"Rs": tuple(rs)},
        distractors=[ohm.series_resistance(rs), sum(rs, Fraction(0)) / len(rs), min(rs)],
        circuit=_parallel_circuit_data(None, rs),
    )


def _p_parallel_branch(rng: random.Random, difficulty: str) -> Question | None:
    rs = _pick_resistances(rng, difficulty)
    v = _pick(rng, _VOLTAGES[difficulty])
    circuit = ohm.parallel_circuit(v, rs)
    index = rng.randrange(len(rs))
    branch = circuit.branch_currents[index]
    listed = "、".join(f"R{n + 1} = {fmt(r)} Ω" for n, r in enumerate(rs))
    return _build(
        rng,
        category="parallel",
        difficulty=difficulty,
        pattern="parallel_branch",
        prompt=(
            f"{fmt(v)} V の電源に {listed} を並列につなぎました。"
            f"R{index + 1}（{fmt(rs[index])} Ω）に流れる電流は何 A ですか。"
        ),
        answer=branch,
        unit="A",
        explanation=_exp_parallel_branch(v, rs[index], branch, index),
        given={"V": v, "Rs": tuple(rs), "index": index},
        distractors=[circuit.total_current, v / circuit.total_resistance / 10, v * rs[index]],
        circuit=_parallel_circuit_data(v, rs),
    )


def _p_parallel_total_current(rng: random.Random, difficulty: str) -> Question | None:
    rs = _pick_resistances(rng, difficulty)
    v = _pick(rng, _VOLTAGES[difficulty])
    circuit = ohm.parallel_circuit(v, rs)
    if any(not is_clean(i) for i in circuit.branch_currents):
        return None
    listed = "、".join(f"{fmt(r)} Ω" for r in rs)
    return _build(
        rng,
        category="parallel",
        difficulty=difficulty,
        pattern="parallel_total_current",
        prompt=(
            f"{fmt(v)} V の電源に {listed} の抵抗を並列につなぎました。"
            "電源から流れ出る電流は何 A ですか。"
        ),
        answer=circuit.total_current,
        unit="A",
        explanation=_exp_parallel_total_current(v, rs, circuit.branch_currents, circuit.total_current),
        given={"V": v, "Rs": tuple(rs)},
        distractors=[v / ohm.series_resistance(rs), max(circuit.branch_currents), v * len(rs)],
        circuit=_parallel_circuit_data(v, rs),
    )


# --------------------------------------------------------------------------
# 出題パターン：合成抵抗（直並列）
# --------------------------------------------------------------------------
def _p_combined_series_parallel(rng: random.Random, difficulty: str) -> Question | None:
    r1, r2, r3 = _pick_resistances(rng, difficulty, count=3)
    inner = ohm.parallel_resistance([r2, r3])
    total = r1 + inner
    if not is_clean(inner):
        return None
    return _build(
        rng,
        category="combined",
        difficulty=difficulty,
        pattern="combined_series_parallel",
        prompt=(
            f"{fmt(r2)} Ω と {fmt(r3)} Ω を並列にしたものに、{fmt(r1)} Ω を直列につなぎました。"
            "全体の合成抵抗は何 Ω ですか。"
        ),
        answer=total,
        unit="Ω",
        explanation=_exp_combined(
            f"まず並列（分かれ道）の部分をまとめる。1/R = 1/{fmt(r2)} + 1/{fmt(r3)} → {fmt(inner)} Ω",
            f"次に直列（一本道）なので足す。{fmt(r1)} + {fmt(inner)}",
            total,
        ),
        given={"R1": r1, "R2": r2, "R3": r3},
        distractors=[r1 + r2 + r3, ohm.parallel_resistance([r1, r2, r3]), r1 + r2 * r3],
    )


def _p_combined_parallel_series(rng: random.Random, difficulty: str) -> Question | None:
    r1, r2, r3 = _pick_resistances(rng, difficulty, count=3)
    inner = r2 + r3
    total = ohm.parallel_resistance([r1, inner])
    return _build(
        rng,
        category="combined",
        difficulty=difficulty,
        pattern="combined_parallel_series",
        prompt=(
            f"{fmt(r2)} Ω と {fmt(r3)} Ω を直列にしたものに、{fmt(r1)} Ω を並列につなぎました。"
            "全体の合成抵抗は何 Ω ですか。"
        ),
        answer=total,
        unit="Ω",
        explanation=_exp_combined(
            f"まず直列（一本道）の部分を足す。{fmt(r2)} + {fmt(r3)} = {fmt(inner)} Ω",
            f"次に並列（分かれ道）としてまとめる。1/R = 1/{fmt(r1)} + 1/{fmt(inner)}",
            total,
        ),
        given={"R1": r1, "R2": r2, "R3": r3},
        distractors=[
            r1 + inner,
            ohm.parallel_resistance([r1, r2, r3]),
            inner - r1 if inner > r1 else r1 - inner,
        ],
    )


def _p_combined_two_pairs(rng: random.Random, difficulty: str) -> Question | None:
    if difficulty == "easy":
        return None
    r1, r2, r3, r4 = _pick_resistances(rng, difficulty, count=4)
    left = ohm.parallel_resistance([r1, r2])
    right = ohm.parallel_resistance([r3, r4])
    total = left + right
    if not (is_clean(left) and is_clean(right)):
        return None
    return _build(
        rng,
        category="combined",
        difficulty=difficulty,
        pattern="combined_two_pairs",
        prompt=(
            f"{fmt(r1)} Ω と {fmt(r2)} Ω の並列と、{fmt(r3)} Ω と {fmt(r4)} Ω の並列を"
            "直列につなぎました。全体の合成抵抗は何 Ω ですか。"
        ),
        answer=total,
        unit="Ω",
        explanation=_exp_combined(
            f"分かれ道を 1 つずつまとめる。左は {fmt(left)} Ω、右は {fmt(right)} Ω",
            f"まとめた 2 つは一本道でつながっているので足す。{fmt(left)} + {fmt(right)}",
            total,
        ),
        given={"Rs": (r1, r2, r3, r4)},
        distractors=[r1 + r2 + r3 + r4, ohm.parallel_resistance([r1, r2, r3, r4]), left * right],
    )


# --------------------------------------------------------------------------
# 出題パターン：電力・電力量・熱量
# --------------------------------------------------------------------------
_MINUTES = _f("1", "2", "3", "5", "10", "20", "30")
_HOURS = _f("0.5", "1", "1.5", "2", "3", "5", "10")


def _p_power_vi(rng: random.Random, difficulty: str) -> Question | None:
    v = _pick(rng, _VOLTAGES[difficulty])
    i = _pick(rng, _CURRENTS[difficulty])
    p = ohm.power(voltage_v=v, current_a=i)
    return _build(
        rng,
        category="power",
        difficulty=difficulty,
        pattern="power_vi",
        prompt=f"{fmt(v)} V の電圧を加えたとき {fmt(i)} A の電流が流れました。消費電力は何 W ですか。",
        answer=p,
        unit="W",
        explanation=_exp_power_vi(v, i, p),
        given={"V": v, "I": i},
        distractors=[v / i, i / v, v + i],
    )


def _p_power_vr(rng: random.Random, difficulty: str) -> Question | None:
    v = _pick(rng, _VOLTAGES[difficulty])
    r = _pick(rng, _RESISTANCES[difficulty])
    p = ohm.power(voltage_v=v, resistance_ohm=r)
    return _build(
        rng,
        category="power",
        difficulty=difficulty,
        pattern="power_vr",
        prompt=f"{fmt(v)} V の電源に {fmt(r)} Ω の抵抗をつなぎました。消費電力は何 W ですか。",
        answer=p,
        unit="W",
        explanation=_exp_power_vr(v, r, p),
        given={"V": v, "R": r},
        distractors=[v * r, v / r, v * v * r],
    )


def _p_power_energy(rng: random.Random, difficulty: str) -> Question | None:
    p = _pick(rng, _POWERS[difficulty])
    minutes = _pick(rng, _MINUTES)
    seconds = minutes * 60
    joules = ohm.energy_joule(p, seconds)
    return _build(
        rng,
        category="power",
        difficulty=difficulty,
        pattern="power_energy",
        prompt=f"{fmt(p)} W の電熱線を {fmt(minutes)} 分間使いました。発生した熱量は何 J ですか。",
        answer=joules,
        unit="J",
        explanation=_exp_power_energy(p, minutes, seconds, joules),
        given={"P": p, "t_s": seconds},
        distractors=[p * minutes, p / seconds, joules / 60],
    )


def _p_power_kwh(rng: random.Random, difficulty: str) -> Question | None:
    p = _pick(rng, _POWERS[difficulty])
    hours = _pick(rng, _HOURS)
    kwh = ohm.kilowatt_hour(p, hours)
    return _build(
        rng,
        category="power",
        difficulty=difficulty,
        pattern="power_kwh",
        prompt=f"{fmt(p)} W の家電を {fmt(hours)} 時間使いました。消費電力量は何 kWh ですか。",
        answer=kwh,
        unit="kWh",
        explanation=_exp_power_kwh(p, hours, kwh),
        given={"P_W": p, "t_h": hours},
        distractors=[p * hours, kwh / 3600, p / hours / 1000],
    )


def _p_power_heat(rng: random.Random, difficulty: str) -> Question | None:
    v = _pick(rng, _VOLTAGES[difficulty])
    i = _pick(rng, _CURRENTS[difficulty])
    minutes = _pick(rng, _MINUTES)
    seconds = minutes * 60
    p = ohm.power(voltage_v=v, current_a=i)
    joules = ohm.energy_joule(p, seconds)
    return _build(
        rng,
        category="power",
        difficulty=difficulty,
        pattern="power_heat",
        prompt=(
            f"{fmt(v)} V の電源につないだ電熱線に {fmt(i)} A が流れています。"
            f"{fmt(minutes)} 分間で発生する熱量は何 J ですか。"
        ),
        answer=joules,
        unit="J",
        explanation=_exp_power_heat(v, i, p, minutes, seconds, joules),
        given={"V": v, "I": i, "t_s": seconds},
        distractors=[p, p * minutes, joules / 1000],
    )


# --------------------------------------------------------------------------
# 出題パターン：偶数と奇数（小学生向け）
# --------------------------------------------------------------------------
_EVEN_ODD_RANGES: dict[str, tuple[int, int]] = {
    "easy": (10, 99),
    "normal": (100, 999),
    "hard": (1000, 9999),
}

_EVEN_ODD_RULE = (
    "**偶数**は 2 でわり切れる数。一の位が **0・2・4・6・8**\n\n"
    "**奇数**は 2 でわると 1 あまる数。一の位が **1・3・5・7・9**"
)


def _pick_even(rng: random.Random, low: int, high: int) -> int:
    return rng.randrange(low + low % 2, high + 1, 2)


def _pick_odd(rng: random.Random, low: int, high: int) -> int:
    return rng.randrange(low + 1 - low % 2, high + 1, 2)


def _p_even_pick(rng: random.Random, difficulty: str) -> Question | None:
    low, high = _EVEN_ODD_RANGES[difficulty]
    answer = _pick_even(rng, low, high)
    others: list[Fraction] = []
    while len(others) < 3:
        candidate = Fraction(_pick_odd(rng, low, high))
        if candidate not in others:
            others.append(candidate)
    return _build(
        rng,
        category="even_odd",
        difficulty=difficulty,
        pattern="even_pick",
        prompt="つぎの中で「偶数（ぐうすう）」はどれですか。",
        answer=Fraction(answer),
        unit="",
        explanation=_steps(
            _EVEN_ODD_RULE,
            f"{answer} の一の位は **{answer % 10}** → 2 でわり切れるので **偶数**",
            "ほかの数は一の位が 1・3・5・7・9 なので奇数だよ。",
        ),
        given={"answer": Fraction(answer), "kind": "even"},
        distractors=others,
        force_choice=True,
    )


def _p_odd_pick(rng: random.Random, difficulty: str) -> Question | None:
    low, high = _EVEN_ODD_RANGES[difficulty]
    answer = _pick_odd(rng, low, high)
    others: list[Fraction] = []
    while len(others) < 3:
        candidate = Fraction(_pick_even(rng, low, high))
        if candidate not in others:
            others.append(candidate)
    return _build(
        rng,
        category="even_odd",
        difficulty=difficulty,
        pattern="odd_pick",
        prompt="つぎの中で「奇数（きすう）」はどれですか。",
        answer=Fraction(answer),
        unit="",
        explanation=_steps(
            _EVEN_ODD_RULE,
            f"{answer} の一の位は **{answer % 10}** → 2 でわると 1 あまるので **奇数**",
            "ほかの数は一の位が 0・2・4・6・8 なので偶数だよ。",
        ),
        given={"answer": Fraction(answer), "kind": "odd"},
        distractors=others,
        force_choice=True,
    )


def _p_next_even_odd(rng: random.Random, difficulty: str) -> Question | None:
    low, high = _EVEN_ODD_RANGES[difficulty]
    want_even = rng.random() < 0.5
    start = rng.randrange(low, high)
    answer = start + 1
    if answer % 2 != (0 if want_even else 1):
        answer += 1
    word = "偶数" if want_even else "奇数"
    return _build(
        rng,
        category="even_odd",
        difficulty=difficulty,
        pattern="next_even_odd",
        prompt=f"{start} より大きい数のうち、いちばん小さい「{word}」はいくつですか。",
        answer=Fraction(answer),
        unit="",
        explanation=_steps(
            _EVEN_ODD_RULE,
            f"① {start} の次の数から順に見ていく：{start + 1}、{start + 2} …",
            f"② 一の位が {'0・2・4・6・8' if want_even else '1・3・5・7・9'} になる"
            f"いちばん小さい数は **{answer}**",
        ),
        given={"start": Fraction(start), "want_even": Fraction(1 if want_even else 0)},
        distractors=[Fraction(answer + 1), Fraction(answer - 1), Fraction(answer + 2)],
    )


def _p_count_even_odd(rng: random.Random, difficulty: str) -> Question | None:
    width = {"easy": 10, "normal": 20, "hard": 50}[difficulty]
    start = rng.randrange(1, 60)
    end = start + width
    want_even = rng.random() < 0.5
    remainder = 0 if want_even else 1
    numbers = [n for n in range(start, end + 1) if n % 2 == remainder]
    count = len(numbers)
    first, last = numbers[0], numbers[-1]
    word = "偶数" if want_even else "奇数"
    return _build(
        rng,
        category="even_odd",
        difficulty=difficulty,
        pattern="count_even_odd",
        prompt=f"{start} から {end} までの中に「{word}」はいくつありますか。",
        answer=Fraction(count),
        unit="こ",
        explanation=_steps(
            _EVEN_ODD_RULE,
            f"① この中でいちばん小さい{word}は **{first}**、いちばん大きい{word}は **{last}**",
            f"② {word}は 2 とびにならぶので、（{last} − {first}）÷ 2 ＋ 1 で数えられる",
            f"③ （{last - first}）÷ 2 ＋ 1 = **{count} こ**",
        ),
        given={"start": Fraction(start), "end": Fraction(end), "want_even": Fraction(1 if want_even else 0)},
        distractors=[Fraction(count + 1), Fraction(count - 1), Fraction(end - start + 1)],
    )


# --------------------------------------------------------------------------
# 出題パターン：かけ算の筆算（小学生向け）
# --------------------------------------------------------------------------
def _multiplication_walkthrough(a: int, b: int) -> str:
    """1 けたの数をかける筆算を、一の位から順に説明する。"""
    lines: list[str] = []
    carry = 0
    for index, char in enumerate(reversed(str(a))):
        digit = int(char)
        carried_in = carry
        product = digit * b + carried_in
        keep, carry = product % 10, product // 10
        text = f"- {_place_name(index)}：{b} × {digit} = {digit * b}"
        if carried_in:
            text += f"、くり上がりの {carried_in} をたして {product}"
        text += f" → **{keep}** を書く"
        if carry:
            text += f"、{carry} をくり上げる"
        lines.append(text)
    if carry:
        lines.append(f"- 最後にくり上がった **{carry}** をそのまま書く")
    return "\n".join(lines)


_MULT_SMALL: dict[str, tuple[int, int]] = {"easy": (12, 99), "normal": (23, 499), "hard": (123, 999)}
_MULT_ONE_DIGIT: dict[str, tuple[int, ...]] = {
    "easy": (2, 3, 4, 5),
    "normal": (3, 4, 6, 7, 8, 9),
    "hard": (6, 7, 8, 9),
}


def _p_multiply_single(rng: random.Random, difficulty: str) -> Question | None:
    low, high = _MULT_SMALL[difficulty]
    a = rng.randrange(low, high + 1)
    b = rng.choice(_MULT_ONE_DIGIT[difficulty])
    answer = Fraction(a * b)
    return _build(
        rng,
        category="multiplication",
        difficulty=difficulty,
        pattern="multiply_single",
        prompt=f"{a} × {b} を筆算で計算しましょう。答えはいくつですか。",
        answer=answer,
        unit="",
        explanation=_steps(
            f"① {a} × {b} を、一の位から順に計算する。",
            _multiplication_walkthrough(a, b),
            f"② 答えは **{a * b}**",
            "ポイント：くり上がった数は、次の位のかけ算のあとに**たす**よ。",
        ),
        given={"a": Fraction(a), "b": Fraction(b)},
        distractors=[Fraction(a + b), Fraction(a * b + 10), Fraction(a * b) / 10],
    )


def _p_multiply_double(rng: random.Random, difficulty: str) -> Question | None:
    if difficulty == "easy":
        return None
    a = rng.randrange(12, 100)
    b = rng.randrange(12, 100 if difficulty == "hard" else 50)
    ones, tens = b % 10, (b // 10) * 10
    answer = Fraction(a * b)
    return _build(
        rng,
        category="multiplication",
        difficulty=difficulty,
        pattern="multiply_double",
        prompt=f"{a} × {b} を筆算で計算しましょう。答えはいくつですか。",
        answer=answer,
        unit="",
        explanation=_steps(
            f"① まず一の位をかける：{a} × {ones} = **{a * ones}**",
            f"② つぎに十の位をかける：{a} × {tens} = **{a * tens}**（0 を 1 つずらして書く）",
            f"③ 2 つを足す：{a * ones} + {a * tens} = **{a * b}**",
            "ポイント：2 けたのかけ算は、**一の位のかけ算＋十の位のかけ算**に分けると計算できるよ。",
        ),
        given={"a": Fraction(a), "b": Fraction(b)},
        distractors=[Fraction(a * ones), Fraction(a * tens), Fraction(a + b)],
    )


_MULT_DECIMALS: dict[str, tuple[Fraction, ...]] = {
    "easy": _f("0.5", "1.5", "2.5", "0.2", "0.4"),
    "normal": _f("0.3", "0.6", "1.2", "2.5", "3.5", "4.5"),
    "hard": _f("0.15", "0.25", "0.75", "1.25", "2.4", "3.6"),
}


def _p_multiply_decimal(rng: random.Random, difficulty: str) -> Question | None:
    a = rng.choice(_MULT_DECIMALS[difficulty])
    b = Fraction(rng.randrange(2, 10)) if rng.random() < 0.6 else rng.choice(_MULT_DECIMALS[difficulty])
    answer = a * b
    places = _decimal_places(a) + _decimal_places(b)
    whole_a = a * 10 ** _decimal_places(a)
    whole_b = b * 10 ** _decimal_places(b)
    return _build(
        rng,
        category="multiplication",
        difficulty=difficulty,
        pattern="multiply_decimal",
        prompt=f"{fmt(a)} × {fmt(b)} を計算しましょう。答えはいくつですか。",
        answer=answer,
        unit="",
        explanation=_steps(
            f"① 小数点をわすれて、整数どうしでかける：{fmt(whole_a)} × {fmt(whole_b)} = "
            f"**{fmt(whole_a * whole_b)}**",
            f"② 小数点より下のけた数をたす：{fmt(a)} は {_decimal_places(a)} けた、"
            f"{fmt(b)} は {_decimal_places(b)} けた → 合わせて **{places} けた**",
            f"③ 答えの小数点を左に {places} つ動かす：{fmt(whole_a * whole_b)} → **{fmt(answer)}**",
        ),
        given={"a": a, "b": b},
        distractors=[whole_a * whole_b, answer * 10, answer / 10],
    )


# --------------------------------------------------------------------------
# 出題パターン：わり算の筆算（小学生向け）
# --------------------------------------------------------------------------
_PLACE_NAMES: dict[int, str] = {
    4: "一万の位",
    3: "千の位",
    2: "百の位",
    1: "十の位",
    0: "一の位",
    -1: "小数第1位",
    -2: "小数第2位",
    -3: "小数第3位",
}


def _place_name(power: int) -> str:
    return _PLACE_NAMES.get(power, f"10^{power} の位")


def _division_walkthrough(dividend: int, divisor: int, max_decimals: int = 2) -> str:
    """整数どうしのわり算の筆算を、上の位から順に 1 行ずつ説明する。"""
    digits = str(dividend)
    top = len(digits) - 1
    lines: list[str] = []
    remainder = 0
    started = False
    for index, char in enumerate(digits):
        power = top - index
        current = remainder * 10 + int(char)
        quotient, remainder = divmod(current, divisor)
        if quotient == 0 and not started:
            lines.append(f"- {current} に {divisor} は入らない → {_place_name(power)} には書かずに次の位へ")
            continue
        started = True
        lines.append(
            f"- {current} ÷ {divisor} = {quotient} あまり {remainder}"
            f" → {_place_name(power)} に **{quotient}** をたてる"
        )
    if remainder:
        lines.append(f"- あまりが {remainder} なので、小数点をうって 0 をおろす")
    power = -1
    while remainder and power >= -max_decimals:
        current = remainder * 10
        quotient, remainder = divmod(current, divisor)
        lines.append(
            f"- {current} ÷ {divisor} = {quotient} あまり {remainder}"
            f" → {_place_name(power)} に **{quotient}** をたてる"
        )
        power -= 1
    return "\n".join(lines)


_DIVISORS: dict[str, tuple[int, ...]] = {
    "easy": (2, 3, 4, 5, 6),
    "normal": (3, 4, 6, 7, 8, 9, 12),
    "hard": (12, 14, 15, 16, 18, 24, 25, 32),
}
_QUOTIENTS: dict[str, tuple[int, ...]] = {
    "easy": tuple(range(11, 50)),
    "normal": tuple(range(12, 100)),
    "hard": tuple(range(23, 100)),
}


def _p_division_exact(rng: random.Random, difficulty: str) -> Question | None:
    divisor = rng.choice(_DIVISORS[difficulty])
    quotient = rng.choice(_QUOTIENTS[difficulty])
    dividend = divisor * quotient
    answer = Fraction(quotient)
    return _build(
        rng,
        category="division",
        difficulty=difficulty,
        pattern="division_exact",
        prompt=f"{dividend} ÷ {divisor} を筆算で計算しましょう。答えはいくつですか。",
        answer=answer,
        unit="",
        explanation=_steps(
            f"① {dividend} ÷ {divisor} を、上の位から順に計算する。",
            _division_walkthrough(dividend, divisor),
            f"② 答えは **{quotient}**",
            f"たしかめ算：{divisor} × {quotient} = {dividend} なので合っているよ。",
        ),
        given={"a": Fraction(dividend), "b": Fraction(divisor)},
        distractors=[
            Fraction(dividend, divisor * 10),
            Fraction(dividend * 10, divisor),
            Fraction(dividend - divisor),
        ],
    )


def _p_division_decimal(rng: random.Random, difficulty: str) -> Question | None:
    divisor = rng.choice(_DIVISORS[difficulty])
    dividend = rng.randrange(11, 400 if difficulty == "easy" else 900)
    answer = Fraction(dividend, divisor)
    if answer.denominator == 1:  # 割り切れる問題は別パターンにまかせる
        return None
    return _build(
        rng,
        category="division",
        difficulty=difficulty,
        pattern="division_decimal",
        prompt=f"{dividend} ÷ {divisor} を筆算で計算しましょう。答えはいくつですか。",
        answer=answer,
        unit="",
        explanation=_steps(
            f"① {dividend} ÷ {divisor} を、上の位から順に計算する。",
            _division_walkthrough(dividend, divisor),
            f"② 答えは **{fmt(answer)}**",
            "ポイント：わり切れないときは、**小数点をうって 0 をおろす**とつづきが計算できるよ。",
        ),
        given={"a": Fraction(dividend), "b": Fraction(divisor)},
        distractors=[answer * 10, answer / 10, Fraction(dividend // divisor)],
    )


_DECIMAL_DIVISORS: dict[str, tuple[Fraction, ...]] = {
    "easy": _f("0.2", "0.5", "0.4"),
    "normal": _f("0.2", "0.25", "0.3", "0.5", "1.5", "2.5"),
    "hard": _f("0.05", "0.08", "0.12", "0.15", "0.25", "0.75", "1.25", "2.5"),
}


def _p_division_by_decimal(rng: random.Random, difficulty: str) -> Question | None:
    divisor = rng.choice(_DECIMAL_DIVISORS[difficulty])
    dividend = Fraction(rng.randrange(2, 60 if difficulty == "easy" else 200))
    answer = dividend / divisor
    places = _decimal_places(divisor)
    factor = 10 ** places
    return _build(
        rng,
        category="division",
        difficulty=difficulty,
        pattern="division_by_decimal",
        prompt=f"{fmt(dividend)} ÷ {fmt(divisor)} を計算しましょう。答えはいくつですか。",
        answer=answer,
        unit="",
        explanation=_steps(
            f"① わる数 {fmt(divisor)} が小数なので、**わる数とわられる数を同じだけ {factor} 倍**する"
            f"（小数点を右に {places} つ）。{fmt(dividend)} ÷ {fmt(divisor)} → "
            f"**{fmt(dividend * factor)} ÷ {fmt(divisor * factor)}**",
            f"② {fmt(dividend * factor)} ÷ {fmt(divisor * factor)} を筆算する。",
            _division_walkthrough(int(dividend * factor), int(divisor * factor)),
            f"③ 答えは **{fmt(answer)}**",
            "ポイント：同じ数をかけているので、**答えは変わらない**よ。",
        ),
        given={"a": dividend, "b": divisor},
        distractors=[dividend * divisor, answer / 10, answer * 10],
    )


# --------------------------------------------------------------------------
# 出題パターン：小数点の動かし方（小学生向け）
# --------------------------------------------------------------------------
_DECIMAL_VALUES: dict[str, tuple[Fraction, ...]] = {
    "easy": _f("0.5", "0.7", "1.2", "2.5", "3.4", "6", "12"),
    "normal": _f("0.25", "0.08", "1.05", "3.6", "4.75", "12.5", "40"),
    "hard": _f("0.006", "0.045", "0.125", "2.08", "7.25", "36.4", "125"),
}
_TEN_POWERS: dict[str, tuple[int, ...]] = {"easy": (1, 2), "normal": (1, 2, 3), "hard": (2, 3)}


def _p_decimal_multiply(rng: random.Random, difficulty: str) -> Question | None:
    value = rng.choice(_DECIMAL_VALUES[difficulty])
    power = rng.choice(_TEN_POWERS[difficulty])
    times = 10 ** power
    answer = value * times
    return _build(
        rng,
        category="decimal_point",
        difficulty=difficulty,
        pattern="decimal_multiply",
        prompt=f"{fmt(value)} を {times} 倍すると、いくつになりますか。",
        answer=answer,
        unit="",
        explanation=_steps(
            f"① {times} をかけるときは、**小数点を右に {power} つ**動かす。",
            f"② {fmt(value)} → **{fmt(answer)}**",
            "ポイント：けたが足りなくなったら 0 を書きたす（例：0.25 × 1000 → 250）。",
        ),
        given={"v": value, "power": Fraction(power)},
        distractors=[value / times, value * 10 ** (power + 1), value * 10 ** max(power - 1, 0)],
        max_decimals=3,
    )


def _p_decimal_divide(rng: random.Random, difficulty: str) -> Question | None:
    value = rng.choice(_DECIMAL_VALUES[difficulty]) * rng.choice([10, 100, 1000])
    power = rng.choice(_TEN_POWERS[difficulty])
    times = 10 ** power
    answer = value / times
    return _build(
        rng,
        category="decimal_point",
        difficulty=difficulty,
        pattern="decimal_divide",
        prompt=f"{fmt(value)} を {times} でわると、いくつになりますか。",
        answer=answer,
        unit="",
        explanation=_steps(
            f"① {times} でわるときは、**小数点を左に {power} つ**動かす。",
            f"② {fmt(value)} → **{fmt(answer)}**",
            "ポイント：けたが足りなくなったら 0 を書きたす（例：3 ÷ 1000 → 0.003）。",
        ),
        given={"v": value, "power": Fraction(power)},
        distractors=[value * times, value / 10 ** (power + 1), value / 10 ** max(power - 1, 0)],
        max_decimals=3,
    )


def _p_decimal_factor(rng: random.Random, difficulty: str) -> Question | None:
    value = rng.choice(_DECIMAL_VALUES[difficulty])
    power = rng.choice(_TEN_POWERS[difficulty])
    times = 10 ** power
    result = value * times
    return _build(
        rng,
        category="decimal_point",
        difficulty=difficulty,
        pattern="decimal_factor",
        prompt=f"{fmt(value)} を何倍すると {fmt(result)} になりますか。",
        answer=Fraction(times),
        unit="倍",
        explanation=_steps(
            f"① 小数点がどちらへいくつ動いたかを見る。{fmt(value)} → {fmt(result)} は"
            f"**右に {power} つ**動いている。",
            f"② 右に {power} つ動かすのは {times} 倍のとき。答えは **{times} 倍**",
            "ポイント：右に動けばかけ算、左に動けばわり算だよ。",
        ),
        given={"v": value, "result": result},
        distractors=[Fraction(times * 10), Fraction(times // 10 or 1), Fraction(power)],
    )


# --------------------------------------------------------------------------
# 出題パターン：単位の変換（小学生向け）
#
# 換算そのものは tanin.units のデータを使う（表を二重管理しない）。
# --------------------------------------------------------------------------
_UNIT_PAIRS: dict[str, tuple[tuple[str, str], ...]] = {
    "easy": (
        ("cm", "m"),
        ("m", "cm"),
        ("mm", "cm"),
        ("cm", "mm"),
        ("g", "kg"),
        ("kg", "g"),
        ("mL", "L"),
        ("L", "mL"),
    ),
    "normal": (
        ("m", "km"),
        ("km", "m"),
        ("cm", "m"),
        ("m", "cm"),
        ("g", "kg"),
        ("kg", "g"),
        ("kg", "t"),
        ("mL", "L"),
        ("L", "mL"),
        ("cm³", "mL"),
    ),
    "hard": (
        ("mm", "m"),
        ("m", "mm"),
        ("km", "cm"),
        ("g", "t"),
        ("t", "kg"),
        ("mL", "kL"),
        ("cm²", "m²"),
        ("m²", "cm²"),
    ),
}
_UNIT_VALUES: dict[str, tuple[Fraction, ...]] = {
    "easy": _f("2", "3", "5", "8", "10", "20", "50", "100", "200", "500", "1000"),
    "normal": _f("1.5", "2.5", "25", "60", "120", "250", "750", "1200", "2500", "3500"),
    "hard": _f("0.5", "4.5", "45", "125", "480", "1250", "3600", "12500", "45000"),
}


def _p_unit_metric(rng: random.Random, difficulty: str) -> Question | None:
    from_symbol, to_symbol = rng.choice(_UNIT_PAIRS[difficulty])
    value = rng.choice(_UNIT_VALUES[difficulty])
    result = units.convert(value, from_symbol, to_symbol)
    answer = result.value
    src, dst = result.from_unit, result.to_unit
    ratio = src.ratio / dst.ratio
    power = _power_of_ten(ratio)
    if power is None:  # 10 の何倍かで表せない組み合わせは別パターンにまかせる
        return None
    times = 10 ** abs(power)
    if power > 0:
        # 大きい単位 → 小さい単位（例: m → mm）。1 m = 1000 mm
        how = f"**{times} をかける**（小数点を右に {abs(power)} つ）"
        rule = f"1 {from_symbol} = {times} {to_symbol}"
    elif power < 0:
        # 小さい単位 → 大きい単位（例: cm → m）。1 m = 100 cm
        how = f"**{times} でわる**（小数点を左に {abs(power)} つ）"
        rule = f"1 {to_symbol} = {times} {from_symbol}"
    else:
        # 同じ大きさの単位（例: cm³ と mL）
        how = "**数はそのまま**でよい"
        rule = f"1 {from_symbol} = 1 {to_symbol}"
    return _build(
        rng,
        category="unit_convert",
        difficulty=difficulty,
        pattern="unit_metric",
        prompt=f"{fmt(value)} {from_symbol} は何 {to_symbol} ですか。",
        answer=answer,
        unit=to_symbol,
        explanation=_steps(
            f"① おぼえること：{rule}（{from_symbol} ＝ {src.name}、{to_symbol} ＝ {dst.name}）",
            f"② {from_symbol} から {to_symbol} に直すときは {how}",
            f"③ {fmt(value)} → **{fmt(answer)} {to_symbol}**",
            "ポイント：大きい単位に直すと数は小さく、小さい単位に直すと数は大きくなるよ。",
        ),
        given={"value": value, "from": from_symbol, "to": to_symbol},
        distractors=[value / ratio, answer * 10, answer / 10],
    )


_TIME_PAIRS: dict[str, tuple[tuple[str, str], ...]] = {
    "easy": (("min", "s"), ("h", "min")),
    "normal": (("min", "s"), ("s", "min"), ("h", "min"), ("min", "h"), ("d", "h")),
    "hard": (("s", "min"), ("min", "h"), ("h", "s"), ("d", "h"), ("h", "min")),
}
_TIME_LABELS: dict[str, str] = {"s": "秒", "min": "分", "h": "時間", "d": "日"}


def _p_unit_time(rng: random.Random, difficulty: str) -> Question | None:
    from_symbol, to_symbol = rng.choice(_TIME_PAIRS[difficulty])
    value = rng.choice(
        _f("1", "2", "3", "5", "10", "15", "20", "30", "45", "60", "90", "120", "180")
        if difficulty != "easy"
        else _f("1", "2", "3", "5", "10", "15", "20", "30")
    )
    answer = units.convert(value, from_symbol, to_symbol).value
    from_label, to_label = _TIME_LABELS[from_symbol], _TIME_LABELS[to_symbol]
    ratio = units.get_unit(from_symbol).ratio / units.get_unit(to_symbol).ratio
    how = f"**{fmt(ratio)} をかける**" if ratio > 1 else f"**{fmt(1 / ratio)} でわる**"
    return _build(
        rng,
        category="unit_convert",
        difficulty=difficulty,
        pattern="unit_time",
        prompt=f"{fmt(value)} {from_label}は何{to_label}ですか。",
        answer=answer,
        unit=to_label,
        explanation=_steps(
            "① おぼえること：1 分 = 60 秒、1 時間 = 60 分、1 日 = 24 時間",
            f"② {from_label} から {to_label} に直すときは {how}",
            f"③ {fmt(value)} {from_label} → **{fmt(answer)} {to_label}**",
            "ポイント：時間だけは 10 のかたまりではなく **60 のかたまり**。小数点を動かす方法は使えないよ。",
        ),
        given={"value": value, "from": from_symbol, "to": to_symbol},
        distractors=[value * 10, value / 10, answer / 60 if answer > 60 else answer * 60],
    )


_PATTERNS: dict[str, tuple[Pattern, ...]] = {
    "even_odd": (_p_even_pick, _p_odd_pick, _p_next_even_odd, _p_count_even_odd),
    "multiplication": (_p_multiply_single, _p_multiply_double, _p_multiply_decimal),
    "division": (_p_division_exact, _p_division_decimal, _p_division_by_decimal),
    "decimal_point": (_p_decimal_multiply, _p_decimal_divide, _p_decimal_factor),
    "unit_convert": (_p_unit_metric, _p_unit_time),
    "ohm_basic": (_p_ohm_voltage, _p_ohm_current, _p_ohm_resistance),
    "unit_calc": (_p_unit_voltage, _p_unit_current, _p_unit_resistance),
    "series": (_p_series_total, _p_series_current, _p_series_drop),
    "parallel": (_p_parallel_total, _p_parallel_branch, _p_parallel_total_current),
    "combined": (_p_combined_series_parallel, _p_combined_parallel_series, _p_combined_two_pairs),
    "power": (_p_power_vi, _p_power_vr, _p_power_energy, _p_power_kwh, _p_power_heat),
}


# --------------------------------------------------------------------------
# フォールバック（構成上かならずきれいな値になる問題）
# --------------------------------------------------------------------------
def _fallback(rng: random.Random, category: str, difficulty: str) -> Question:
    """どのパターンも 200 回の再抽選で成功しなかったときの保険。

    整数どうしの掛け算だけで作るので、答えは必ず整数になる。
    """
    r = rng.choice([2, 4, 5, 10, 20, 25, 50])
    i = rng.choice([1, 2, 3, 5])
    n = rng.choice([2, 3])
    if category == "even_odd":
        answer = rng.choice([12, 24, 36, 48])
        others = [Fraction(answer + 1), Fraction(answer + 3), Fraction(answer - 1)]
        question = _build(
            rng,
            category=category,
            difficulty=difficulty,
            pattern="even_pick",
            prompt="つぎの中で「偶数（ぐうすう）」はどれですか。",
            answer=Fraction(answer),
            unit="",
            explanation=_steps(
                _EVEN_ODD_RULE,
                f"{answer} の一の位は **{answer % 10}** → 2 でわり切れるので **偶数**",
            ),
            given={"answer": Fraction(answer), "kind": "even"},
            distractors=others,
            force_choice=True,
        )
    elif category == "multiplication":
        a = rng.choice([12, 23, 34, 45])
        b = rng.choice([2, 3, 4])
        question = _build(
            rng,
            category=category,
            difficulty=difficulty,
            pattern="multiply_single",
            prompt=f"{a} × {b} を筆算で計算しましょう。答えはいくつですか。",
            answer=Fraction(a * b),
            unit="",
            explanation=_steps(
                f"① {a} × {b} を、一の位から順に計算する。",
                _multiplication_walkthrough(a, b),
                f"② 答えは **{a * b}**",
            ),
            given={"a": Fraction(a), "b": Fraction(b)},
            distractors=[Fraction(a + b), Fraction(a * b + 10), Fraction(a * b) / 10],
        )
    elif category == "division":
        divisor = rng.choice([2, 3, 4, 5])
        quotient = rng.choice([12, 21, 32, 41])
        dividend = divisor * quotient
        question = _build(
            rng,
            category=category,
            difficulty=difficulty,
            pattern="division_exact",
            prompt=f"{dividend} ÷ {divisor} を筆算で計算しましょう。答えはいくつですか。",
            answer=Fraction(quotient),
            unit="",
            explanation=_steps(
                f"① {dividend} ÷ {divisor} を、上の位から順に計算する。",
                _division_walkthrough(dividend, divisor),
                f"② 答えは **{quotient}**",
                f"たしかめ算：{divisor} × {quotient} = {dividend}",
            ),
            given={"a": Fraction(dividend), "b": Fraction(divisor)},
            distractors=[
                Fraction(dividend, divisor * 10),
                Fraction(dividend * 10, divisor),
                Fraction(dividend - divisor),
            ],
        )
    elif category == "decimal_point":
        value = Fraction(rng.choice([25, 5, 12]), 10)
        power = rng.choice([1, 2, 3])
        times = 10 ** power
        answer = value * times
        question = _build(
            rng,
            category=category,
            difficulty=difficulty,
            pattern="decimal_multiply",
            prompt=f"{fmt(value)} を {times} 倍すると、いくつになりますか。",
            answer=answer,
            unit="",
            explanation=_steps(
                f"① {times} をかけるときは、**小数点を右に {power} つ**動かす。",
                f"② {fmt(value)} → **{fmt(answer)}**",
            ),
            given={"v": value, "power": Fraction(power)},
            distractors=[value / times, value * 10 ** (power + 1), value * 10 ** max(power - 1, 0)],
            max_decimals=3,
        )
    elif category == "unit_convert":
        value = Fraction(rng.choice([200, 300, 500, 1500]))
        answer = units.convert(value, "cm", "m").value
        question = _build(
            rng,
            category=category,
            difficulty=difficulty,
            pattern="unit_metric",
            prompt=f"{fmt(value)} cm は何 m ですか。",
            answer=answer,
            unit="m",
            explanation=_steps(
                "① おぼえること：1 m = 100 cm",
                "② cm から m に直すときは **100 でわる**（小数点を左に 2 つ）",
                f"③ {fmt(value)} → **{fmt(answer)} m**",
            ),
            given={"value": value, "from": "cm", "to": "m"},
            distractors=[value * 100, answer * 10, answer / 10],
        )
    elif category == "series":
        rs = tuple(Fraction(r * (k + 1)) for k in range(n))
        total = ohm.series_resistance(rs)
        question = _build(
            rng,
            category=category,
            difficulty=difficulty,
            pattern="series_total",
            prompt=(
                "、".join(f"{fmt(x)} Ω" for x in rs) + " の抵抗を直列につなぎました。合成抵抗は何 Ω ですか。"
            ),
            answer=total,
            unit="Ω",
            explanation=_exp_series_total(rs, total),
            given={"Rs": rs},
            distractors=[ohm.parallel_resistance(rs), total / len(rs), min(rs)],
            circuit=_series_circuit_data(None, rs),
        )
    elif category == "parallel":
        rs = tuple(Fraction(r * n) for _ in range(n))  # 同じ値どうしの並列 → R/n で必ず割り切れる
        total = ohm.parallel_resistance(rs)
        question = _build(
            rng,
            category=category,
            difficulty=difficulty,
            pattern="parallel_total",
            prompt=(
                "、".join(f"{fmt(x)} Ω" for x in rs) + " の抵抗を並列につなぎました。合成抵抗は何 Ω ですか。"
            ),
            answer=total,
            unit="Ω",
            explanation=_exp_parallel_total(rs, total),
            given={"Rs": rs},
            distractors=[ohm.series_resistance(rs), sum(rs, Fraction(0)) / len(rs), min(rs)],
            circuit=_parallel_circuit_data(None, rs),
        )
    elif category == "combined":
        rs = (Fraction(r), Fraction(r * 2), Fraction(r * 2))
        inner = ohm.parallel_resistance([rs[1], rs[2]])  # 同値の並列 → r
        total = rs[0] + inner
        question = _build(
            rng,
            category=category,
            difficulty=difficulty,
            pattern="combined_series_parallel",
            prompt=(
                f"{fmt(rs[1])} Ω と {fmt(rs[2])} Ω を並列にしたものに、{fmt(rs[0])} Ω を直列につなぎました。"
                "全体の合成抵抗は何 Ω ですか。"
            ),
            answer=total,
            unit="Ω",
            explanation=_exp_combined(
                f"まず並列（分かれ道）をまとめる。1/R = 1/{fmt(rs[1])} + 1/{fmt(rs[2])} → {fmt(inner)} Ω",
                f"次に直列（一本道）なので足す。{fmt(rs[0])} + {fmt(inner)}",
                total,
            ),
            given={"R1": rs[0], "R2": rs[1], "R3": rs[2]},
            distractors=[sum(rs, Fraction(0)), ohm.parallel_resistance(rs), rs[0] * inner],
        )
    elif category == "power":
        v, amp = Fraction(r), Fraction(i)
        p = ohm.power(voltage_v=v, current_a=amp)
        question = _build(
            rng,
            category=category,
            difficulty=difficulty,
            pattern="power_vi",
            prompt=f"{fmt(v)} V の電圧を加えたとき {fmt(amp)} A の電流が流れました。消費電力は何 W ですか。",
            answer=p,
            unit="W",
            explanation=_exp_power_vi(v, amp, p),
            given={"V": v, "I": amp},
            distractors=[v / amp, amp / v, v + amp],
        )
    elif category == "unit_calc":
        r_k, i_ma = Fraction(r), Fraction(i)
        v = r_k * i_ma
        question = _build(
            rng,
            category=category,
            difficulty=difficulty,
            pattern="unit_voltage",
            prompt=f"{fmt(r_k)} kΩ の抵抗に {fmt(i_ma)} mA の電流が流れています。電圧は何 V ですか。",
            answer=v,
            unit="V",
            explanation=_exp_unit_voltage(r_k, i_ma, v),
            given={"R_kohm": r_k, "I_mA": i_ma},
            distractors=[r_k * i_ma * 1000, r_k * i_ma / 1000, r_k / i_ma],
        )
    else:
        rr, ii = Fraction(r), Fraction(i)
        v = ohm.voltage(rr, ii)
        question = _build(
            rng,
            category="ohm_basic",
            difficulty=difficulty,
            pattern="ohm_voltage",
            prompt=f"{fmt(rr)} Ω の抵抗に {fmt(ii)} A の電流が流れています。抵抗の両端の電圧は何 V ですか。",
            answer=v,
            unit="V",
            explanation=_exp_voltage(rr, ii, v),
            given={"R": rr, "I": ii},
            distractors=[rr / ii, ii / rr, rr + ii],
        )
    assert question is not None  # 構成上かならず整数になる
    return question


# --------------------------------------------------------------------------
# 公開 API
# --------------------------------------------------------------------------
def generate_question(
    category: str,
    difficulty: str = "normal",
    rng: random.Random | None = None,
) -> Question:
    """指定カテゴリ・難易度の問題を 1 問生成する。答えは必ずきれいな値になる。"""
    if category not in _PATTERNS:
        raise ValueError(f"未知のカテゴリです: {category!r}")
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"未知の難易度です: {difficulty!r}")
    generator = rng or random.Random()

    patterns = list(_PATTERNS[category])
    generator.shuffle(patterns)
    for pattern in patterns:
        for _ in range(MAX_ATTEMPTS):
            question = pattern(generator, difficulty)
            if question is not None:
                return question
    return _fallback(generator, category, difficulty)


def generate_quiz(
    categories: Sequence[str],
    difficulty: str = "normal",
    count: int = 10,
    rng: random.Random | None = None,
) -> list[Question]:
    """複数カテゴリから ``count`` 問を生成する。"""
    if not categories:
        raise ValueError("カテゴリを 1 つ以上選んでください")
    generator = rng or random.Random()
    order = list(categories)
    questions: list[Question] = []
    while len(questions) < count:
        generator.shuffle(order)
        for category in order:
            if len(questions) >= count:
                break
            questions.append(generate_question(category, difficulty, generator))
    return questions


# --------------------------------------------------------------------------
# 採点
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Grade:
    correct: bool
    your_answer: str
    correct_answer: str
    explanation: str


def grade(question: Question, response: str | int | None) -> Grade:
    """解答を採点する。4 択なら選択肢の番号、数値入力なら文字列を渡す。"""
    if question.kind == "choice":
        index = -1
        if isinstance(response, int):
            index = response
        elif isinstance(response, str) and response in question.choices:
            index = question.choices.index(response)
        your = question.choices[index] if 0 <= index < len(question.choices) else "（未回答）"
        return Grade(
            correct=index == question.answer_index,
            your_answer=your,
            correct_answer=question.choices[question.answer_index],
            explanation=question.explanation,
        )

    text = "" if response is None else str(response)
    value = parse_number(text)
    correct = value is not None and abs(value - question.answer) <= TOLERANCE
    return Grade(
        correct=correct,
        your_answer=f"{text.strip()} {question.unit}" if text.strip() else "（未回答）",
        correct_answer=question.answer_text,
        explanation=question.explanation,
    )
