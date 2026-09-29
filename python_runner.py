"""
Runner WSGI minimal.

Le fichier Python du site doit définir :
    def create_app():
        return app

Exemple Flask :
    from flask import Flask
    app = Flask(__name__)

    @app.get("/")
    def index():
        return "Hello"

    def create_app():
        return app
"""

import importlib.util
import sys
from pathlib import Path


def load_module(path: str):
    path = str(Path(path).resolve())
    spec = importlib.util.spec_from_file_location("managed_site", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Impossible de charger {path}")

    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(Path(path).parent))
    spec.loader.exec_module(module)
    return module


def main():
    if len(sys.argv) != 3:
        print("Usage: python python_runner.py sites/python/app.py 5001")
        raise SystemExit(2)

    script = sys.argv[1]
    port = int(sys.argv[2])
    module = load_module(script)

    if not hasattr(module, "create_app"):
        raise RuntimeError(
            f"{script} doit définir create_app() retournant une application WSGI."
        )

    app = module.create_app()

    try:
        from werkzeug.serving import run_simple
    except ImportError:
        raise RuntimeError("Installe Flask/Werkzeug : pip install flask")

    run_simple(
        hostname="0.0.0.0",
        port=port,
        application=app,
        use_reloader=False,
        use_debugger=False,
    )


if __name__ == "__main__":
    main()
