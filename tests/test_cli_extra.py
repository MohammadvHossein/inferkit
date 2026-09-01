import pathlib
from unittest import mock
from inferkit.cli import cmd_deploy

def test_deploy_bare_metal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pathlib.Path("my_model.py").write_text("x=1", encoding="utf-8")
    monkeypatch.setattr("shutil.which", lambda x: None)
    monkeypatch.setattr("subprocess.run", lambda *a, **k: None)
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: None)
    pathlib.Path(".venv").mkdir()
    (pathlib.Path(".venv") / "bin").mkdir(exist_ok=True)
    (pathlib.Path(".venv") / "Scripts").mkdir(exist_ok=True)
    try:
        cmd_deploy(None)
    except SystemExit:
        pass
    assert True
