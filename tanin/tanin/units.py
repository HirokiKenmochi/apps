"""単位の定義と換算ロジック（Streamlit 非依存の純粋 Python モジュール）。

設計方針
--------
* 各単位は「その単位 1 個あたりの、量ごとの基準単位での値」を係数として持つ。
  換算は ``結果 = 入力値 × 係数(変換元) ÷ 係数(変換先)`` で行う。
* 係数は ``fractions.Fraction`` で厳密に保持する。float の丸めを介さないため、
  往復変換や既知換算値との一致を厳密に検証できる。
* 温度だけは係数方式ではなく、オフセット付きのアフィン変換で扱う
  （基準単位 K に対して ``K = 値 × ratio + offset``）。
* ``Unit.exact`` は「その係数が 10 進の有限小数として厳密に書けるか」を表す。
  例）1 in = 0.0254 m は有限小数なので ``exact=True``。
  1 尺 = 10/33 m は循環小数になるため ``exact=False``（丸めた値でしか表示できない）。
  表示時にはさらに、丸めた結果が厳密値と一致するかを毎回判定し、
  一致しないときだけ "≈" を付ける（:func:`format_value` を参照）。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext
from fractions import Fraction

__all__ = [
    "ConversionResult",
    "IncompatibleUnitsError",
    "Quantity",
    "QUANTITIES",
    "SI_BASE_UNITS",
    "SI_DERIVED_UNITS",
    "SI_PREFIXES",
    "SiBaseUnit",
    "SiDerivedUnit",
    "SiPrefix",
    "Unit",
    "UnitError",
    "UnknownUnitError",
    "convert",
    "convert_float",
    "conversion_rows",
    "find_quantity",
    "format_value",
    "get_quantity",
    "get_unit",
    "list_quantities",
    "parse_number",
]


# --------------------------------------------------------------------------
# 例外
# --------------------------------------------------------------------------
class UnitError(Exception):
    """単位まわりのエラーの基底クラス。"""


class UnknownUnitError(UnitError):
    """未知の単位記号を指定した。"""


class IncompatibleUnitsError(UnitError):
    """異なる量（次元）どうしの換算を要求した。"""


# --------------------------------------------------------------------------
# データ構造
# --------------------------------------------------------------------------
def _d(text: str) -> Fraction:
    """10 進表記の文字列を厳密な Fraction にする。"""
    return Fraction(Decimal(text))


@dataclass(frozen=True)
class Unit:
    """1 つの単位の定義。

    ``基準単位での値 = 入力値 × ratio + offset``
    （温度以外は ``offset == 0``）
    """

    symbol: str
    name: str
    ratio: Fraction
    exact: bool = True
    offset: Fraction = Fraction(0)
    note: str = ""

    @property
    def factor(self) -> float:
        """基準単位での係数（float 版）。"""
        return float(self.ratio)

    def to_base(self, value: Fraction) -> Fraction:
        return value * self.ratio + self.offset

    def from_base(self, base: Fraction) -> Fraction:
        return (base - self.offset) / self.ratio


@dataclass(frozen=True)
class Quantity:
    """量（長さ・質量など）と、その量に属する単位の集合。"""

    key: str
    label: str
    base_symbol: str
    units: tuple[Unit, ...]

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(u.symbol for u in self.units)

    def unit(self, symbol: str) -> Unit:
        for u in self.units:
            if u.symbol == symbol:
                return u
        raise UnknownUnitError(f"{self.label} に単位 {symbol!r} はありません")

    @property
    def base_unit(self) -> Unit:
        return self.unit(self.base_symbol)


@dataclass(frozen=True)
class ConversionResult:
    """換算結果。``value`` は厳密値、``as_float`` は float 版。"""

    value: Fraction
    quantity: Quantity
    from_unit: Unit
    to_unit: Unit

    @property
    def as_float(self) -> float:
        return float(self.value)

    @property
    def units_exact(self) -> bool:
        """変換元・変換先の両方の係数が有限小数で書けるか。"""
        return self.from_unit.exact and self.to_unit.exact

    def text(self, sig_digits: int = 6) -> str:
        """有効数字 ``sig_digits`` 桁の表示文字列（近似なら "≈" 付き）。"""
        body, exact = format_value(self.value, sig_digits)
        return body if exact else f"≈{body}"


# --------------------------------------------------------------------------
# 単位データ
#
# 係数の出典は各行のコメントに記す。
#   SI9   : 国際単位系（SI）第 9 版（2019）日本語版
#   計量法 : 計量法（日本）計量単位令の定義値
#   NIST  : NIST Special Publication 811 (2008) 付録 B
# --------------------------------------------------------------------------

_LENGTH = Quantity(
    key="length",
    label="長さ",
    base_symbol="m",
    units=(
        Unit("nm", "ナノメートル", _d("1e-9"), note="10^-9 m（SI 接頭語）"),
        Unit("µm", "マイクロメートル", _d("1e-6"), note="10^-6 m（SI 接頭語）"),
        Unit("mm", "ミリメートル", _d("1e-3"), note="10^-3 m（SI 接頭語）"),
        Unit("cm", "センチメートル", _d("1e-2"), note="10^-2 m（SI 接頭語）"),
        Unit("m", "メートル", Fraction(1), note="SI 基本単位"),
        Unit("km", "キロメートル", _d("1e3"), note="10^3 m（SI 接頭語）"),
        # 1 in = 0.0254 m（定義値、国際ヤード・ポンド協定 1959／NIST SP811）
        Unit("in", "インチ", _d("0.0254"), note="1 in = 0.0254 m（定義値）"),
        # 1 ft = 12 in = 0.3048 m（定義値、国際ヤード・ポンド協定 1959）
        Unit("ft", "フィート", _d("0.3048"), note="1 ft = 0.3048 m（定義値）"),
        # 1 yd = 3 ft = 0.9144 m（定義値、国際ヤード・ポンド協定 1959）
        Unit("yd", "ヤード", _d("0.9144"), note="1 yd = 0.9144 m（定義値）"),
        # 1 mile = 1760 yd = 1609.344 m（定義値、国際マイル）
        Unit("mile", "マイル", _d("1609.344"), note="1 mile = 1609.344 m（定義値）"),
        # 1 海里 = 1852 m（定義値、国際海里・第1回国際水路会議 1929）
        Unit("海里", "かいり", _d("1852"), note="1 海里 = 1852 m（定義値）"),
        # 1 尺 = 10/33 m（定義値、計量法）→ 循環小数のため exact=False
        Unit("尺", "しゃく", Fraction(10, 33), exact=False, note="1 尺 = 10/33 m（定義値）"),
        # 1 間 = 6 尺 = 20/11 m（定義値、計量法）
        Unit("間", "けん", Fraction(20, 11), exact=False, note="1 間 = 6 尺 = 20/11 m"),
    ),
)

_MASS = Quantity(
    key="mass",
    label="質量",
    base_symbol="kg",
    units=(
        Unit("µg", "マイクログラム", _d("1e-9"), note="10^-9 kg"),
        Unit("mg", "ミリグラム", _d("1e-6"), note="10^-6 kg"),
        Unit("g", "グラム", _d("1e-3"), note="10^-3 kg"),
        Unit("kg", "キログラム", Fraction(1), note="SI 基本単位"),
        # 1 t = 1000 kg（SI 併用単位、SI9 表8）
        Unit("t", "トン", _d("1e3"), note="1 t = 1000 kg（SI 併用単位）"),
        # 1 lb = 0.45359237 kg（定義値、国際ヤード・ポンド協定 1959）
        Unit("lb", "ポンド", _d("0.45359237"), note="1 lb = 0.45359237 kg（定義値）"),
        # 1 oz = 1/16 lb = 0.028349523125 kg（定義値）
        Unit("oz", "オンス", _d("0.028349523125"), note="1 oz = 1/16 lb（定義値）"),
        # 1 貫 = 3.75 kg（定義値、計量法）
        Unit("貫", "かん", _d("3.75"), note="1 貫 = 3.75 kg（定義値）"),
        # 1 匁 = 1/1000 貫 = 3.75 g（定義値、計量法）
        Unit("匁", "もんめ", _d("0.00375"), note="1 匁 = 3.75 g（定義値）"),
    ),
)

_AREA = Quantity(
    key="area",
    label="面積",
    base_symbol="m²",
    units=(
        Unit("mm²", "平方ミリメートル", _d("1e-6"), note="(10^-3 m)^2"),
        Unit("cm²", "平方センチメートル", _d("1e-4"), note="(10^-2 m)^2"),
        Unit("m²", "平方メートル", Fraction(1), note="SI 組立単位"),
        # 1 a = 100 m²（SI 併用単位、SI9 表8）
        Unit("a", "アール", _d("100"), note="1 a = 100 m²（定義値）"),
        # 1 ha = 100 a = 10000 m²（SI 併用単位、SI9 表8）
        Unit("ha", "ヘクタール", _d("10000"), note="1 ha = 10000 m²（定義値）"),
        Unit("km²", "平方キロメートル", _d("1e6"), note="(10^3 m)^2"),
        # 1 坪 = 400/121 m²（定義値、計量法。1 坪 = (20/11 m)^2 = 1 間四方）
        Unit("坪", "つぼ", Fraction(400, 121), exact=False, note="1 坪 = 400/121 m²（定義値）"),
        # 1 反 = 300 坪 = 120000/121 m²（計量法）
        Unit("反", "たん", Fraction(120000, 121), exact=False, note="1 反 = 300 坪"),
        # 1 町 = 10 反 = 3000 坪 = 1200000/121 m²（計量法）
        Unit("町", "ちょう", Fraction(1200000, 121), exact=False, note="1 町 = 3000 坪"),
    ),
)

_VOLUME = Quantity(
    key="volume",
    label="体積",
    base_symbol="m³",
    units=(
        Unit("mm³", "立方ミリメートル", _d("1e-9"), note="(10^-3 m)^3"),
        Unit("mL", "ミリリットル", _d("1e-6"), note="1 mL = 1 cm³（定義値）"),
        Unit("cm³", "立方センチメートル", _d("1e-6"), note="(10^-2 m)^3"),
        # 1 L = 1 dm³ = 10^-3 m³（SI 併用単位、SI9 表8）
        Unit("L", "リットル", _d("1e-3"), note="1 L = 1 dm³（定義値）"),
        Unit("m³", "立方メートル", Fraction(1), note="SI 組立単位"),
        Unit("kL", "キロリットル", Fraction(1), note="1 kL = 1 m³（定義値）"),
        # 1 米ガロン = 231 in³ = 3.785411784 L（定義値、US liquid gallon／NIST SP811）
        Unit("米ガロン", "べいガロン", _d("0.003785411784"), note="1 US gal = 231 in³（定義値）"),
        # 1 英ガロン = 4.54609 L（定義値、英国 Weights and Measures Act 1985）
        Unit("英ガロン", "えいガロン", _d("0.00454609"), note="1 UK gal = 4.54609 L（定義値）"),
        # 1 バレル = 42 米ガロン = 158.987294928 L（石油用バレル、定義値／NIST SP811）
        Unit("バレル", "バレル", _d("0.158987294928"), note="1 bbl = 42 US gal（石油用・定義値）"),
        # 1 升 = 2401/1331 L（定義値、計量法）→ 循環小数のため exact=False
        Unit("升", "しょう", Fraction(2401, 1331) / 1000, exact=False, note="1 升 = 2401/1331 L（定義値）"),
        # 1 合 = 1/10 升（計量法）
        Unit("合", "ごう", Fraction(2401, 1331) / 10000, exact=False, note="1 合 = 1/10 升"),
    ),
)

_TIME = Quantity(
    key="time",
    label="時間",
    base_symbol="s",
    units=(
        Unit("ms", "ミリ秒", _d("1e-3"), note="10^-3 s（SI 接頭語）"),
        Unit("s", "秒", Fraction(1), note="SI 基本単位"),
        # 1 min = 60 s（SI 併用単位、SI9 表8）
        Unit("min", "分", _d("60"), note="1 min = 60 s（定義値）"),
        # 1 h = 3600 s（SI 併用単位、SI9 表8）
        Unit("h", "時", _d("3600"), note="1 h = 3600 s（定義値）"),
        # 1 d = 86400 s（SI 併用単位、SI9 表8）
        Unit("d", "日", _d("86400"), note="1 d = 86400 s（定義値）"),
    ),
)

_PRESSURE = Quantity(
    key="pressure",
    label="圧力",
    base_symbol="Pa",
    units=(
        Unit("Pa", "パスカル", Fraction(1), note="1 Pa = 1 N/m²（SI 組立単位）"),
        Unit("hPa", "ヘクトパスカル", _d("100"), note="10^2 Pa（SI 接頭語）"),
        Unit("kPa", "キロパスカル", _d("1000"), note="10^3 Pa（SI 接頭語）"),
        Unit("MPa", "メガパスカル", _d("1e6"), note="10^6 Pa（SI 接頭語）"),
        # 1 bar = 100000 Pa（定義値、SI9 表9）
        Unit("bar", "バール", _d("1e5"), note="1 bar = 100000 Pa（定義値）"),
        # 1 atm = 101325 Pa（定義値、第10回 CGPM 1954／SI9）
        Unit("atm", "標準大気圧", _d("101325"), note="1 atm = 101325 Pa（定義値）"),
        # 1 mmHg = 133.322387415 Pa（慣用水銀柱ミリメートルの定義値／NIST SP811）
        Unit("mmHg", "水銀柱ミリメートル", _d("133.322387415"), note="1 mmHg = 133.322387415 Pa（定義値）"),
        # 1 kgf/cm² = 98066.5 Pa（1 kgf = 9.80665 N の定義値より）
        Unit(
            "kgf/cm²",
            "重量キログラム毎平方センチメートル",
            _d("98066.5"),
            note="= 9.80665 N / 1 cm²（定義値）",
        ),
        # 1 psi = 1 lbf/in² = 4.4482216152605 N / 0.00064516 m²（定義値。循環小数）
        Unit(
            "psi",
            "重量ポンド毎平方インチ",
            _d("4.4482216152605") / _d("0.00064516"),
            exact=False,
            note="1 psi = 1 lbf/in²（定義値、≈6894.757 Pa）",
        ),
    ),
)

_FORCE = Quantity(
    key="force",
    label="力",
    base_symbol="N",
    units=(
        Unit("N", "ニュートン", Fraction(1), note="1 N = 1 kg·m/s²（SI 組立単位）"),
        Unit("kN", "キロニュートン", _d("1000"), note="10^3 N（SI 接頭語）"),
        # 1 kgf = 9.80665 N（標準重力加速度 g_n = 9.80665 m/s² の定義値、第3回 CGPM 1901）
        Unit("kgf", "重量キログラム", _d("9.80665"), note="1 kgf = 9.80665 N（定義値）"),
        # 1 dyn = 10^-5 N（CGS 単位、定義値／SI9 表9）
        Unit("dyn", "ダイン", _d("1e-5"), note="1 dyn = 10^-5 N（定義値）"),
    ),
)

_ENERGY = Quantity(
    key="energy",
    label="エネルギー",
    base_symbol="J",
    units=(
        Unit("J", "ジュール", Fraction(1), note="1 J = 1 N·m（SI 組立単位）"),
        Unit("kJ", "キロジュール", _d("1000"), note="10^3 J（SI 接頭語）"),
        Unit("MJ", "メガジュール", _d("1e6"), note="10^6 J（SI 接頭語）"),
        # 1 cal = 4.184 J（熱化学カロリーの定義値／NIST SP811）
        Unit("cal", "カロリー", _d("4.184"), note="1 cal = 4.184 J（熱化学カロリー・定義値）"),
        # 1 kcal = 4184 J（熱化学カロリー）
        Unit("kcal", "キロカロリー", _d("4184"), note="1 kcal = 4184 J（熱化学カロリー）"),
        # 1 Wh = 3600 J（1 W × 1 h）
        Unit("Wh", "ワット時", _d("3600"), note="1 Wh = 3600 J（定義値）"),
        # 1 kWh = 3.6 MJ
        Unit("kWh", "キロワット時", _d("3.6e6"), note="1 kWh = 3.6 MJ（定義値）"),
        # 1 eV = 1.602176634e-19 J（電気素量 e の定義値より、SI9 表8）
        Unit("eV", "電子ボルト", _d("1.602176634e-19"), note="1 eV = 1.602176634×10^-19 J（定義値）"),
    ),
)

_POWER = Quantity(
    key="power",
    label="仕事率",
    base_symbol="W",
    units=(
        Unit("W", "ワット", Fraction(1), note="1 W = 1 J/s（SI 組立単位）"),
        Unit("kW", "キロワット", _d("1000"), note="10^3 W（SI 接頭語）"),
        Unit("MW", "メガワット", _d("1e6"), note="10^6 W（SI 接頭語）"),
        # 1 PS = 75 kgf·m/s = 735.49875 W（仏馬力の定義値／NIST SP811）
        Unit("PS", "仏馬力", _d("735.49875"), note="1 PS = 75 kgf·m/s（定義値）"),
        # 1 HP = 550 ft·lbf/s = 745.6998715822702... W（英馬力の定義値。循環小数）
        Unit(
            "HP",
            "英馬力",
            _d("550") * _d("0.3048") * _d("4.4482216152605"),
            exact=False,
            note="1 HP = 550 ft·lbf/s（定義値、≈745.6999 W）",
        ),
    ),
)

_SPEED = Quantity(
    key="speed",
    label="速度",
    base_symbol="m/s",
    units=(
        Unit("m/s", "メートル毎秒", Fraction(1), note="SI 組立単位"),
        # 1 km/h = 1000/3600 m/s = 5/18 m/s（循環小数）
        Unit("km/h", "キロメートル毎時", Fraction(5, 18), exact=False, note="1 km/h = 5/18 m/s（定義値）"),
        # 1 ノット = 1 海里/h = 1852/3600 m/s = 463/900 m/s（循環小数）
        Unit("ノット", "ノット", Fraction(463, 900), exact=False, note="1 kn = 1852 m/h（定義値）"),
        # 1 mph = 1609.344/3600 m/s = 0.44704 m/s（定義値）
        Unit("mph", "マイル毎時", _d("0.44704"), note="1 mph = 0.44704 m/s（定義値）"),
    ),
)

_TEMPERATURE = Quantity(
    key="temperature",
    label="温度",
    base_symbol="K",
    units=(
        Unit("℃", "セルシウス度", Fraction(1), offset=_d("273.15"), note="t/℃ = T/K − 273.15（定義値）"),
        Unit("K", "ケルビン", Fraction(1), note="SI 基本単位"),
        # T/K = (t/℉ + 459.67) × 5/9（定義値）→ offset は循環小数
        Unit(
            "℉",
            "ファーレンハイト度",
            Fraction(5, 9),
            exact=False,
            offset=_d("459.67") * Fraction(5, 9),
            note="t/℉ = t/℃ × 9/5 + 32（定義値）",
        ),
    ),
)

QUANTITIES: dict[str, Quantity] = {
    q.key: q
    for q in (
        _LENGTH,
        _MASS,
        _AREA,
        _VOLUME,
        _TIME,
        _PRESSURE,
        _FORCE,
        _ENERGY,
        _POWER,
        _SPEED,
        _TEMPERATURE,
    )
}


def _build_symbol_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for q in QUANTITIES.values():
        seen: set[str] = set()
        for u in q.units:
            if u.symbol in seen:
                raise AssertionError(f"{q.key} に重複した単位記号 {u.symbol!r}")
            seen.add(u.symbol)
            if u.symbol in index:
                raise AssertionError(f"単位記号 {u.symbol!r} が複数の量で重複しています")
            index[u.symbol] = q.key
    return index


_SYMBOL_TO_QUANTITY: dict[str, str] = _build_symbol_index()

# 入力ゆれの吸収（ギリシャ文字ミューなど）
_ALIASES: dict[str, str] = {
    "μm": "µm",
    "um": "µm",
    "μg": "µg",
    "ug": "µg",
    "C": "℃",
    "°C": "℃",
    "degC": "℃",
    "F": "℉",
    "°F": "℉",
    "degF": "℉",
}


# --------------------------------------------------------------------------
# 参照系 API
# --------------------------------------------------------------------------
def list_quantities() -> tuple[Quantity, ...]:
    """定義済みの量を定義順に返す。"""
    return tuple(QUANTITIES.values())


def get_quantity(key: str) -> Quantity:
    """量のキー（"length" など）または表示名（"長さ"）から Quantity を得る。"""
    if key in QUANTITIES:
        return QUANTITIES[key]
    for q in QUANTITIES.values():
        if q.label == key:
            return q
    raise UnknownUnitError(f"未知の量です: {key!r}")


def _normalize(symbol: str) -> str:
    s = symbol.strip()
    return _ALIASES.get(s, s)


def find_quantity(symbol: str) -> Quantity:
    """単位記号が属する量を返す。"""
    s = _normalize(symbol)
    try:
        return QUANTITIES[_SYMBOL_TO_QUANTITY[s]]
    except KeyError:
        raise UnknownUnitError(f"未知の単位です: {symbol!r}") from None


def get_unit(symbol: str, quantity: str | Quantity | None = None) -> Unit:
    """単位記号から Unit を得る。``quantity`` を指定すると、その量に限定する。"""
    s = _normalize(symbol)
    if quantity is None:
        return find_quantity(s).unit(s)
    q = quantity if isinstance(quantity, Quantity) else get_quantity(quantity)
    return q.unit(s)


# --------------------------------------------------------------------------
# 換算
# --------------------------------------------------------------------------
def _as_fraction(value: float | int | str | Decimal | Fraction) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, str):
        parsed = parse_number(value)
        if parsed is None:
            raise ValueError(f"数値として解釈できません: {value!r}")
        return parsed
    if isinstance(value, Decimal):
        return Fraction(value)
    if isinstance(value, int):
        return Fraction(value)
    return Fraction(value)  # float は 2 進での厳密値として扱う


def convert(
    value: float | int | str | Decimal | Fraction,
    from_unit: str | Unit,
    to_unit: str | Unit,
    quantity: str | Quantity | None = None,
) -> ConversionResult:
    """``value`` を ``from_unit`` から ``to_unit`` に換算する。

    異なる量どうしを指定した場合は :class:`IncompatibleUnitsError` を送出する。
    """
    src_symbol = from_unit.symbol if isinstance(from_unit, Unit) else _normalize(from_unit)
    dst_symbol = to_unit.symbol if isinstance(to_unit, Unit) else _normalize(to_unit)

    if quantity is not None:
        q = quantity if isinstance(quantity, Quantity) else get_quantity(quantity)
        src_q = dst_q = q
        src = q.unit(src_symbol)
        dst = q.unit(dst_symbol)
    else:
        src_q = find_quantity(src_symbol)
        dst_q = find_quantity(dst_symbol)
        src = src_q.unit(src_symbol)
        dst = dst_q.unit(dst_symbol)

    if src_q.key != dst_q.key:
        raise IncompatibleUnitsError(
            f"{src_q.label}の単位 {src.symbol!r} は{dst_q.label}の単位 {dst.symbol!r} に換算できません"
        )

    result = dst.from_base(src.to_base(_as_fraction(value)))
    return ConversionResult(value=result, quantity=src_q, from_unit=src, to_unit=dst)


def convert_float(
    value: float,
    from_unit: str | Unit,
    to_unit: str | Unit,
    quantity: str | Quantity | None = None,
) -> float:
    """:func:`convert` の float 版ショートカット。"""
    return convert(value, from_unit, to_unit, quantity).as_float


# --------------------------------------------------------------------------
# 表示
# --------------------------------------------------------------------------
def _strip_zeros(text: str) -> str:
    if "." not in text:
        return text
    text = text.rstrip("0").rstrip(".")
    return text or "0"


def _plain(dec: Decimal) -> str:
    """指数表記が必要かどうかを判断して読みやすい文字列にする。"""
    adjusted = dec.adjusted()
    if -5 < adjusted < 12:
        return _strip_zeros(format(dec, "f"))
    mantissa, _, exponent = format(dec, "e").partition("e")
    return f"{_strip_zeros(mantissa)}e{int(exponent)}"


def format_value(value: Fraction | float | Decimal, sig_digits: int = 6) -> tuple[str, bool]:
    """有効数字 ``sig_digits`` 桁に丸めた文字列と、それが厳密値かどうかを返す。

    戻り値の 2 番目が False のときは丸めが発生している（表示時に "≈" を付ける）。
    """
    if sig_digits < 1:
        raise ValueError("sig_digits は 1 以上である必要があります")
    frac = _as_fraction(value)
    if frac == 0:
        return "0", True

    with localcontext() as ctx:
        ctx.prec = sig_digits + 15
        dec = Decimal(frac.numerator) / Decimal(frac.denominator)
        quantum = Decimal(1).scaleb(dec.adjusted() - sig_digits + 1)
        try:
            rounded = dec.quantize(quantum, rounding=ROUND_HALF_UP)
        except InvalidOperation:  # pragma: no cover - 桁あふれ時の保険
            rounded = dec
    return _plain(rounded), Fraction(rounded) == frac


# --------------------------------------------------------------------------
# 入力パース（スマホでの手入力を想定）
# --------------------------------------------------------------------------
_FULLWIDTH = str.maketrans(
    "０１２３４５６７８９．－＋ｅＥ",
    "0123456789.-+eE",
)


def parse_number(text: str) -> Fraction | None:
    """ユーザー入力を厳密な Fraction にする。解釈できなければ None。

    全角数字・カンマ区切り・前後の空白を許容する。
    """
    if text is None:
        return None
    cleaned = text.translate(_FULLWIDTH).replace(",", "").replace("_", "").strip()
    if not cleaned:
        return None
    try:
        return Fraction(Decimal(cleaned))
    except (InvalidOperation, ArithmeticError, ValueError):
        return None


# --------------------------------------------------------------------------
# 早見表用データ（SI 第 9 版）
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class SiPrefix:
    """SI 接頭語。"""

    symbol: str
    name: str
    exponent: int

    @property
    def factor_text(self) -> str:
        return f"10^{self.exponent}"


# SI 第 9 版（2019）＋ 第 27 回 CGPM（2022）で追加された 4 語（ロナ・クエタ・ロント・クエクト）
SI_PREFIXES: tuple[SiPrefix, ...] = (
    SiPrefix("Q", "クエタ", 30),
    SiPrefix("R", "ロナ", 27),
    SiPrefix("Y", "ヨタ", 24),
    SiPrefix("Z", "ゼタ", 21),
    SiPrefix("E", "エクサ", 18),
    SiPrefix("P", "ペタ", 15),
    SiPrefix("T", "テラ", 12),
    SiPrefix("G", "ギガ", 9),
    SiPrefix("M", "メガ", 6),
    SiPrefix("k", "キロ", 3),
    SiPrefix("h", "ヘクト", 2),
    SiPrefix("da", "デカ", 1),
    SiPrefix("d", "デシ", -1),
    SiPrefix("c", "センチ", -2),
    SiPrefix("m", "ミリ", -3),
    SiPrefix("µ", "マイクロ", -6),
    SiPrefix("n", "ナノ", -9),
    SiPrefix("p", "ピコ", -12),
    SiPrefix("f", "フェムト", -15),
    SiPrefix("a", "アト", -18),
    SiPrefix("z", "ゼプト", -21),
    SiPrefix("y", "ヨクト", -24),
    SiPrefix("r", "ロント", -27),
    SiPrefix("q", "クエクト", -30),
)


@dataclass(frozen=True)
class SiBaseUnit:
    """SI 基本単位。"""

    symbol: str
    name: str
    quantity: str
    definition: str


SI_BASE_UNITS: tuple[SiBaseUnit, ...] = (
    SiBaseUnit("s", "秒", "時間", "セシウム 133 の超微細構造遷移周波数 ΔνCs = 9192631770 Hz による"),
    SiBaseUnit("m", "メートル", "長さ", "真空中の光速 c = 299792458 m/s による"),
    SiBaseUnit("kg", "キログラム", "質量", "プランク定数 h = 6.62607015×10⁻³⁴ J·s による"),
    SiBaseUnit("A", "アンペア", "電流", "電気素量 e = 1.602176634×10⁻¹⁹ C による"),
    SiBaseUnit("K", "ケルビン", "熱力学温度", "ボルツマン定数 k = 1.380649×10⁻²³ J/K による"),
    SiBaseUnit("mol", "モル", "物質量", "アボガドロ定数 NA = 6.02214076×10²³ mol⁻¹ による"),
    SiBaseUnit("cd", "カンデラ", "光度", "視感効果度 Kcd = 683 lm/W による"),
)


@dataclass(frozen=True)
class SiDerivedUnit:
    """固有の名称と記号をもつ SI 組立単位。"""

    symbol: str
    name: str
    quantity: str
    in_other_si: str
    in_base_units: str


SI_DERIVED_UNITS: tuple[SiDerivedUnit, ...] = (
    SiDerivedUnit("rad", "ラジアン", "平面角", "m/m", "1"),
    SiDerivedUnit("sr", "ステラジアン", "立体角", "m²/m²", "1"),
    SiDerivedUnit("Hz", "ヘルツ", "周波数", "—", "s⁻¹"),
    SiDerivedUnit("N", "ニュートン", "力", "—", "m·kg·s⁻²"),
    SiDerivedUnit("Pa", "パスカル", "圧力・応力", "N/m²", "m⁻¹·kg·s⁻²"),
    SiDerivedUnit("J", "ジュール", "エネルギー・仕事・熱量", "N·m", "m²·kg·s⁻²"),
    SiDerivedUnit("W", "ワット", "仕事率・工率・電力", "J/s", "m²·kg·s⁻³"),
    SiDerivedUnit("C", "クーロン", "電荷", "—", "s·A"),
    SiDerivedUnit("V", "ボルト", "電位差（電圧）・起電力", "W/A", "m²·kg·s⁻³·A⁻¹"),
    SiDerivedUnit("F", "ファラド", "静電容量", "C/V", "m⁻²·kg⁻¹·s⁴·A²"),
    SiDerivedUnit("Ω", "オーム", "電気抵抗", "V/A", "m²·kg·s⁻³·A⁻²"),
    SiDerivedUnit("S", "ジーメンス", "コンダクタンス", "A/V", "m⁻²·kg⁻¹·s³·A²"),
    SiDerivedUnit("Wb", "ウェーバ", "磁束", "V·s", "m²·kg·s⁻²·A⁻¹"),
    SiDerivedUnit("T", "テスラ", "磁束密度", "Wb/m²", "kg·s⁻²·A⁻¹"),
    SiDerivedUnit("H", "ヘンリー", "インダクタンス", "Wb/A", "m²·kg·s⁻²·A⁻²"),
    SiDerivedUnit("℃", "セルシウス度", "セルシウス温度", "—", "K"),
    SiDerivedUnit("lm", "ルーメン", "光束", "cd·sr", "cd"),
    SiDerivedUnit("lx", "ルクス", "照度", "lm/m²", "m⁻²·cd"),
    SiDerivedUnit("Bq", "ベクレル", "放射性核種の放射能", "—", "s⁻¹"),
    SiDerivedUnit("Gy", "グレイ", "吸収線量", "J/kg", "m²·s⁻²"),
    SiDerivedUnit("Sv", "シーベルト", "線量当量", "J/kg", "m²·s⁻²"),
    SiDerivedUnit("kat", "カタール", "触媒活性", "—", "s⁻¹·mol"),
)


def conversion_rows(sig_digits: int = 10) -> list[dict[str, str]]:
    """換算一覧表を :data:`QUANTITIES` から自動生成する（表を二重管理しない）。"""
    rows: list[dict[str, str]] = []
    for quantity in list_quantities():
        base = quantity.base_unit
        for unit in quantity.units:
            if quantity.key == "temperature":
                value = "換算式は下の温度の項を参照"
            else:
                text, exact = format_value(unit.ratio, sig_digits)
                value = f"{'' if exact else '≈'}{text} {base.symbol}"
            rows.append(
                {
                    "量": quantity.label,
                    "単位": unit.symbol,
                    "読み": unit.name,
                    "1 単位あたり": value,
                    "厳密": "定義値" if unit.exact else "丸めた値",
                    "備考": unit.note,
                }
            )
    return rows
