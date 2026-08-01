"""tanin.units の検証（UI を通さずロジックだけをテストする）。"""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

import pytest

from tanin import units
from tanin.units import (
    IncompatibleUnitsError,
    UnknownUnitError,
    convert,
    convert_float,
    format_value,
    parse_number,
)

ALL_UNITS = [
    (q.key, u.symbol) for q in units.list_quantities() for u in q.units
]


# --------------------------------------------------------------------------
# データ構造の健全性
# --------------------------------------------------------------------------
def test_required_quantities_exist() -> None:
    expected = {
        "length",
        "mass",
        "area",
        "volume",
        "time",
        "pressure",
        "force",
        "energy",
        "power",
        "speed",
        "temperature",
    }
    assert expected <= set(units.QUANTITIES)


@pytest.mark.parametrize(
    ("quantity_key", "symbols"),
    [
        ("length", ["nm", "µm", "mm", "cm", "m", "km", "in", "ft", "yd", "mile", "海里", "尺", "間"]),
        ("mass", ["µg", "mg", "g", "kg", "t", "lb", "oz", "貫", "匁"]),
        ("area", ["mm²", "cm²", "m²", "a", "ha", "km²", "坪", "反", "町"]),
        ("volume", ["mm³", "mL", "cm³", "L", "m³", "kL", "米ガロン", "英ガロン", "バレル", "升", "合"]),
        ("time", ["ms", "s", "min", "h", "d"]),
        ("pressure", ["Pa", "hPa", "kPa", "MPa", "bar", "atm", "mmHg", "kgf/cm²", "psi"]),
        ("force", ["N", "kN", "kgf", "dyn"]),
        ("energy", ["J", "kJ", "MJ", "cal", "kcal", "Wh", "kWh", "eV"]),
        ("power", ["W", "kW", "MW", "PS", "HP"]),
        ("speed", ["m/s", "km/h", "ノット", "mph"]),
        ("temperature", ["℃", "K", "℉"]),
    ],
)
def test_required_units_exist(quantity_key: str, symbols: list[str]) -> None:
    available = set(units.get_quantity(quantity_key).symbols)
    assert set(symbols) <= available


def test_base_unit_ratio_is_one() -> None:
    for q in units.list_quantities():
        base = q.base_unit
        assert base.ratio == 1
        if q.key != "temperature":
            assert base.offset == 0


def test_every_unit_has_a_source_note() -> None:
    for q in units.list_quantities():
        for u in q.units:
            assert u.note, f"{q.key}/{u.symbol} に出典コメントがありません"


def test_symbols_are_globally_unique() -> None:
    seen: set[str] = set()
    for _, symbol in ALL_UNITS:
        assert symbol not in seen
        seen.add(symbol)


# --------------------------------------------------------------------------
# 往復変換
# --------------------------------------------------------------------------
@pytest.mark.parametrize(("quantity_key", "symbol"), ALL_UNITS)
def test_round_trip_via_base(quantity_key: str, symbol: str) -> None:
    """A→B→A が元の値に戻る（相対誤差 1e-12 以内）。"""
    quantity = units.get_quantity(quantity_key)
    original = 123.456
    for other in quantity.symbols:
        there = convert_float(original, symbol, other, quantity_key)
        back = convert_float(there, other, symbol, quantity_key)
        assert abs(back - original) / abs(original) < 1e-12


@pytest.mark.parametrize(("quantity_key", "symbol"), ALL_UNITS)
def test_round_trip_is_exact_with_fractions(quantity_key: str, symbol: str) -> None:
    """Fraction 経路では往復変換が厳密に一致する。"""
    quantity = units.get_quantity(quantity_key)
    original = Fraction(123456, 1000)
    for other in quantity.symbols:
        there = convert(original, symbol, other, quantity_key).value
        back = convert(there, other, symbol, quantity_key).value
        assert back == original


