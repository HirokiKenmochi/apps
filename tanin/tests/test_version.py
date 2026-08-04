"""tanin.version の検証（デプロイが反映されたかを見分けるための仕組み）。"""

from __future__ import annotations

from pathlib import Path

from tanin import version


def test_version_file_is_read(tmp_path: Path) -> None:
    static = tmp_path / "static"
    static.mkdir()
    (static / "version.txt").write_text("build=2026-08-02T00:00:00Z\ncommit=abc1234\n", encoding="utf-8")
    values = version.read_version_file(tmp_path)
    assert values == {"build": "2026-08-02T00:00:00Z", "commit": "abc1234"}

    current = version.current_version(tmp_path)
    assert current.build == "2026-08-02T00:00:00Z"
    assert current.commit == "abc1234"
    assert current.source == "version.txt"
    assert "abc1234" in current.label


def test_missing_version_file_is_not_an_error(tmp_path: Path) -> None:
    assert version.read_version_file(tmp_path) == {}
    current = version.current_version(tmp_path)
    assert current.source in {"git", "unknown"}
    assert current.label  # 何かしら表示できる文字列になる


def test_repo_has_a_version_file() -> None:
    """本番で配信する static/version.txt が存在すること。"""
    path = version.repo_root() / version.VERSION_FILE
    assert path.exists(), "static/version.txt が必要（scripts/deploy.sh が書き換える）"
    assert "build=" in path.read_text(encoding="utf-8")


def test_current_version_of_this_repo_has_a_label() -> None:
    current = version.current_version()
    assert current.label.strip()
