import pathlib
import subprocess
import sys

from inferkit.cli import bump_version, cmd_init


def test_bump_patch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pathlib.Path("pyproject.toml").write_text('version = "1.2.3"\n', encoding="utf-8")
    pathlib.Path("inferkit").mkdir()
    pathlib.Path("inferkit/__init__.py").write_text('__version__ = "1.2.3"\n', encoding="utf-8")
    v = bump_version("patch")
    assert v == "1.2.4"
    v = bump_version("minor")
    assert v == "1.3.0"
    v = bump_version("major")
    assert v == "2.0.0"


def test_init_creates_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cmd_init(None)
    assert pathlib.Path(".env.example").exists()
    assert pathlib.Path(".env").exists()
    assert pathlib.Path("Dockerfile").exists()


def test_cli_help():
    r = subprocess.run([sys.executable, "-m", "inferkit.cli", "--help"], capture_output=True, text=True)
    assert r.returncode == 0 or "usage" in r.stdout.lower() or "usage" in r.stderr.lower()
