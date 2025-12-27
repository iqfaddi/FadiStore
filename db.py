import os, psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")

@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_conn() as c:
        cur = c.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_services (
            id SERIAL PRIMARY KEY,
            name TEXT,
            active BOOLEAN DEFAULT TRUE
        );
        CREATE TABLE IF NOT EXISTS stock_orders (
            id SERIAL PRIMARY KEY,
            phone TEXT,
            service_name TEXT,
            months INT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS stock_accounts (
            id SERIAL PRIMARY KEY,
            phone TEXT,
            service_name TEXT,
            email TEXT,
            password TEXT,
            profile TEXT,
            start_date DATE,
            end_date DATE
        );
        """)

def create_stock_order(phone, service, months):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            "INSERT INTO stock_orders(phone,service_name,months,created_at) VALUES (%s,%s,%s,%s) RETURNING *",
            (phone, service, months, datetime.utcnow())
        )
        return cur.fetchone()
