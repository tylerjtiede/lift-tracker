import sqlite3
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport

from lift_tracker.main import app
from lift_tracker import database


@pytest.fixture(autouse=True)
def fresh_db():
    """
    Use a single shared in-memory connection for each test.
    Patching get_connection() ensures all database calls hit the same
    in-memory database rather than creating a new (empty) one each time.
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    with patch.object(database, "get_connection", return_value=conn):
        database.init_db()
        yield
        conn.close()
