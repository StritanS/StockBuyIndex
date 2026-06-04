"""Vercel Python Function entrypoint for the FastAPI backend.

Vercel discovers this file under /api and serves the imported ASGI `app` as a
single serverless function. The repository keeps the real application code in
backend/app so local FastAPI development and Vercel deployment share one app.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.main import app  # noqa: E402
