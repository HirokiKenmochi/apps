"""オームの法則・回路計算ロジック（Streamlit 非依存の純粋 Python モジュール）。

すべての計算は :class:`fractions.Fraction` で厳密に行う。
float を渡した場合は「見た目どおりの 10 進数」として解釈する
（例: ``0.1`` は 1/10。2 進の丸め誤差を持ち込まない）。

公式
----
* オームの法則      : V = R × I,  I = V ÷ R,  R = V ÷ I
* 直列合成抵抗      : R = R1 + R2 + …
* 並列合成抵抗      : 1/R = 1/R1 + 1/R2 + …
* 電力              : P = V × I = I² × R = V² ÷ R
* 電力量・熱量      : W = P × t（J）, kWh = P[W] × t[h] ÷ 1000
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction

from tanin.units import format_value

__all__ = [
    "OhmError",
    "Parallel",
    "ParallelCircuit",
    "Series",
    "SeriesCircuit",
    "as_fraction",
    "combined_resistance",
    "current",
    "describe",
    "energy_joule",
    "fmt",
    "kilowatt_hour",
    "parallel_circuit",
    "parallel_resistance",
    "power",
    "resistance",
    "series_circuit",
    "series_resistance",
    "voltage",
]

Number = int | float | Decimal | Fraction


class OhmError(ValueError):
    """回路計算に渡された値が不正である。"""


def as_fraction(value: Number) -> Fraction:
    """数値を厳密な Fraction に変換する（float は 10 進表記どおりに解釈）。"""
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool):  # bool は int のサブクラスなので先に弾く
        raise OhmError(f"数値ではありません: {value!r}")
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, Decimal):
        try:
            return Fraction(value)
        except (ValueError, InvalidOperation, OverflowError) as exc:
            raise OhmError(f"数値ではありません: {value!r}") from exc
    if isinstance(value, float):
        try:
            return Fraction(Decimal(repr(value)))
        except (ValueError, InvalidOperation, OverflowError) as exc:
            raise OhmError(f"数値ではありません: {value!r}") from exc
    raise OhmError(f"数値ではありません: {value!r}")


def fmt(value: Number, sig_digits: int = 10) -> str:
    """問題文・解説用に数値を読みやすい文字列にする。"""
    text, _ = format_value(as_fraction(value), sig_digits)
    return text


def _positive(value: Number, name: str) -> Fraction:
    frac = as_fraction(value)
    if frac <= 0:
        raise OhmError(f"{name}は正の値である必要があります: {fmt(frac)}")
    return frac


# --------------------------------------------------------------------------
# オームの法則
# --------------------------------------------------------------------------
def voltage(resistance_ohm: Number, current_a: Number) -> Fraction:
    """V = R × I（V）。"""
    return _positive(resistance_ohm, "抵抗") * as_fraction(current_a)


def current(voltage_v: Number, resistance_ohm: Number) -> Fraction:
    """I = V ÷ R（A）。"""
    return as_fraction(voltage_v) / _positive(resistance_ohm, "抵抗")


def resistance(voltage_v: Number, current_a: Number) -> Fraction:
    """R = V ÷ I（Ω）。"""
    amps = as_fraction(current_a)
    if amps == 0:
        raise OhmError("電流が 0 のときは抵抗を求められません")
    return as_fraction(voltage_v) / amps


# --------------------------------------------------------------------------
# 合成抵抗
# --------------------------------------------------------------------------
def _resistance_list(resistances: Iterable[Number]) -> tuple[Fraction, ...]:
    values = tuple(_positive(r, "抵抗") for r in resistances)
    if not values:
        raise OhmError("抵抗が 1 つも指定されていません")
    return values


def series_resistance(resistances: Iterable[Number]) -> Fraction:
    """直列合成抵抗 R = R1 + R2 + …（Ω）。"""
    return sum(_resistance_list(resistances), Fraction(0))


def parallel_resistance(resistances: Iterable[Number]) -> Fraction:
    """並列合成抵抗 1/R = 1/R1 + 1/R2 + …（Ω）。"""
    values = _resistance_list(resistances)
    return 1 / sum((1 / r for r in values), Fraction(0))


@dataclass(frozen=True)
class Series:
    """直列につながれた部分回路。"""

    parts: tuple[Node, ...]


@dataclass(frozen=True)
class Parallel:
    """並列につながれた部分回路。"""

    parts: tuple[Node, ...]


Node = Fraction | int | float | Decimal | Series | Parallel


def combined_resistance(node: Node) -> Fraction:
    """直列・並列・直並列を組み合わせたネットワークの合成抵抗（Ω）。"""
    if isinstance(node, Series):
        return series_resistance(combined_resistance(p) for p in node.parts)
    if isinstance(node, Parallel):
        return parallel_resistance(combined_resistance(p) for p in node.parts)
    return _positive(node, "抵抗")


def describe(node: Node) -> str:
    """ネットワークを日本語の式に書き下す（解説用）。"""
    if isinstance(node, Series):
        return "（" + " + ".join(describe(p) for p in node.parts) + "）の直列"
    if isinstance(node, Parallel):
        return "（" + " ∥ ".join(describe(p) for p in node.parts) + "）の並列"
    return f"{fmt(node)} Ω"


# --------------------------------------------------------------------------
# 直列回路・並列回路
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class SeriesCircuit:
    """電圧 ``voltage_v`` の電源に抵抗を直列接続した回路。"""

    voltage_v: Fraction
    resistances: tuple[Fraction, ...]

    @property
    def total_resistance(self) -> Fraction:
        return series_resistance(self.resistances)

    @property
    def current(self) -> Fraction:
        """回路を流れる電流（どの抵抗でも共通）。"""
        return current(self.voltage_v, self.total_resistance)

    @property
    def voltage_drops(self) -> tuple[Fraction, ...]:
        """各抵抗にかかる電圧。"""
        i = self.current
        return tuple(r * i for r in self.resistances)

    @property
    def powers(self) -> tuple[Fraction, ...]:
        i = self.current
        return tuple(i * i * r for r in self.resistances)

    @property
    def total_power(self) -> Fraction:
        return self.voltage_v * self.current


@dataclass(frozen=True)
class ParallelCircuit:
    """電圧 ``voltage_v`` の電源に抵抗を並列接続した回路。"""

    voltage_v: Fraction
    resistances: tuple[Fraction, ...]

    @property
    def total_resistance(self) -> Fraction:
        return parallel_resistance(self.resistances)

    @property
    def branch_currents(self) -> tuple[Fraction, ...]:
        """各枝を流れる電流（どの枝にも電源電圧がかかる）。"""
        return tuple(current(self.voltage_v, r) for r in self.resistances)

    @property
    def total_current(self) -> Fraction:
        return sum(self.branch_currents, Fraction(0))

    @property
    def powers(self) -> tuple[Fraction, ...]:
        return tuple(self.voltage_v * i for i in self.branch_currents)

    @property
    def total_power(self) -> Fraction:
        return self.voltage_v * self.total_current


def series_circuit(voltage_v: Number, resistances: Sequence[Number]) -> SeriesCircuit:
    return SeriesCircuit(as_fraction(voltage_v), _resistance_list(resistances))


def parallel_circuit(voltage_v: Number, resistances: Sequence[Number]) -> ParallelCircuit:
    return ParallelCircuit(as_fraction(voltage_v), _resistance_list(resistances))


# --------------------------------------------------------------------------
# 電力・電力量
# --------------------------------------------------------------------------
def power(
    *,
    voltage_v: Number | None = None,
    current_a: Number | None = None,
    resistance_ohm: Number | None = None,
) -> Fraction:
    """電力 P（W）。V・I・R のうち 2 つを与える。"""
    if voltage_v is not None and current_a is not None:
        return as_fraction(voltage_v) * as_fraction(current_a)
    if current_a is not None and resistance_ohm is not None:
        i = as_fraction(current_a)
        return i * i * _positive(resistance_ohm, "抵抗")
    if voltage_v is not None and resistance_ohm is not None:
        v = as_fraction(voltage_v)
        return v * v / _positive(resistance_ohm, "抵抗")
    raise OhmError("V・I・R のうち 2 つを指定してください")


def energy_joule(power_w: Number, seconds: Number) -> Fraction:
    """電力量・発熱量 W = P × t（J）。"""
    t = as_fraction(seconds)
    if t < 0:
        raise OhmError("時間は 0 以上である必要があります")
    return as_fraction(power_w) * t


def kilowatt_hour(power_w: Number, hours: Number) -> Fraction:
    """電力量（kWh）。P は W、t は h。"""
    h = as_fraction(hours)
    if h < 0:
        raise OhmError("時間は 0 以上である必要があります")
    return as_fraction(power_w) * h / 1000