# --------------------------------------------------------------------------
# 既知の換算値
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("value", "src", "dst", "expected"),
    [
        # 圧力
        (1, "atm", "hPa", Fraction(101325, 100)),
        (1, "atm", "Pa", Fraction(101325)),
        (1, "bar", "kPa", Fraction(100)),
        (1, "mmHg", "Pa", Fraction(Decimal("133.322387415"))),
        (1, "kgf/cm²", "Pa", Fraction(Decimal("98066.5"))),
        # 長さ
        (1, "in", "cm", Fraction(Decimal("2.54"))),
        (1, "mile", "m", Fraction(1609344, 1000)),
        (1, "海里", "m", Fraction(1852)),
        (1, "尺", "m", Fraction(10, 33)),
        (1, "間", "尺", Fraction(6)),
        # 質量
        (1, "lb", "kg", Fraction(Decimal("0.45359237"))),
        (1, "oz", "lb", Fraction(1, 16)),
        (1, "貫", "kg", Fraction(15, 4)),
        (1000, "匁", "貫", Fraction(1)),
        # 面積
        (1, "坪", "m²", Fraction(400, 121)),
        (1, "反", "坪", Fraction(300)),
        (1, "町", "反", Fraction(10)),
        (1, "ha", "a", Fraction(100)),
        # 体積
        (1, "L", "cm³", Fraction(1000)),
        (1, "升", "L", Fraction(2401, 1331)),
        (1, "升", "合", Fraction(10)),
        (1, "米ガロン", "L", Fraction(Decimal("3.785411784"))),
        (1, "英ガロン", "L", Fraction(Decimal("4.54609"))),
        (1, "バレル", "米ガロン", Fraction(42)),
        (1, "kL", "m³", Fraction(1)),
        # 時間
        (1, "d", "h", Fraction(24)),
        (1, "h", "s", Fraction(3600)),
        # 力・エネルギー・仕事率
        (1, "kgf", "N", Fraction(Decimal("9.80665"))),
        (1, "dyn", "N", Fraction(Decimal("1e-5"))),
        (1, "kcal", "J", Fraction(4184)),
        (1, "kWh", "MJ", Fraction(Decimal("3.6"))),
        (1, "eV", "J", Fraction(Decimal("1.602176634e-19"))),
        (1, "PS", "W", Fraction(Decimal("735.49875"))),
        # 速度
        (36, "km/h", "m/s", Fraction(10)),
        (1, "ノット", "km/h", Fraction(1852, 1000)),
        (1, "mph", "m/s", Fraction(Decimal("0.44704"))),
    ],
)
def test_known_conversions(value: int, src: str, dst: str, expected: Fraction) -> None:
    assert convert(value, src, dst).value == expected


def test_psi_matches_definition() -> None:
    """1 psi = 1 lbf/in²。lbf と in² から独立に組み立てた値と一致する。"""
    lbf = Fraction(Decimal("0.45359237")) * Fraction(Decimal("9.80665"))  # N
    in2 = Fraction(Decimal("0.0254")) ** 2  # m²
    assert convert(1, "psi", "Pa").value == lbf / in2


def test_hp_matches_definition() -> None:
    """1 HP = 550 ft·lbf/s。"""
    lbf = Fraction(Decimal("0.45359237")) * Fraction(Decimal("9.80665"))
    expected = 550 * Fraction(Decimal("0.3048")) * lbf
    assert convert(1, "HP", "W").value == expected


# --------------------------------------------------------------------------
# 温度（オフセット付き換算）
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("value", "src", "dst", "expected"),
    [
        (0, "℃", "K", Fraction(Decimal("273.15"))),
        (0, "℃", "℉", Fraction(32)),
        (100, "℃", "℉", Fraction(212)),
        (100, "℃", "K", Fraction(Decimal("373.15"))),
        (32, "℉", "℃", Fraction(0)),
        (212, "℉", "℃", Fraction(100)),
        (-40, "℃", "℉", Fraction(-40)),
        (0, "K", "℃", Fraction(Decimal("-273.15"))),
        (Fraction(Decimal("440.33")), "℉", "K", Fraction(500)),
    ],
)
def test_temperature_conversions(value: object, src: str, dst: str, expected: Fraction) -> None:
    assert convert(value, src, dst).value == expected


def test_absolute_zero_round_trip() -> None:
    assert convert(0, "K", "℉").value == Fraction(Decimal("-459.67"))


# --------------------------------------------------------------------------
# エラー処理
# --------------------------------------------------------------------------
def test_cross_quantity_conversion_raises() -> None:
    with pytest.raises(IncompatibleUnitsError):
        convert(1, "m", "kg")


def test_cross_quantity_conversion_raises_for_similar_looking_units() -> None:
    with pytest.raises(IncompatibleUnitsError):
        convert(1, "m²", "m³")
    with pytest.raises(IncompatibleUnitsError):
        convert(1, "W", "J")


def test_unknown_unit_raises() -> None:
    with pytest.raises(UnknownUnitError):
        convert(1, "m", "オクテット")
    with pytest.raises(UnknownUnitError):
        units.get_quantity("magnetism")


def test_unit_not_in_specified_quantity_raises() -> None:
    with pytest.raises(UnknownUnitError):
        convert(1, "kg", "m", quantity="length")


