from pathlib import Path

from app.main import resolve_sqlite_path


def test_vercel_rewrites_relative_sqlite_database_to_tmp():
    assert resolve_sqlite_path("sqlite:///./market_opportunity.db", is_vercel=True) == Path("/tmp/market_opportunity.db")


def test_vercel_keeps_explicit_tmp_sqlite_database():
    assert resolve_sqlite_path("sqlite:////tmp/custom.db", is_vercel=True) == Path("/tmp/custom.db")


def test_local_keeps_relative_sqlite_database():
    assert resolve_sqlite_path("sqlite:///./market_opportunity.db", is_vercel=False) == Path("market_opportunity.db")
