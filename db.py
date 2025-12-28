import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL")

@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                phone TEXT UNIQUE,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS stock_orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                service TEXT,
                months INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """)
            conn.commit()
# DB with users + stock tables
