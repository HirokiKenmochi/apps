"""UI 共通部品：CSS、スマホ向け数値入力、回路図 SVG、セッション初期化。

配色は一切ハードコードせず、Streamlit のテーマに任せる
（SVG は ``currentColor`` を使うのでライト／ダークどちらでも読める）。
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from tanin.units import parse_number

NUMERIC_PLACEHOLDER_PREFIX = "半角数字"
"""この文字列で始まる placeholder を持つ入力欄を、スマホで数字キーパッドにする。"""

_CSS = """
<style>
/* 画面幅いっぱいまで使い、横スクロールを発生させない */
.block-container {
    max-width: 46rem;
    padding-top: 1.2rem;
    padding-bottom: 4rem;
    padding-left: 0.8rem;
    padding-right: 0.8rem;
    overflow-x: hidden;
}
/* 指で押せるサイズを確保する（44px は Apple HIG の推奨値） */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    min-height: 44px;
    width: 100%;
    font-size: 1rem;
}
.stTextInput input,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"] > div {
    min-height: 44px;
    font-size: 1rem;
}
div[role="radiogroup"] > label {
    min-height: 44px;
    display: flex;
    align-items: center;
    padding: 0.1rem 0;
}
/* タブ（Streamlit 1.60 では data-testid で指定する） */
[data-testid="stTabs"] [role="tablist"] {
    overflow-x: auto;
    gap: 0.15rem;
    scrollbar-width: none;
}
[data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar { display: none; }
[data-testid="stTab"] {
    min-height: 44px;
    padding-left: 0.6rem;
    padding-right: 0.6rem;
    white-space: nowrap;
}
/* タップの青いハイライトを消し、文字の自動拡大も止める（アプリらしい操作感） */
html { -webkit-text-size-adjust: 100%; }
* { -webkit-tap-highlight-color: transparent; }
button, [role="tab"], [role="radiogroup"] label { user-select: none; }

/* ------------------------------------------------------------------ */
/* スマホ幅では、タブを画面下に固定してアプリのタブバーのようにする      */
/* 背景色はテーマから読み取った --tanin-bg を使う（色はハードコードしない）*/
/* ------------------------------------------------------------------ */
@media (max-width: 640px) {
    .block-container {
        padding-top: 0.6rem;
        padding-bottom: 5.5rem;   /* 下タブバーのぶんだけ空ける */
    }
    h1 { font-size: 1.5rem !important; line-height: 1.35 !important; }
    [data-testid="stTabs"] [role="tablist"] {
        position: fixed;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 1000;
        display: flex;
        gap: 0;
        overflow-x: visible;
        background: var(--tanin-bg, #ffffff);
        border-top: 1px solid rgba(128, 128, 128, 0.3);
        box-shadow: 0 -2px 14px rgba(0, 0, 0, 0.08);
        /* iPhone のホームバーに隠れないようにする */
        padding: 0.1rem 0 calc(0.1rem + env(safe-area-inset-bottom, 0px));
    }
    [data-testid="stTab"] {
        flex: 1 1 0;
        justify-content: center;
        padding-left: 0.2rem;
        padding-right: 0.2rem;
        min-height: 48px;
    }
    [data-testid="stTab"] p { font-size: 0.78rem !important; }
}
/* はみ出し防止 */
img, svg, table, pre, code { max-width: 100%; }
[data-testid="stMetricValue"] { font-size: 1.5rem; }
/* 換算結果の大きな表示 */
.tanin-result {
    font-size: 1.75rem;
    font-weight: 700;
    line-height: 1.3;
    word-break: break-word;
}
.tanin-question {
    font-size: 1.1rem;
    line-height: 1.7;
    word-break: break-word;
}
</style>
"""

_KEYPAD_SCRIPT_TEMPLATE = """
<script>
// スマホで数値入力欄に 10 キー（小数点付き）を出す。
// Streamlit の text_input には inputmode を直接指定できないため、
// placeholder を目印に親ドキュメント側の input 要素へ属性を付与する。
const MARK = "__MARK__";
function applyDecimalKeypad() {
    const doc = window.parent.document;
    doc.querySelectorAll('input[type="text"]').forEach(function (el) {
        const ph = el.getAttribute("placeholder") || "";
        if (ph.startsWith(MARK)) {
            el.setAttribute("inputmode", "decimal");
            el.setAttribute("autocomplete", "off");
        }
    });
}
applyDecimalKeypad();
new MutationObserver(applyDecimalKeypad).observe(
    window.parent.document.body, { childList: true, subtree: true }
);

// 下タブバーの背景に使う色を、テーマの背景色から取り出しておく
function syncThemeColor() {
    const doc = window.parent.document;
    const background = getComputedStyle(doc.body).backgroundColor;
    if (background && background !== "rgba(0, 0, 0, 0)") {
        doc.documentElement.style.setProperty("--tanin-bg", background);
    }
    return background;
}
const themeBackground = syncThemeColor();
new MutationObserver(syncThemeColor).observe(
    window.parent.document.documentElement, { attributes: true, attributeFilter: ["class", "style"] }
);

// 「ホーム画面に追加」したときに、ブラウザのバーなしで開けるようにする
function addMeta(doc, name, content) {
    if (!content) return;
    let tag = doc.querySelector('meta[name="' + name + '"]');
    if (!tag) {
        tag = doc.createElement("meta");
        tag.setAttribute("name", name);
        doc.head.appendChild(tag);
    }
    tag.setAttribute("content", content);
}
try {
    // Streamlit Cloud ではアプリが iframe の中なので、いちばん外側の文書を優先する
    const target = (function () {
        try { return window.top.document.head ? window.top.document : window.parent.document; }
        catch (e) { return window.parent.document; }
    })();
    addMeta(target, "apple-mobile-web-app-capable", "yes");
    addMeta(target, "mobile-web-app-capable", "yes");
    addMeta(target, "apple-mobile-web-app-status-bar-style", "default");
    addMeta(target, "apple-mobile-web-app-title", "TanIn");
    addMeta(target, "theme-color", themeBackground);
} catch (e) {
    /* 別ドメインに埋め込まれている場合は何もしない */
}
</script>
"""

_KEYPAD_SCRIPT = _KEYPAD_SCRIPT_TEMPLATE.replace("__MARK__", NUMERIC_PLACEHOLDER_PREFIX)


def inject_css() -> None:
    """最小限のカスタム CSS と、数字キーパッド用のスクリプトを注入する。"""
    st.markdown(_CSS, unsafe_allow_html=True)
    components.html(_KEYPAD_SCRIPT, height=0)


def init_state() -> None:
    """セッション状態の初期値をそろえる（サーバーには何も保存しない）。"""
    defaults: dict[str, Any] = {
        "attempts": [],
        "favorites": [],
        "sig_digits": 6,
        "conv_value": "1",
        "quiz_categories": ["ohm_basic"],
        "quiz_difficulty": "easy",
        "quiz_mode": "practice",
        "current_step": None,
        "quiz_current": None,
        "quiz_grade": None,
        "quiz_serial": 0,
        "quiz_started_at": None,
        "challenge_index": 0,
        "challenge_correct": 0,
        "challenge_started_at": None,
        "challenge_finished": False,
        "challenge_seconds": 0.0,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def numeric_input(
    label: str,
    key: str,
    *,
    default: str = "",
    example: str = "12.5",
    help_text: str | None = None,
    label_visibility: str = "visible",
) -> tuple[str, Fraction | None]:
    """スマホで押しにくい矢印ボタンを避けた数値入力欄。

    ``st.number_input`` ではなく ``st.text_input`` と自前パースを使い、
    placeholder を目印に ``inputmode="decimal"`` を付与する。
    """
    st.session_state.setdefault(key, default)
    text = st.text_input(
        label,
        key=key,
        placeholder=f"{NUMERIC_PLACEHOLDER_PREFIX}（例: {example}）",
        help=help_text,
        label_visibility=label_visibility,
    )
    value = parse_number(text)
    if text.strip() and value is None:
        st.warning("数値として読み取れません。半角数字で入力してください。")
    return text, value


# --------------------------------------------------------------------------
# 回路図（SVG）
# --------------------------------------------------------------------------
_SVG_HEAD = (
    '<div style="width:100%;overflow-x:auto;">'
    '<svg viewBox="0 0 340 {height}" width="100%" height="{height}" '
    'preserveAspectRatio="xMidYMid meet" role="img" aria-label="{alt}" '
    'style="max-width:340px;display:block;margin:0 auto;color:inherit;'
    'stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;">'
)
_SVG_TAIL = "</svg></div>"


def _text(x: float, y: float, content: str, anchor: str = "middle", size: int = 11) -> str:
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
        f'fill="currentColor" stroke="none">{_escape(content)}</text>'
    )


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _line(x1: float, y1: float, x2: float, y2: float) -> str:
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" />'


def _resistor_box(cx: float, cy: float, width: float = 54, height: float = 20) -> str:
    return (
        f'<rect x="{cx - width / 2}" y="{cy - height / 2}" width="{width}" '
        f'height="{height}" rx="3" />'
    )


def _battery(x: float, y: float) -> str:
    """縦線の途中に電池記号（長い極板と短い極板）を描く。"""
    return (
        f'<line x1="{x - 11}" y1="{y - 5}" x2="{x + 11}" y2="{y - 5}" stroke-width="2.5" />'
        f'<line x1="{x - 6}" y1="{y + 4}" x2="{x + 6}" y2="{y + 4}" stroke-width="4" />'
    )


def _series_svg(resistors: list[str], source: str | None) -> str:
    n = max(len(resistors), 1)
    height = 160 if source else 110
    top_y = 52.0
    bottom_y = top_y + 68
    left_x, right_x = 34.0, 306.0
    span = (right_x - left_x) / n
    box_w = min(58.0, span - 10)

    parts: list[str] = []
    cursor = left_x
    for index in range(n):
        cx = left_x + span * (index + 0.5)
        parts.append(_line(cursor, top_y, cx - box_w / 2, top_y))
        parts.append(_resistor_box(cx, top_y, box_w))
        parts.append(_text(cx, top_y - 18, resistors[index] if index < len(resistors) else ""))
        cursor = cx + box_w / 2
    parts.append(_line(cursor, top_y, right_x, top_y))

    if source:
        parts.append(_line(right_x, top_y, right_x, bottom_y))
        parts.append(_line(right_x, bottom_y, left_x, bottom_y))
        mid_y = top_y + (bottom_y - top_y) / 2
        parts.append(_line(left_x, bottom_y, left_x, mid_y + 10))
        parts.append(_line(left_x, top_y, left_x, mid_y - 10))
        parts.append(_battery(left_x, mid_y))
        parts.append(_text(left_x + 4, bottom_y + 24, source, anchor="start"))
    else:
        parts.append(f'<circle cx="{left_x}" cy="{top_y}" r="3" fill="currentColor" />')
        parts.append(f'<circle cx="{right_x}" cy="{top_y}" r="3" fill="currentColor" />')

    alt = "直列回路：" + "、".join(resistors)
    return _SVG_HEAD.format(height=height, alt=_escape(alt)) + "".join(parts) + _SVG_TAIL


def _parallel_svg(resistors: list[str], source: str | None) -> str:
    n = max(len(resistors), 1)
    first_y = 46.0
    gap = 48.0
    last_y = first_y + gap * (n - 1)
    height = last_y + 46
    left_rail = 92.0 if source else 60.0
    right_rail = 300.0
    box_w = 58.0
    cx = (left_rail + right_rail) / 2

    parts: list[str] = [
        _line(left_rail, first_y, left_rail, last_y),
        _line(right_rail, first_y, right_rail, last_y),
    ]
    for index in range(n):
        y = first_y + gap * index
        parts.append(_line(left_rail, y, cx - box_w / 2, y))
        parts.append(_resistor_box(cx, y, box_w))
        parts.append(_line(cx + box_w / 2, y, right_rail, y))
        parts.append(_text(cx, y - 15, resistors[index] if index < len(resistors) else ""))

    if source:
        battery_x = 36.0
        mid_y = (first_y + last_y) / 2
        parts.append(_line(left_rail, first_y, battery_x, first_y))
        parts.append(_line(left_rail, last_y, battery_x, last_y))
        parts.append(_line(battery_x, first_y, battery_x, mid_y - 10))
        parts.append(_line(battery_x, mid_y + 10, battery_x, last_y))
        parts.append(_battery(battery_x, mid_y))
        parts.append(_text(battery_x - 4, last_y + 26, source, anchor="start"))
    else:
        mid_y = (first_y + last_y) / 2
        parts.append(_line(left_rail, mid_y, 30, mid_y))
        parts.append(_line(right_rail, mid_y, 316, mid_y))
        parts.append(f'<circle cx="30" cy="{mid_y}" r="3" fill="currentColor" />')
        parts.append(f'<circle cx="316" cy="{mid_y}" r="3" fill="currentColor" />')

    alt = "並列回路：" + "、".join(resistors)
    return _SVG_HEAD.format(height=height, alt=_escape(alt)) + "".join(parts) + _SVG_TAIL


def _fill_ellipse(cx: float, cy: float, rx: float, ry: float) -> str:
    """「ここをかくす」を表すうすい楕円（色はハードコードしない）。"""
    return (
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" '
        f'fill="currentColor" fill-opacity="0.13" stroke="currentColor" '
        f'stroke-dasharray="5 4" />'
    )


def _arrow_head(x: float, y: float, direction: int = 1, size: float = 7.0) -> str:
    """矢印の先端だけを描く（direction=1 で右向き、-1 で左向き）。"""
    return (
        f'<path d="M{x} {y} l{-direction * size} {-size * 0.6} '
        f'M{x} {y} l{-direction * size} {size * 0.6}" />'
    )


def ohm_triangle_svg(highlight: str | None = None) -> str:
    """オームの法則の三角形。``highlight`` は "V" | "I" | "R"（その文字をかくす）。"""
    parts: list[str] = ['<path d="M170 34 L314 186 L26 186 Z" />']
    if highlight == "V":
        parts.append(_fill_ellipse(170, 84, 34, 28))
    elif highlight == "I":
        parts.append(_fill_ellipse(127, 156, 34, 28))
    elif highlight == "R":
        parts.append(_fill_ellipse(215, 156, 34, 28))
    parts += [
        _line(93, 116, 247, 116),
        _line(170, 116, 170, 186),
        _text(170, 90, "V", size=38),
        _text(170, 108, "でんあつ", size=12),
        _text(127, 162, "I", size=34),
        _text(127, 180, "でんりゅう", size=12),
        _text(215, 162, "R", size=34),
        _text(215, 180, "ていこう", size=12),
        # まわりのミニ説明（三角形の外がわの空いているところに置く）
        _text(58, 44, "たて に ならぶ", size=11),
        _text(58, 62, "→ わり算 ÷", size=13),
        _text(284, 44, "よこ に ならぶ", size=11),
        _text(284, 62, "→ かけ算 ×", size=13),
    ]
    alt = "オームの法則の三角形：上が電圧V、下が電流Iと抵抗R"
    return _SVG_HEAD.format(height=200, alt=_escape(alt)) + "".join(parts) + _SVG_TAIL


def _wavy(x1: float, x2: float, y: float) -> str:
    """水面をあらわす波線。"""
    step = (x2 - x1) / 4
    d = f"M{x1} {y}"
    for k in range(4):
        up = -4 if k % 2 == 0 else 4
        d += f" q{step / 2} {up} {step} 0"
    return f'<path d="{d}" />'


def water_model_svg() -> str:
    """水にたとえた絵：水の高さ＝電圧、流れる水の量＝電流、管のせまさ＝抵抗。"""
    parts: list[str] = [
        # タンク（上はあいている）
        _line(24, 52, 24, 154),
        _line(24, 154, 100, 154),
        _line(100, 52, 100, 128),
        # 水
        '<rect x="25" y="66" width="74" height="88" fill="currentColor" '
        'fill-opacity="0.15" stroke="none" />',
        _wavy(25, 99, 66),
        # 管（とちゅうがせまい＝抵抗）
        '<path d="M100 128 L166 128 L178 136 L214 136 L226 128 L318 128" />',
        '<path d="M100 154 L166 154 L178 146 L214 146 L226 154 L318 154" />',
        # 流れる水（矢印）
        _line(116, 141, 140, 141),
        _arrow_head(140, 141),
        _line(250, 141, 276, 141),
        _arrow_head(276, 141),
        _line(286, 141, 300, 141),
        _arrow_head(300, 141),
        # 水の高さ（電圧）の両矢印
        _line(14, 66, 14, 153),
        _arrow_head(14, 66, -1, 6),
        '<path d="M14 153 l-6 -3.6 M14 153 l6 -3.6" />',
        # ことば
        _text(70, 26, "水の高さ ＝ 電圧", size=13),
        _text(70, 40, "たかいほど いきおいが強い", size=10),
        _text(196, 176, "管がせまい ＝ 抵抗", size=13),
        _text(196, 192, "せまいほど 流れにくい", size=10),
        _text(252, 112, "流れる水の量 ＝ 電流", size=13),
    ]
    alt = "水のたとえ：水の高さが電圧、流れる水の量が電流、管のせまさが抵抗"
    return _SVG_HEAD.format(height=204, alt=_escape(alt)) + "".join(parts) + _SVG_TAIL


def _bulb(cx: float, cy: float, radius: float = 17) -> str:
    """豆電球の絵（光の線つき）。"""
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{radius}" />'
        f'<path d="M{cx - 8} {cy - 4} l4 9 l4 -13 l4 13 l4 -9" />'
        f'<path d="M{cx - 20} {cy - 18} l-6 -6 M{cx} {cy - radius - 5} l0 -7 '
        f'M{cx + 20} {cy - 18} l6 -6" />'
    )


def _battery_box(cx: float, cy: float) -> str:
    """かん電池の絵（＋と−つき）。"""
    return (
        f'<rect x="{cx - 16}" y="{cy - 22}" width="32" height="44" rx="5" />'
        f'<rect x="{cx - 5}" y="{cy - 28}" width="10" height="6" rx="2" />'
        + _text(cx, cy - 4, "＋", size=13)
        + _text(cx, cy + 18, "－", size=13)
    )


def labeled_circuit_svg() -> str:
    """かん電池と豆電球で、どこが電圧・電流・抵抗かを示した絵。"""
    parts: list[str] = [
        # 導線（豆電球のところだけあける）
        _line(52, 62, 183, 62),
        _line(217, 62, 292, 62),
        _line(292, 62, 292, 154),
        _line(292, 154, 52, 154),
        _line(52, 154, 52, 129),
        _line(52, 62, 52, 79),
        _battery_box(52, 107),
        _bulb(200, 62),
        # 電流の向き（ぐるっと一周）
        _line(96, 62, 124, 62),
        _arrow_head(124, 62),
        _line(200, 154, 172, 154),
        _arrow_head(172, 154, -1),
        _line(292, 100, 292, 124),
        _arrow_head(292, 124, 1, 0),
        '<path d="M292 124 l-4.2 -7 M292 124 l4.2 -7" />',
        # ことば
        _text(110, 44, "電流 I（流れる電気）", size=12),
        _text(200, 26, "豆電球 ＝ 抵抗 R", size=13),
        _text(52, 186, "かん電池 ＝ 電圧 V", size=13),
        _text(230, 178, "電流はぐるっと一周する", size=11),
    ]
    alt = "回路の絵：かん電池が電圧、導線を流れるのが電流、豆電球が抵抗"
    return _SVG_HEAD.format(height=198, alt=_escape(alt)) + "".join(parts) + _SVG_TAIL


def relation_bars_svg() -> str:
    """電圧を2倍にすると電流も2倍、抵抗を2倍にすると電流は半分、を棒の長さで見せる絵。"""
    rows = [
        {"v": "3 V", "vn": "", "r": "10 Ω", "rn": "", "len": 62.0, "i": "0.3 A", "note": ""},
        {"v": "6 V", "vn": "2ばい", "r": "10 Ω", "rn": "そのまま", "len": 124.0,
         "i": "0.6 A", "note": "2ばい"},
        {"v": "3 V", "vn": "そのまま", "r": "20 Ω", "rn": "2ばい", "len": 31.0,
         "i": "0.15 A", "note": "はんぶん"},
    ]
    parts: list[str] = [
        _text(42, 20, "電圧", size=12),
        _text(112, 20, "抵抗", size=12),
        _text(215, 20, "電流の大きさ", size=12),
    ]
    for index, row in enumerate(rows):
        y = 56.0 + index * 48
        length = float(row["len"])
        parts += [
            _text(42, y + 2, str(row["v"]), size=14),
            _text(42, y + 18, str(row["vn"]), size=10),
            _text(112, y + 2, str(row["r"]), size=14),
            _text(112, y + 18, str(row["rn"]), size=10),
            f'<rect x="150" y="{y - 10}" width="{length}" height="20" rx="3" '
            f'fill="currentColor" fill-opacity="0.18" />',
            f'<path d="M{150 + length} {y - 10} l12 10 l-12 10 Z" '
            f'fill="currentColor" fill-opacity="0.35" />',
            _text(150 + length + 18, y + 4, str(row["i"]), anchor="start", size=12),
            _text(150 + length + 18, y + 19, str(row["note"]), anchor="start", size=10),
        ]
    alt = "電圧を2倍にすると電流も2倍、抵抗を2倍にすると電流は半分になることを示す棒グラフ"
    return _SVG_HEAD.format(height=210, alt=_escape(alt)) + "".join(parts) + _SVG_TAIL


def render_figure(svg: str) -> None:
    """図（SVG）を表示する。"""
    if svg:
        st.markdown(svg, unsafe_allow_html=True)


def circuit_svg(circuit: dict[str, Any] | None) -> str:
    """問題データから回路図の SVG 文字列を作る。"""
    if not circuit:
        return ""
    resistors = [str(r) for r in (circuit.get("resistors") or [])]
    source = circuit.get("source")
    source = str(source) if source else None
    if circuit.get("kind") == "series":
        return _series_svg(resistors, source)
    if circuit.get("kind") == "parallel":
        return _parallel_svg(resistors, source)
    return ""


def render_circuit(circuit: dict[str, Any] | None) -> None:
    """回路図を表示する。

    ``st.html`` は DOMPurify の HTML プロファイルで SVG 要素ごと除去してしまうため、
    ``st.markdown(unsafe_allow_html=True)`` で埋め込む。
    こうすると ``currentColor`` が効き、ライト／ダークどちらのテーマでも線が見える。
    """
    svg = circuit_svg(circuit)
    if not svg:
        return
    st.markdown(svg, unsafe_allow_html=True)
