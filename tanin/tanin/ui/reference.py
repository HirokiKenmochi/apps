"""早見表ページ。表は tanin.units のデータから生成し、二重管理しない。"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from tanin import units
from tanin.ui._common import (
    labeled_circuit_svg,
    ohm_triangle_svg,
    relation_bars_svg,
    render_figure,
    water_model_svg,
)

_VIR_ROLES: list[dict[str, str]] = [
    {
        "名前": "電圧",
        "記号": "V",
        "単位": "V（ボルト）",
        "水にたとえると": "水面の高さ（おし出す力）",
        "大きくすると": "電流がふえる",
    },
    {
        "名前": "電流",
        "記号": "I",
        "単位": "A（アンペア）",
        "水にたとえると": "流れる水の量",
        "大きくすると": "（電圧と抵抗で決まる）",
    },
    {
        "名前": "抵抗",
        "記号": "R",
        "単位": "Ω（オーム）",
        "水にたとえると": "管のせまさ（通りにくさ）",
        "大きくすると": "電流がへる",
    },
]

_VIR_INTRO = """
電気は目に見えないので、**水の流れ**にたとえるとイメージしやすいよ。
"""

_VIR_WATER = """
- **電圧（V）**… 水を「おし出す力」。水面が高いほど、いきおいよく流れる
- **電流（I）**… じっさいに「流れる水の量」。1 秒あたりどれだけ流れたか
- **抵抗（R）**… 管の「せまさ」。せまいほど水（電気）は流れにくい

つまり **電圧が大きいほど電流はふえて、抵抗が大きいほど電流はへる**。
これを式にしたのがオームの法則だよ。
"""

_VIR_CIRCUIT = """
本もののかいろでは、**かん電池が電圧**、導線を流れているのが **電流**、
**豆電球が抵抗**（電気の通りにくさ）だよ。電流は電池から出て、ぐるっと一周してもどってくる。
"""

_VIR_RELATION = """
#### くらべてみよう

同じかいろで、**電圧だけ 2 ばい**にしたときと、**抵抗だけ 2 ばい**にしたときのちがい。
ぼうの長さが電流の大きさだよ。
"""

_VIR_RELATION_AFTER = """
- **電圧を 2 ばい** にすると、電流も **2 ばい**（水をおし出す力が強くなるから）
- **抵抗を 2 ばい** にすると、電流は **はんぶん**（管がせまくなって通りにくいから）
"""

_VIR_TRIANGLE = """
#### オームの法則の三角形（かくすと式が出てくる）

- **V をかくす** → のこりは `I` と `R` が**横ならび**　→ **V = I × R**
- **I をかくす** → `V` が上で `R` が下 → **I = V ÷ R**
- **R をかくす** → `V` が上で `I` が下 → **R = V ÷ I**

