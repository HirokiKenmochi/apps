"""単位換算ページ。"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from tanin import units
from tanin.ui._common import numeric_input

_FAVORITE_LIMIT = 12


def _unit_label(quantity: units.Quantity) -> Any:
    def formatter(symbol: str) -> str:
        unit = quantity.unit(symbol)
        return f"{unit.symbol}（{unit.name}）"

    return formatter


def _swap() -> None:
    st.session_state["conv_from"], st.session_state["conv_to"] = (
        st.session_state["conv_to"],
        st.session_state["conv_from"],
    )


def _use_favorite(favorite: dict[str, str]) -> None:
    st.session_state["conv_quantity"] = favorite["quantity"]
    st.session_state["conv_from"] = favorite["from"]
    st.session_state["conv_to"] = favorite["to"]


def _add_favorite(favorite: dict[str, str]) -> None:
    favorites: list[dict[str, str]] = st.session_state["favorites"]
    if favorite in favorites:
        return
    favorites.insert(0, favorite)
    del favorites[_FAVORITE_LIMIT:]


def _remove_favorite(favorite: dict[str, str]) -> None:
    favorites: list[dict[str, str]] = st.session_state["favorites"]
    if favorite in favorites:
        favorites.remove(favorite)


def render() -> None:
    st.subheader("単位換算")

    quantities = units.list_quantities()
    labels = [q.label for q in quantities]
    st.session_state.setdefault("conv_quantity", labels[0])
    if st.session_state["conv_quantity"] not in labels:
        st.session_state["conv_quantity"] = labels[0]

    quantity_label = st.selectbox("量", labels, key="conv_quantity")
    quantity = units.get_quantity(quantity_label)
    symbols = list(quantity.symbols)

    # 変換元・変換先は「選んだ量の単位」しか選べない → 異なる量の換算は設計上できない
    if st.session_state.get("conv_from") not in symbols:
        st.session_state["conv_from"] = symbols[0]
    if st.session_state.get("conv_to") not in symbols:
        st.session_state["conv_to"] = symbols[1] if len(symbols) > 1 else symbols[0]

    left, right = st.columns(2)
    with left:
        from_symbol = st.selectbox("変換元", symbols, key="conv_from", format_func=_unit_label(quantity))
    with right:
        to_symbol = st.selectbox("変換先", symbols, key="conv_to", format_func=_unit_label(quantity))

    st.button("⇅ 変換元と変換先を入れかえる", on_click=_swap, use_container_width=True)

    text, value = numeric_input(
        f"数値（{from_symbol}）",
        key="conv_value",
        default="1",
        example="12.5",
        help_text="全角数字やカンマ区切りも読み取ります。",
    )
    sig_digits = st.slider("有効数字（桁）", min_value=3, max_value=10, key="sig_digits")

    if value is not None:
        result = units.convert(value, from_symbol, to_symbol, quantity)
        body, exact = units.format_value(result.value, sig_digits)
        source_text, _ = units.format_value(value, max(sig_digits, 10))
        with st.container(border=True):
            st.markdown(
                f'<div class="tanin-result">{"" if exact else "≈"}{body} {to_symbol}</div>',
                unsafe_allow_html=True,
            )
            sign = "=" if exact else "≈"
            st.caption(f"{source_text} {from_symbol} {sign} {body} {to_symbol}")
        if not exact:
            st.caption(
                "「≈」は「だいたいこの数」という意味。きっちり割り切れないので、"
                "表示するけた数で四捨五入しています。"
            )
        elif not result.units_exact:
            st.caption("この単位はふつう割り切れませんが、この数はちょうど割り切れました。")
    else:
        st.info("数値を入力すると結果が表示されます。")

    current = {"quantity": quantity_label, "from": from_symbol, "to": to_symbol}
    favorites: list[dict[str, str]] = st.session_state["favorites"]
    if current in favorites:
        st.button(
            "★ お気に入りから外す",
            on_click=_remove_favorite,
            args=(current,),
            use_container_width=True,
        )
    else:
        st.button(
            "☆ この組み合わせをお気に入りに追加",
            on_click=_add_favorite,
            args=(current,),
            use_container_width=True,
        )

    if favorites:
        st.markdown("**お気に入り**（タップで呼び出し）")
        columns = st.columns(2)
        for index, favorite in enumerate(favorites):
            with columns[index % 2]:
                st.button(
                    f"{favorite['from']} → {favorite['to']}",
                    key=f"fav_{index}",
                    on_click=_use_favorite,
                    args=(favorite,),
                    use_container_width=True,
                    help=favorite["quantity"],
                )

    with st.expander(f"{quantity_label}のほかの単位にまとめて換算"):
        if value is None:
            st.caption("数値を入力してください。")
        else:
            rows = []
            for symbol in symbols:
                converted = units.convert(value, from_symbol, symbol, quantity)
                body, exact = units.format_value(converted.value, sig_digits)
                rows.append(
                    {
                        "単位": symbol,
                        "読み": quantity.unit(symbol).name,
                        "値": f"{'' if exact else '≈'}{body}",
                    }
                )
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if quantity.key == "temperature":
        st.caption(
            "温度は係数ではなくオフセット付きの式で換算します："
            "T/K = t/℃ + 273.15、t/℉ = t/℃ × 9/5 + 32"
        )
