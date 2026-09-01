import pathlib
from inferkit.cli import bump_version

def test_bump(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pathlib.Path("pyproject.toml").write_text('version = "0.1.2"\n', encoding="utf-8")
    pathlib.Path("inferkit").mkdir()
    pathlib.Path("inferkit/__init__.py").write_text('__version__ = "0.1.2"\n', encoding="utf-8")
    v = bump_version("patch")
    assert v == "0.1.3"
