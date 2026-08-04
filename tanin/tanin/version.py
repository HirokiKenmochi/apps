"""いま動いているアプリがどのコミットのものかを調べる（Streamlit 非依存）。

公開したアプリに「push した内容が反映されたか」を確かめるために使う。

* `static/version.txt` … `scripts/deploy.sh` が push のたびに書き換えるファイル。
  Streamlit の静的配信により `<アプリのURL>/app/static/version.txt` で外からも読める。
* 見つからなければ git のコミットハッシュ、それも無ければ "unknown" を返す。
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

__all__ = ["Version", "current_version", "read_version_file", "repo_root"]

VERSION_FILE = "static/version.txt"


@dataclass(frozen=True)
class Version:
    """アプリのバージョン情報。"""

    build: str = ""
    commit: str = ""
    source: str = "unknown"

    @property
    def label(self) -> str:
        """画面に出す 1 行の文字列。"""
        parts = [part for part in (self.build, self.commit) if part]
        return " ・ ".join(parts) if parts else "バージョン不明"


def repo_root() -> Path:
    """このファイルから見たプロジェクトのルート。"""
    return Path(__file__).resolve().parent.parent


def read_version_file(root: Path | None = None) -> dict[str, str]:
    """``static/version.txt`` を ``key=value`` として読む。無ければ空の辞書。"""
    path = (root or repo_root()) / VERSION_FILE
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    values: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            values[key.strip()] = value.strip()
    return values


def _git_commit(root: Path) -> str:
    try:
        result = subprocess.run(  # noqa: S603 - 固定の git コマンドのみ実行する
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def current_version(root: Path | None = None) -> Version:
    """いま動いているコードのバージョンを返す。"""
    base = root or repo_root()
    values = read_version_file(base)
    commit = values.get("commit", "") or _git_commit(base)
    build = values.get("build", "")
    if build or commit:
        source = "version.txt" if values else "git"
        return Version(build=build, commit=commit, source=source)
    return Version()
