import argparse
import importlib.util
import pathlib
import re
import shutil
import subprocess
import sys


def cmd_init(args):
    base = pathlib.Path.cwd()
    env_ex = base / ".env.example"
    env = base / ".env"
    if not env_ex.exists():
        env_ex.write_text(
            "# InferKit config — use INFERKIT_ prefix or plain names (HOST, PORT...)\n"
            "INFERKIT_APP_NAME=InferKit\n"
            "INFERKIT_DEBUG=false\n"
            "INFERKIT_HOST=0.0.0.0\n"
            "INFERKIT_PORT=8000\n"
            "# CORS: JSON array or comma separated, * = allow all (no credentials)\n"
            "INFERKIT_CORS_ORIGINS=[\"*\"]\n"
            "INFERKIT_MAX_UPLOAD_MB=50\n"
            "INFERKIT_RATE_LIMIT=60/minute\n"
            "# INFERKIT_API_KEY=  # if set, require X-API-Key header\n",
            encoding="utf-8",
        )
        print("created .env.example")
    if not env.exists() and env_ex.exists():
        shutil.copy(env_ex, env)
        print("created .env from .env.example")
    dockerfile = base / "Dockerfile"
    if not dockerfile.exists():
        dockerfile.write_text(
            "FROM python:3.11-slim\nWORKDIR /app\nCOPY . .\nRUN pip install -e .[vision]\nEXPOSE 8000\nCMD [\"inferkit\", \"serve\", \"my_model.py\"]\n",
            encoding="utf-8",
        )
        print("created Dockerfile")
    if not (base / "my_model.py").exists():
        (base / "my_model.py").write_text(
            "from inferkit import infer\n\n"
            "@infer\n"
            "async def run(payload, files=None):\n"
            "    return {\"output\": f\"echo: {payload.get('text','')}\"}\n",
            encoding="utf-8",
        )
        print("created my_model.py")
    print("init done. Edit my_model.py and run: inferkit dev my_model.py")


def bump_version(part: str = "patch"):
    p = pathlib.Path("pyproject.toml")
    text = p.read_text(encoding="utf-8")
    m = re.search(r'^version = "(\d+)\.(\d+)\.(\d+)"', text, re.MULTILINE)
    if not m:
        print("version not found")
        sys.exit(1)
    major, minor, patch = map(int, m.groups())
    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1
    new = f"{major}.{minor}.{patch}"
    text = re.sub(r'^version = ".*?"', f'version = "{new}"', text, count=1, flags=re.MULTILINE)
    p.write_text(text, encoding="utf-8")
    init = pathlib.Path("inferkit/__init__.py")
    if init.exists():
        it = init.read_text(encoding="utf-8")
        it = re.sub(r'__version__ = ".*?"', f'__version__ = "{new}"', it)
        init.write_text(it, encoding="utf-8")
    print(f"bumped to {new}")
    return new


def cmd_bump(args):
    new = bump_version(args.part)
    if args.push:
        subprocess.run(["git", "add", "pyproject.toml", "inferkit/__init__.py"], check=True)
        subprocess.run(["git", "commit", "-m", f"bump {new}"], check=True)
        subprocess.run(["git", "push"], check=True)
        subprocess.run(["git", "tag", f"v{new}"], check=True)
        subprocess.run(["git", "push", "--tags"], check=True)
        print(f"pushed v{new}, GitHub Actions will publish")


def load_entry(entry: str):
    p = pathlib.Path(entry).resolve()
    if not p.exists():
        print(f"file not found: {entry}")
        sys.exit(1)
    if str(p.parent) not in sys.path:
        sys.path.insert(0, str(p.parent))
    spec = importlib.util.spec_from_file_location(p.stem, str(p))
    if spec is None or spec.loader is None:
        print(f"cannot load {entry}")
        sys.exit(1)
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def cmd_dev(args):
    from .server import serve

    serve(entry_file=args.entry, host=args.host, port=args.port, reload=True)


def cmd_serve(args):
    from .server import serve

    serve(entry_file=args.entry, host=args.host, port=args.port, reload=False)


def cmd_deploy(args):
    from .config import settings

    host = settings.host
    port = settings.port
    has_docker = shutil.which("docker") is not None
    has_compose = False
    if has_docker:
        try:
            subprocess.run(["docker", "compose", "version"], capture_output=True, check=True)
            has_compose = True
        except Exception:
            pass
    if has_docker and has_compose and pathlib.Path("docker-compose.yml").exists():
        print("deploying with docker compose...")
        subprocess.run(["docker", "compose", "up", "--build", "-d"], check=True)
        print("deployed via docker")
        return
    if has_docker and pathlib.Path("Dockerfile").exists():
        print("deploying with docker...")
        subprocess.run(["docker", "build", "-t", "inferkit-app", "."], check=True)
        subprocess.run(["docker", "run", "-d", "-p", f"{port}:{port}", "inferkit-app"], check=True)
        print(f"deployed via docker run on {host}:{port}")
        return
    print("deploying bare metal...")
    venv = pathlib.Path(".venv")
    if not venv.exists():
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
    pip = venv / "Scripts" / "pip" if sys.platform == "win32" else venv / "bin" / "pip"
    uvicorn = venv / "Scripts" / "uvicorn" if sys.platform == "win32" else venv / "bin" / "uvicorn"
    req = pathlib.Path("requirements.txt")
    if req.exists():
        subprocess.run([str(pip), "install", "-r", str(req)], check=False)
    elif pathlib.Path("pyproject.toml").exists():
        subprocess.run([str(pip), "install", "-e", ".[vision]"], check=False)
    else:
        subprocess.run([str(pip), "install", "inferkit[vision]"], check=False)
    print("starting uvicorn (single worker, model loaded in worker)...")
    subprocess.Popen([str(uvicorn), "inferkit.server:create_app", "--factory", "--host", host, "--port", str(port)])
    print(f"deployed on {host}:{port}")


def main():
    parser = argparse.ArgumentParser(prog="inferkit")
    sub = parser.add_subparsers(dest="cmd")
    p_init = sub.add_parser("init", help="init project")
    p_init.set_defaults(func=cmd_init)
    p_bump = sub.add_parser("bump", help="bump version")
    p_bump.add_argument("part", nargs="?", default="patch", choices=["patch", "minor", "major"])
    p_bump.add_argument("--push", action="store_true", help="commit and push tag")
    p_bump.set_defaults(func=cmd_bump)
    p_dev = sub.add_parser("dev", help="dev server with reload")
    p_dev.add_argument("entry", help="path to my_model.py")
    p_dev.add_argument("--host", default=None)
    p_dev.add_argument("--port", type=int, default=None)
    p_dev.set_defaults(func=cmd_dev)
    p_serve = sub.add_parser("serve", help="prod server")
    p_serve.add_argument("entry", help="path to my_model.py")
    p_serve.add_argument("--host", default=None)
    p_serve.add_argument("--port", type=int, default=None)
    p_serve.set_defaults(func=cmd_serve)
    p_dep = sub.add_parser("deploy", help="one-command deploy")
    p_dep.set_defaults(func=cmd_deploy)
    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)
    args.func(args)