**よこに ならんだら かけ算、たて に ならんだら わり算。** これだけ覚えれば 3 つの式は全部作れる。
"""

_FORMULAS: list[dict[str, str]] = [
    {"分類": "オームの法則", "公式": "V = R × I", "意味": "電圧は、抵抗と電流をかけ算するだけ"},
    {"分類": "オームの法則", "公式": "I = V ÷ R", "意味": "電流は、電圧を抵抗でわり算するだけ"},
    {"分類": "オームの法則", "公式": "R = V ÷ I", "意味": "抵抗は、電圧を電流でわり算するだけ"},
    {
        "分類": "直列回路",
        "公式": "R = R₁ + R₂ + …",
        "意味": "一本道のつなぎ方。抵抗は足すだけで、どれよりも大きくなる",
    },
    {
        "分類": "直列回路",
        "公式": "I が共通",
        "意味": "一本道だから電流はどこでも同じ。抵抗が大きいところほど電圧を多く使う",
    },
    {"分類": "直列回路", "公式": "V = V₁ + V₂ + …", "意味": "それぞれの電圧をぜんぶ足すと、電池の電圧になる"},
    {
        "分類": "並列回路",
        "公式": "1/R = 1/R₁ + 1/R₂ + …",
        "意味": "分かれ道のつなぎ方。逆数を足してから1でわる。どれよりも小さくなる",
    },
    {"分類": "並列回路", "公式": "V が共通", "意味": "どの道にも、電池と同じ電圧がかかる"},
    {"分類": "並列回路", "公式": "I = I₁ + I₂ + …", "意味": "道ごとの電流を足すと、電池から出る電流になる"},
    {"分類": "並列回路", "公式": "R = R₁R₂ ÷ (R₁ + R₂)", "意味": "2本のときの近道：かけ算 ÷ 足し算"},
    {
        "分類": "電力",
        "公式": "P = V × I = I²R = V² ÷ R",
        "意味": "1秒でどれだけ電気を使うか。W（ワット）",
    },
    {
        "分類": "電力量・熱量",
        "公式": "W = P × t",
        "意味": "時間は「秒」に直してからかける。答えは J（ジュール）",
    },
    {
        "分類": "電力量",
        "公式": "kWh = P[kW] × t[h]",
        "意味": "電気代の計算に使う。W は 1000 でわって kW にしてからかける",
    },
    {
        "分類": "単位の換算",
        "公式": "kΩ × mA = V",
        "意味": "1000倍と1000分の1で打ち消し合うので、そのままかけてよい",
    },
    {"分類": "単位の換算", "公式": "V ÷ kΩ = mA", "意味": "上の式をひっくり返しただけ"},
]


# 小学生向けの計算の教え方。表（検索でしぼり込める）と本文に分けて持つ。
_DECIMAL_SHIFT: list[dict[str, str]] = [
    {"計算": "× 10", "小数点の動き": "右に 1 つ", "例": "0.25 → 2.5", "単位の例": "cm → mm"},
    {"計算": "× 100", "小数点の動き": "右に 2 つ", "例": "0.25 → 25", "単位の例": "m → cm"},
    {"計算": "× 1000", "小数点の動き": "右に 3 つ", "例": "0.25 → 250", "単位の例": "A → mA、kΩ → Ω"},
    {"計算": "÷ 10", "小数点の動き": "左に 1 つ", "例": "25 → 2.5", "単位の例": "mm → cm"},
    {"計算": "÷ 100", "小数点の動き": "左に 2 つ", "例": "25 → 0.25", "単位の例": "cm → m"},
    {"計算": "÷ 1000", "小数点の動き": "左に 3 つ", "例": "25 → 0.025", "単位の例": "mA → A、W → kW"},
]

_MULTIPLICATION = """
#### ① かけ算の筆算（1 けたをかける）

「248 × 8」をやってみよう。**位をそろえて、一の位から**計算する。

```text
    248
  ×   8
  -----
   1984
```

1. **一の位**　8 × 8 = 64 → 一の位に **4** を書き、**6 をくり上げる**
2. **十の位**　8 × 4 = 32、くり上がりの 6 をたして 38 → **8** を書き、**3 をくり上げる**
3. **百の位**　8 × 2 = 16、くり上がりの 3 をたして 19 → **9** を書き、**1 をくり上げる**
4. 最後にくり上がった **1** をそのまま書く → 答えは **1984**

くり上がりは、**かけ算をしたあとにたす**のがポイント。

#### ② かけ算の筆算（2 けたをかける）

「38 × 24」は、**一の位のかけ算と十の位のかけ算に分けて**、あとで足す。

```text
     38
  ×  24
  -----
    152
   76
  -----
    912
```

1. **一の位**　38 × 4 = **152**
2. **十の位**　38 × 2 = **76**。2 は十の位なので、**1 つ左にずらして**書く（本当は 38 × 20 = 760）
3. **たす**　152 + 760 = **912**

「1 つ左にずらす」＝「0 を 1 つつける」と同じこと。