# --------------------------------------------------------------------------
# 表示・有効数字・近似記号
# --------------------------------------------------------------------------
def test_format_value_marks_exact_results() -> None:
    text, exact = format_value(convert(1, "atm", "hPa").value, 6)
    assert text == "1013.25"
    assert exact is True


def test_format_value_marks_rounded_results() -> None:
    text, exact = format_value(convert(1, "坪", "m²").value, 6)
    assert text == "3.30579"
    assert exact is False


def test_result_text_uses_approximation_sign() -> None:
    assert convert(1, "atm", "hPa").text(6) == "1013.25"
    assert convert(1, "坪", "m²").text(4).startswith("≈")
    # 逆向きに厳密な値になるケースでは ≈ を付けない
    assert convert(36, "km/h", "m/s").text(6) == "10"


@pytest.mark.parametrize(
    ("sig", "expected"),
    [(3, "3.31"), (4, "3.306"), (6, "3.30579"), (10, "3.305785124")],
)
def test_significant_digits(sig: int, expected: str) -> None:
    text, _ = format_value(convert(1, "坪", "m²").value, sig)
    assert text == expected


def test_format_value_uses_scientific_notation_for_extremes() -> None:
    text, _ = format_value(convert(1, "eV", "J").value, 6)
    assert text == "1.60218e-19"


def test_format_value_zero() -> None:
    assert format_value(Fraction(0), 5) == ("0", True)


def test_exact_flag_reflects_finite_decimal_definition() -> None:
    assert units.get_unit("atm").exact is True
    assert units.get_unit("in").exact is True
    assert units.get_unit("尺").exact is False
    assert units.get_unit("坪").exact is False
    assert units.get_unit("psi").exact is False


# --------------------------------------------------------------------------
# 入力パース
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12", Fraction(12)),
        (" 3.5 ", Fraction(7, 2)),
        ("-0.25", Fraction(-1, 4)),
        ("1,234.5", Fraction(2469, 2)),
        ("１２３", Fraction(123)),
        ("1.5e3", Fraction(1500)),
    ],
)
def test_parse_number(text: str, expected: Fraction) -> None:
    assert parse_number(text) == expected


@pytest.mark.parametrize("text", ["", "  ", "abc", "1.2.3", "１２３円"])
def test_parse_number_rejects_invalid(text: str) -> None:
    assert parse_number(text) is None


# --------------------------------------------------------------------------
# 早見表用データ
# --------------------------------------------------------------------------
def test_si_prefixes() -> None:
    # 従来の 20 種（ヨタ〜ヨクト）＋ 2022 年追加の 4 種
    assert len(units.SI_PREFIXES) == 24
    classic = [p for p in units.SI_PREFIXES if -24 <= p.exponent <= 24]
    assert len(classic) == 20
    assert {p.symbol for p in units.SI_PREFIXES} >= {"k", "M", "G", "m", "µ", "n", "h", "c", "d", "da"}
    assert len({p.exponent for p in units.SI_PREFIXES}) == 24


def test_si_base_units() -> None:
    assert len(units.SI_BASE_UNITS) == 7
    assert {u.symbol for u in units.SI_BASE_UNITS} == {"s", "m", "kg", "A", "K", "mol", "cd"}


def test_si_derived_units() -> None:
    assert len(units.SI_DERIVED_UNITS) == 22
    symbols = {u.symbol for u in units.SI_DERIVED_UNITS}
    assert {"Hz", "N", "Pa", "J", "W", "V", "Ω", "F", "S"} <= symbols
    assert {"T", "H", "lm", "lx", "Bq", "Gy", "Sv", "kat"} <= symbols
    for u in units.SI_DERIVED_UNITS:
        assert u.in_base_units


def test_conversion_rows_are_generated_from_the_converter_data() -> None:
    """換算一覧表は QUANTITIES から自動生成する（表を二重管理しない）。"""
    rows = units.conversion_rows()
    assert len(rows) == sum(len(q.units) for q in units.list_quantities())
    pairs = {(row["量"], row["単位"]) for row in rows}
    assert len(pairs) == len(rows)
    length_rows = {row["単位"]: row for row in rows if row["量"] == "長さ"}
    assert length_rows["海里"]["1 単位あたり"] == "1852 m"
    assert length_rows["尺"]["1 単位あたり"].startswith("≈")
    assert length_rows["尺"]["厳密"] == "丸めた値"


def test_alias_lookup() -> None:
    assert units.get_unit("μm").symbol == "µm"
    assert convert(0, "°C", "K").value == Fraction(Decimal("273.15"))
