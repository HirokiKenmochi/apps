"""学習履歴をブラウザ（localStorage）に残すための橋渡し。

サーバーには何も保存しない。保存先はその端末のブラウザだけなので、
* 画面を読み込み直しても成績が残る
* デプロイでサーバーが再起動しても成績が残る
* 別の端末とは共有されない（引き継ぎたいときは成績タブの JSON を使う）

Streamlit のカスタムコンポーネント（``tanin/ui/storage/index.html``）を
1 つだけ置いて、そこと値をやり取りしている。
"""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from tanin import history

__all__ = ["clear_saved_history", "sync_history"]

_STORAGE_DIR = Path(__file__).parent / "storage"
_COMPONENT_KEY = "tanin_storage"


@st.cache_resource(show_spinner=False)
def _component() -> object:
    """保存用コンポーネントを 1 度だけ登録する。"""
    return components.declare_component("tanin_storage", path=str(_STORAGE_DIR))


def sync_history() -> None:
    """起動時にブラウザの保存を読み込み、以降は変更のたびに書き戻す。"""
    st.session_state.setdefault("history_loaded", False)
    st.session_state.setdefault("history_cleared", False)

    if st.session_state["history_cleared"]:
        payload = ""  # 「履歴をすべて消す」を押したとき
    elif st.session_state["history_loaded"]:
        payload = history.to_json(st.session_state["attempts"], indent=0)
    else:
        payload = None  # まだ読み込み前なので、上書きせずに読むだけ

    try:
        stored = _component()(payload=payload, key=_COMPONENT_KEY, default=None)
    except Exception:  # noqa: BLE001 - 保存できない環境でもアプリは動かす
        st.session_state["history_loaded"] = True
        return

    if st.session_state["history_loaded"] or stored is None:
        return

    st.session_state["history_loaded"] = True
    if isinstance(stored, str) and stored.strip():
        # こわれた保存データは無視して、まっさらから始める
        with suppress(ValueError):
            st.session_state["attempts"] = history.from_json(stored)
    st.rerun()


def clear_saved_history() -> None:
    """ブラウザに保存した履歴も消す（成績タブの「履歴をすべて消す」用）。"""
    st.session_state["attempts"] = []
    st.session_state["review_queue"] = []
    st.session_state["history_cleared"] = True
