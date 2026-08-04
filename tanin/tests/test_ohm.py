"""tanin.ohm の検証。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from tanin import ohm
from tanin.ohm import (
    OhmError,
    Parallel,
    Series,
    combined_resistance,
    current,
    energy_joule,
    kilowatt_hour,
    parallel_circuit,
    parallel_resistance,
    power,
    resistance,
    series_circuit,
    series_resistance,
    voltage,
)


# --------------------------------------------------------------------------
# オームの法則
# --------------------------------------------------------------------------
def test_ohms_law_basic() -> None:
    assert voltage(20, 0.3) == Fraction(6)
    assert current(6, 20) == Fraction(3, 10)
    assert resistance(6, 0.3) == Fraction(20)


def test_ohms_law_is_consistent() -> None:
    """V=RI から求めた V を使うと元の I・R に戻る。"""
    r, i = Fraction(47), Fraction(3, 100)
    v = voltage(r, i)
    assert current(v, r) == i
    assert resistance(v, i) == r


def test_float_inputs_are_read_as_decimals() -> None:
    """0.1 は 1/10 として扱う（2 進の丸め誤差を持ち込まない）。"""
    assert ohm.as_fraction(0.1) == Fraction(1, 10)
    assert voltage(30, 0.1) == Fraction(3)


@pytest.mark.parametrize("bad", [0, -5])
def test_non_positive_resistance_raises(bad: int) -> None:
    with pytest.raises(OhmError):
        voltage(bad, 1)
    with pytest.raises(OhmError):
        current(10, bad)


def test_zero_current_resistance_raises() -> None:
    with pytest.raises(OhmError):
        resistance(10, 0)


def test_non_numeric_raises() -> None:
    with pytest.raises(OhmError):
        ohm.as_fraction("10")
    with pytest.raises(OhmError):
        ohm.as_fraction(True)


# --------------------------------------------------------------------------
# 合成抵抗
# --------------------------------------------------------------------------
def test_series_resistance() -> None:
    assert series_resistance([10, 20, 30]) == Fraction(60)


def test_parallel_resistance_two_equal() -> None:
    assert parallel_resistance([10, 10]) == Fraction(5)


def test_parallel_resistance_uses_reciprocal_sum() -> None:
    # 30 Ω と 60 Ω の並列 = 20 Ω
    assert parallel_resistance([30, 60]) == Fraction(20)
    # 1/R = 1/2 + 1/3 + 1/6 = 1 → R = 1
    assert parallel_resistance([2, 3, 6]) == Fraction(1)


def test_parallel_resistance_is_smaller_than_any_branch() -> None:
    values = [Fraction(12), Fraction(15), Fraction(47)]
    assert parallel_resistance(values) < min(values)


def test_empty_resistance_list_raises() -> None:
    with pytest.raises(OhmError):
        series_resistance([])
    with pytest.raises(OhmError):
        parallel_resistance([])


def test_combined_resistance_nested() -> None:
    # 10 Ω と（20 Ω + 30 Ω の直列 = 50 Ω）の並列 = 500/60 Ω
    node = Parallel((Fraction(10), Series((Fraction(20), Fraction(30)))))
    assert combined_resistance(node) == Fraction(25, 3)


def test_combined_resistance_series_of_parallel() -> None:
    # 5 Ω +（20 Ω ∥ 20 Ω = 10 Ω）= 15 Ω
    node = Series((Fraction(5), Parallel((Fraction(20), Fraction(20)))))
    assert combined_resistance(node) == Fraction(15)


def test_combined_resistance_scalar() -> None:
    assert combined_resistance(Fraction(33)) == Fraction(33)


def test_describe_mentions_all_parts() -> None:
    text = ohm.describe(Series((Fraction(5), Parallel((Fraction(20), Fraction(20))))))
    assert "5 Ω" in text
    assert "20 Ω" in text


# --------------------------------------------------------------------------
# 直列回路
# --------------------------------------------------------------------------
def test_series_circuit() -> None:
    circuit = series_circuit(12, [20, 40])
    assert circuit.total_resistance == Fraction(60)
    assert circuit.current == Fraction(1, 5)
    assert circuit.voltage_drops == (Fraction(4), Fraction(8))


def test_series_voltage_drops_sum_to_source() -> None:
    circuit = series_circuit(100, [3, 5, 7, 11])
    assert sum(circuit.voltage_drops) == circuit.voltage_v


def test_series_powers_sum_to_total() -> None:
    circuit = series_circuit(24, [4, 8])
    assert sum(circuit.powers) == circuit.total_power


# --------------------------------------------------------------------------
# 並列回路
# --------------------------------------------------------------------------
def test_parallel_circuit() -> None:
    circuit = parallel_circuit(12, [30, 60])
    assert circuit.branch_currents == (Fraction(2, 5), Fraction(1, 5))
    assert circuit.total_current == Fraction(3, 5)
    assert circuit.total_resistance == Fraction(20)


def test_parallel_total_current_matches_ohms_law() -> None:
    circuit = parallel_circuit(24, [12, 8, 6])
    assert circuit.total_current == current(circuit.voltage_v, circuit.total_resistance)


def test_parallel_powers_sum_to_total() -> None:
    circuit = parallel_circuit(9, [3, 9, 18])
    assert sum(circuit.powers) == circuit.total_power


# --------------------------------------------------------------------------
# 電力・電力量
# --------------------------------------------------------------------------
def test_power_from_any_pair() -> None:
    # V=12, I=0.5, R=24 は同じ回路を表す
    assert power(voltage_v=12, current_a=0.5) == Fraction(6)
    assert power(current_a=0.5, resistance_ohm=24) == Fraction(6)
    assert power(voltage_v=12, resistance_ohm=24) == Fraction(6)


def test_power_requires_two_values() -> None:
    with pytest.raises(OhmError):
        power(voltage_v=12)
    with pytest.raises(OhmError):
        power()


def test_energy_joule() -> None:
    # 500 W を 2 分 → 60000 J
    assert energy_joule(500, 120) == Fraction(60000)


def test_kilowatt_hour() -> None:
    # 1200 W を 3 時間 → 3.6 kWh
    assert kilowatt_hour(1200, 3) == Fraction(18, 5)


def test_kilowatt_hour_matches_joules() -> None:
    # 1 kWh = 3.6 MJ
    assert energy_joule(1000, 3600) == kilowatt_hour(1000, 1) * 3_600_000


def test_negative_time_raises() -> None:
    with pytest.raises(OhmError):
        energy_joule(100, -1)
    with pytest.raises(OhmError):
        kilowatt_hour(100, -1)


def test_fmt_trims_trailing_zeros() -> None:
    assert ohm.fmt(Fraction(3, 2)) == "1.5"
    assert ohm.fmt(Fraction(6)) == "6"
