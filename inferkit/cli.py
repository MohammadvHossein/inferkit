import argparse
import pathlib
import shutil
import subprocess
import sys

def cmd_init(args):
    base = pathlib.Path.cwd()
    env_ex = base / ".env.example"
    env = base / ".env"
    if not env_ex.exists():
        env_ex.write_text(
            "APP_NAME=InferKit\nDEBUG=false\nHOST=0.0.0.0\nPORT=8000\nCORS_ORIGINS=[\"*\"]\nMAX_UPLOAD_MB=50\nRATE_LIMIT=60/minute\n",
            encoding="utf-8",
        )
        print("created .env.example")
    if not env.exists() and env_ex.exists():
        shutil.copy(env_ex, env)
        print("created .env from .env.example")

    dockerfile = base / "Dockerfile"
    if not dockerfile.exists():
        dockerfile.write_text(
            "FROM python:3.11-slim\nWORKDIR /app\nCOPY . .\nRUN pip install inferkit Pillow\nEXPOSE 8000\nCMD [\"inferkit\", \"serve\", \"my_model.py\"]\n",
            encoding="utf-8",
        )
        print("created Dockerfile")

    print("init done. Edit my_model.py and run: inferkit dev my_model.py")

def load_entry(entry: str):
    import importlib.util

    p = pathlib.Path(entry).resolve()
    if not p.exists():
        print(f"file not found: {entry}")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("user_model", str(p))
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
        subprocess.run(["docker", "run", "-d", "-p", "8000:8000", "inferkit-app"], check=True)
        print("deployed via docker run")
        return

    print("deploying bare metal...")
    venv = pathlib.Path(".venv")
    if not venv.exists():
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
    pip = venv / "Scripts" / "pip" if sys.platform == "win32" else venv / "bin" / "pip"
    uvicorn = venv / "Scripts" / "uvicorn" if sys.platform == "win32" else venv / "bin" / "uvicorn"
    subprocess.run([str(pip), "install", "inferkit", "Pillow"], check=False)
    if pathlib.Path("my_model.py").exists():
        load_entry("my_model.py")
    print("starting uvicorn...")
    subprocess.Popen([str(uvicorn), "inferkit.server:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"])
    print("deployed on 0.0.0.0:8000")

def main():
    parser = argparse.ArgumentParser(prog="inferkit")
    sub = parser.add_subparsers(dest="cmd")
    p_init = sub.add_parser("init", help="init project")
    p_init.set_defaults(func=cmd_init)

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
