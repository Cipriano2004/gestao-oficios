"""Ponto de entrada.

    python run.py          -> servidor de produção (Waitress) em http://127.0.0.1:8000
    python run.py --dev    -> servidor de desenvolvimento do Flask com recarga automática
"""

import os
import sys

from app import create_app

if "--dev" in sys.argv:
    os.environ.setdefault("FLASK_ENV", "development")

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    porta = int(os.environ.get("PORT", "8000"))
    if "--dev" in sys.argv:
        app.run(host=host, port=porta, debug=True)
    else:
        from waitress import serve

        print(f"Gestão de Ofícios em http://{host}:{porta}")
        serve(app, host=host, port=porta, threads=8)
