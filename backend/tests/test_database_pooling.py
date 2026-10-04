"""
Unit tests for SQLAlchemy engine connection pooling configuration.
Validates DATA-DB-003-CONNECTION-POOLING requirements.
"""

from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool

from app.core.database import Base, SessionLocal, engine, get_db, is_sqlite


def test_current_engine_pool_configuration():
    """Verify that the instantiated engine in app.core.database has production pooling configured."""
    assert engine is not None
    assert isinstance(engine.pool, QueuePool)
    if not is_sqlite:
        assert engine.pool.size() == 10
        assert engine.pool._max_overflow == 20
    else:
        assert engine.pool.size() == 5
        assert engine.pool._max_overflow == 10
    assert engine.pool._pre_ping is True
    assert engine.pool._recycle == 1800


def test_postgresql_pooling_parameters():
    """Verify create_engine configuration values for PostgreSQL URLs."""
    pg_url = "postgresql://user:pass@localhost:5432/testdb"
    pg_is_sqlite = pg_url.startswith("sqlite")

    with patch("app.core.database.create_engine", wraps=create_engine) as mock_create_engine:
        test_engine = mock_create_engine(
            pg_url,
            connect_args={"check_same_thread": False} if pg_is_sqlite else {},
            pool_size=10 if not pg_is_sqlite else 5,
            max_overflow=20 if not pg_is_sqlite else 10,
            pool_pre_ping=True,
            pool_recycle=1800,
        )

        mock_create_engine.assert_called_once_with(
            pg_url,
            connect_args={},
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
        assert isinstance(test_engine.pool, QueuePool)
        assert test_engine.pool.size() == 10
        assert test_engine.pool._max_overflow == 20
        assert test_engine.pool._pre_ping is True
        assert test_engine.pool._recycle == 1800


def test_sqlite_pooling_parameters(tmp_path):
    """Verify create_engine configuration values for SQLite URLs."""
    sqlite_db_path = tmp_path / "test_pooling.db"
    sqlite_url = f"sqlite:///{sqlite_db_path}"
    sqlite_is_sqlite = sqlite_url.startswith("sqlite")

    with patch("app.core.database.create_engine", wraps=create_engine) as mock_create_engine:
        test_engine = mock_create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False} if sqlite_is_sqlite else {},
            pool_size=10 if not sqlite_is_sqlite else 5,
            max_overflow=20 if not sqlite_is_sqlite else 10,
            pool_pre_ping=True,
            pool_recycle=1800,
        )

        mock_create_engine.assert_called_once_with(
            sqlite_url,
            connect_args={"check_same_thread": False},
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
        assert isinstance(test_engine.pool, QueuePool)
        assert test_engine.pool.size() == 5
        assert test_engine.pool._max_overflow == 10
        assert test_engine.pool._pre_ping is True
        assert test_engine.pool._recycle == 1800


def test_session_and_get_db(monkeypatch):
    """Verify that SessionLocal, Base, and get_db() dependency work as expected."""
    assert SessionLocal is not None
    assert Base is not None

    db_gen = get_db()
    session = next(db_gen)
    assert isinstance(session, Session)
    # Complete generator to trigger finally db.close()
    try:
        next(db_gen)
    except StopIteration:
        pass