#### ③ 小数のかけ算

「2.5 × 0.4」のように小数があっても、**まず小数点をわすれて**整数のかけ算をする。

1. 小数点をわすれて計算：`25 × 4 = 100`
2. 小数点より下のけた数をたす：2.5 は 1 けた、0.4 は 1 けた → 合わせて **2 けた**
3. 答えの小数点を**左に 2 つ**動かす：`100` → **1**

たし算とちがって、**かけ算は小数点をそろえなくてよい**（最後に動かすだけ）。
"""


_LONG_DIVISION = """
#### ④ わり算の筆算（ひっさん）のやり方

「12 ÷ 30」をやってみよう。**わられる数（12）が小さくても大丈夫**。

```text
      0.4
     -----
30 ) 12.0
     12.0
     -----
        0
```

1. **たてる**　「30 は 12 の中に入る？」→ 入らないので、一の位に **0** を書き、そのすぐ右に**小数点をうつ**
2. **おろす**　12 を「12.0」とみて 0 をおろす → **120**
3. **たてる**　「30 × 4 = 120」だから、小数第 1 位に **4** をたてる
4. **かける・ひく**　120 − 120 = **0**。あまりが 0 になったのでおわり → 答えは **0.4**

あまりが残ったら、また 0 をおろしてつづきを計算する。
（このアプリの問題は、かならず小数第 2 位までで**わりきれる**ように作ってあるよ）

#### ⑤ わる数が小数のとき ＝ 小数点の位を上げる

「6 ÷ 0.3」のように**わる数が小数**のときは、そのままでは筆算できない。
そこで、**わる数とわられる数を同じだけ 10 倍**して、わる数を整数にしてから筆算する。

1. `6 ÷ 0.3` … わる数が小数なので、このままでは筆算できない
2. どちらも 10 倍する（小数点を右に 1 つ）→ `60 ÷ 3`
3. 筆算して答えは **20**

**わる数の小数点を動かした数だけ、わられる数の小数点も同じ数だけ動かす。**
どちらも同じ数をかけているので、**答えは変わらない**。

- わる数が 0.05（小数第 2 位）なら → どちらも **100 倍**（右に 2 つ）
- わる数が 0.002（小数第 3 位）なら → どちらも **1000 倍**（右に 3 つ）

例：`12 ÷ 0.05` → `1200 ÷ 5` = **240**
"""

_DECIMAL_SHIFT_TEXT = """
#### ⑥ 10倍・100倍・1000倍 ＝ 小数点を動かすだけ

かけ算は**右**へ、わり算は**左**へ、0 の数だけ小数点を動かす。

けたが足りなくなったら、**0 を書きたす**。

```text
0.25 × 1000 :  0.25 → 2.5 → 25 → 250
   3 ÷ 1000 :  3 → 0.3 → 0.03 → 0.003
```

#### ⑦ 単位に使ってみよう

- 1 A = 1000 mA → **A から mA** は右に 3 つ：`0.3 A` = **300 mA**
- **mA から A** は左に 3 つ：`25 mA` = **0.025 A**
- 1 kΩ = 1000 Ω → **kΩ から Ω** は右に 3 つ：`2.2 kΩ` = **2200 Ω**
- 1 kW = 1000 W → **W から kW** は左に 3 つ：`600 W` = **0.6 kW**

