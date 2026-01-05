"""Vercel/WSGI entrypoint.

Vercel's Flask detection looks for an `app` object in files like `main.py`.
This module exposes `app` without shadowing the `app/` package.
"""

from app import create_app

app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
