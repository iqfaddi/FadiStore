import os
import psycopg2
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
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            phone TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            balance BIGINT DEFAULT 0,
            created_at TIMESTAMP NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS packages (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            price BIGINT NOT NULL,
            active BOOLEAN DEFAULT TRUE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            package_id INTEGER REFERENCES packages(id),
            user_number TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            active BOOLEAN DEFAULT TRUE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS product_plans (
            id SERIAL PRIMARY KEY,
            product_id INTEGER REFERENCES products(id),
            group_key TEXT NOT NULL,
            group_name TEXT NOT NULL,
            duration_label TEXT NOT NULL,
            price_usd NUMERIC(10,2) NOT NULL,
            active BOOLEAN DEFAULT TRUE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS premium_orders (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            plan_id INTEGER REFERENCES product_plans(id),
            status TEXT DEFAULT 'pending',
            fx_rate INTEGER NOT NULL,
            deducted_lbp BIGINT NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS order_deliveries (
            id SERIAL PRIMARY KEY,
            order_type TEXT NOT NULL,
            order_id INTEGER NOT NULL,
            phone TEXT,
            email TEXT,
            password TEXT,
            notes TEXT,
            delivered_at TIMESTAMP NOT NULL
        )
        """)


def list_premium_groups(product_slug: str):
    with get_conn() as c:
        cur = c.cursor()

        cur.execute(
            "SELECT id, title FROM products WHERE slug=%s AND active=TRUE",
            (product_slug,),
        )
        product = cur.fetchone()
        if not product:
            return []

        cur.execute(
            """
            SELECT id, group_key, group_name, duration_label, price_usd
            FROM product_plans
            WHERE product_id=%s AND active=TRUE
            ORDER BY group_name, price_usd
            """,
            (product["id"],),
        )
        plans = cur.fetchall()

        groups = {}
        for p in plans:
            key = p["group_key"]
            if key not in groups:
                groups[key] = {
                    "group_key": key,
                    "group_name": p["group_name"],
                    "plans": [],
                }
            groups[key]["plans"].append(p)

        return list(groups.values())


def list_all_user_orders(user_id: int):
    with get_conn() as c:
        cur = c.cursor()

        cur.execute(
            """
            SELECT o.id, 'ushare' AS order_type, o.status,
                   p.name AS item, o.created_at
            FROM orders o
            JOIN packages p ON p.id = o.package_id
            WHERE o.user_id=%s
            """,
            (user_id,),
        )
        ushare = cur.fetchall()

        cur.execute(
            """
            SELECT po.id, 'premium' AS order_type, po.status,
                   (pp.group_name || ' - ' || pp.duration_label || ' (' || pr.title || ')') AS item,
                   po.created_at
            FROM premium_orders po
            JOIN product_plans pp ON pp.id = po.plan_id
            JOIN products pr ON pr.id = pp.product_id
            WHERE po.user_id=%s
            """,
            (user_id,),
        )
        premium = cur.fetchall()

        return sorted(ushare + premium, key=lambda x: x["created_at"], reverse=True)