だから「kΩ × mA」は、右に 3 つと左に 3 つで**うち消し合って**、そのままかけ算すると V になるよ。
"""


def _filter(rows: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    if not query:
        return rows
    needle = query.strip().lower()
    return [row for row in rows if any(needle in str(value).lower() for value in row.values())]


def _table(rows: list[dict[str, Any]], query: str, empty_note: str = "該当する項目がありません。") -> None:
    filtered = _filter(rows, query)
    if not filtered:
        st.caption(empty_note)
        return
    st.dataframe(pd.DataFrame(filtered), use_container_width=True, hide_index=True)


def render() -> None:
    st.subheader("早見表")
    query = st.text_input(
        "検索",
        key="ref_query",
        placeholder="単位名・記号・キーワードで絞り込み（例: キロ、Pa、坪）",
    )

    prefix_rows = [
        {
            "記号": p.symbol,
            "読み": p.name,
            "指数": p.factor_text,
            "倍数": f"{10 ** p.exponent:,}" if 0 <= p.exponent <= 12 else p.factor_text,
        }
        for p in units.SI_PREFIXES
    ]
    base_rows = [
        {"記号": u.symbol, "読み": u.name, "量": u.quantity, "定義の根拠": u.definition}
        for u in units.SI_BASE_UNITS
    ]
    derived_rows = [
        {
            "記号": u.symbol,
            "読み": u.name,
            "量": u.quantity,
            "他のSI単位での表現": u.in_other_si,
            "SI基本単位での表現": u.in_base_units,
        }
        for u in units.SI_DERIVED_UNITS
    ]
    conversion_rows = units.conversion_rows()

    with st.expander("図でわかる 電圧・電流・抵抗", expanded=bool(query)):
        st.markdown(_VIR_INTRO)
        render_figure(water_model_svg())
        st.markdown(_VIR_WATER)
        render_figure(labeled_circuit_svg())
        st.markdown(_VIR_CIRCUIT)
        st.markdown(_VIR_RELATION)
        render_figure(relation_bars_svg())
        st.markdown(_VIR_RELATION_AFTER)
        render_figure(ohm_triangle_svg())
        st.markdown(_VIR_TRIANGLE)
        hidden = st.radio(
            "かくしてみる（もとめたいもの）",
            options=["V", "I", "R"],
            key="ref_triangle",
            format_func=lambda k: {"V": "電圧 V", "I": "電流 I", "R": "抵抗 R"}[k],
            horizontal=True,
        )
        render_figure(ohm_triangle_svg(hidden))
        st.markdown({"V": "**V = I × R**", "I": "**I = V ÷ R**", "R": "**R = V ÷ I**"}[hidden])
        _table(_VIR_ROLES, query)

    with st.expander("計算のしかた（かけ算・わり算の筆算、小数点の動かし方）", expanded=bool(query)):
        st.markdown(_MULTIPLICATION)
        st.markdown(_LONG_DIVISION)
        st.markdown(_DECIMAL_SHIFT_TEXT)
        _table(_DECIMAL_SHIFT, query)

    with st.expander(f"SI接頭語（{len(prefix_rows)}種）", expanded=bool(query)):
        st.caption("2022年の第27回CGPMで追加されたロナ・クエタ・ロント・クエクトを含みます（従来は20種）。")
        _table(prefix_rows, query)

    with st.expander(f"SI基本単位（{len(base_rows)}種）", expanded=bool(query)):
        _table(base_rows, query)

    with st.expander(f"固有の名称をもつSI組立単位（{len(derived_rows)}種）", expanded=bool(query)):
        _table(derived_rows, query)

    with st.expander("オームの法則・直列並列・電力の公式", expanded=bool(query)):
        _table(_FORMULAS, query)

    with st.expander(f"非SI単位の換算一覧（{len(conversion_rows)}件）", expanded=bool(query)):
        st.caption("この表は単位換算ページと同じデータから自動生成しています。")
        _table(conversion_rows, query)
        st.caption("「≈」と「丸めた値」は、定義が循環小数になるため有限桁では書けない単位です。")

    with st.expander("温度の換算式"):
        st.markdown(
            "- T/K = t/℃ + 273.15\n"
            "- t/℉ = t/℃ × 9/5 + 32\n"
            "- t/℃ = (t/℉ − 32) × 5/9\n"
            "- 0 ℃ = 273.15 K = 32 ℉、100 ℃ = 373.15 K = 212 ℉、−40 ℃ = −40 ℉"
        )
