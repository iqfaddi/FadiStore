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

        # Premium subscriptions (Netflix / Shahid / etc.)
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

        # Seed default premium products/plans if empty
        cur.execute("SELECT COUNT(*) FROM products")
        if cur.fetchone()["count"] == 0:
            cur.executemany(
                "INSERT INTO products(slug,title,active) VALUES (%s,%s,TRUE)",
                [("netflix","Netflix"),("shahid","Shahid VIP")],
            )

        cur.execute("SELECT COUNT(*) FROM product_plans")
        if cur.fetchone()["count"] == 0:
            # Netflix plans
            cur.execute("SELECT id FROM products WHERE slug=%s", ("netflix",))
            netflix_id = cur.fetchone()["id"]
            cur.executemany(
                "INSERT INTO product_plans(product_id,group_key,group_name,duration_label,price_usd,active) VALUES (%s,%s,%s,%s,%s,TRUE)",
                [
                    (netflix_id,"netflix_1user","Netflix 1 user","1 Month",3.60),
                    (netflix_id,"netflix_1user","Netflix 1 user","3 Months",6.90),
                    (netflix_id,"netflix_1user","Netflix 1 user","6 Months",12.50),
                    (netflix_id,"netflix_1user","Netflix 1 user","1 Year",21.00),
                    (netflix_id,"netflix_full","Netflix Full Account","1 Month",8.90),
                    (netflix_id,"netflix_full","Netflix Full Account","1 Year",90.00),
                ],
            )
            # Shahid plans
            cur.execute("SELECT id FROM products WHERE slug=%s", ("shahid",))
            shahid_id = cur.fetchone()["id"]
            cur.executemany(
                "INSERT INTO product_plans(product_id,group_key,group_name,duration_label,price_usd,active) VALUES (%s,%s,%s,%s,%s,TRUE)",
                [
                    (shahid_id,"shahid_1user","Shahid 1 User VIP","1 Month",2.50),
                    (shahid_id,"shahid_1user","Shahid 1 User VIP","3 Months",4.50),
                    (shahid_id,"shahid_1user","Shahid 1 User VIP","1 Year",10.00),
                    (shahid_id,"shahid_full","Shahid VIP Full Account","1 Month",5.00),
                    (shahid_id,"shahid_full","Shahid VIP Full Account","3 Months",10.00),
                    (shahid_id,"shahid_full","Shahid VIP Full Account","1 Year",35.00),
                ],
            )

        cur.execute("SELECT COUNT(*) FROM packages")
        if cur.fetchone()["count"] == 0:
            cur.executemany(
                "INSERT INTO packages(name, price, active) VALUES (%s,%s,TRUE)",
                [
                    ("11 GB", 870000),
                    ("22 GB", 1200000),
                    ("33 GB", 1450000),
                    ("44 GB", 1860000),
                    ("55 GB", 2280000),
                ],
            )

def fmt_lbp(amount: int) -> str:
    return f"{amount:,}"

def create_user(phone, password_hash):
    with get_conn() as c:
        c.cursor().execute(
            "INSERT INTO users(phone,password_hash,balance,created_at) VALUES (%s,%s,0,%s)",
            (phone, password_hash, datetime.utcnow()),
        )

def get_user_by_phone(phone):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM users WHERE phone=%s", (phone,))
        return cur.fetchone()

def get_user_by_id(uid):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM users WHERE id=%s", (uid,))
        return cur.fetchone()

def add_balance(phone, amt):
    with get_conn() as c:
        c.cursor().execute(
            "UPDATE users SET balance = balance + %s WHERE phone=%s",
            (amt, phone),
        )

def deduct_balance(phone, amt):
    with get_conn() as c:
        c.cursor().execute(
            "UPDATE users SET balance = balance - %s WHERE phone=%s",
            (amt, phone),
        )

def list_packages(active_only=True):
    with get_conn() as c:
        cur = c.cursor()
        if active_only:
            cur.execute("SELECT * FROM packages WHERE active=TRUE ORDER BY price")
        else:
            cur.execute("SELECT * FROM packages ORDER BY price")
        return cur.fetchall()

def create_order(user_id, package_id, user_number):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO orders(user_id,package_id,user_number,status,created_at)
               VALUES (%s,%s,%s,'pending',%s) RETURNING id""",
            (user_id, package_id, user_number, datetime.utcnow()),
        )
        return cur.fetchone()["id"]
def list_user_orders(user_id, limit=20):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """SELECT o.id, o.status,
                      o.user_number,
                      p.name AS package_name,
                      p.price AS package_price
               FROM orders o
               JOIN packages p ON p.id = o.package_id
               WHERE o.user_id = %s
               ORDER BY o.id DESC
               LIMIT %s""",
            (user_id, limit),
        )
        return cur.fetchall()
def get_order(oid: int):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """SELECT o.id, o.status,
                      o.user_number,
                      u.phone,
                      u.balance,
                      p.name AS package_name,
                      p.price AS package_price
               FROM orders o
               JOIN users u ON u.id = o.user_id
               JOIN packages p ON p.id = o.package_id
               WHERE o.id = %s""",
            (oid,),
        )
        return cur.fetchone()
def update_order_status(oid: int, status: str):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            "UPDATE orders SET status = %s WHERE id = %s",
            (status, oid),
        )

def list_premium_groups(product_slug: str):
    """Return list of groups with their plans for a product slug."""
    with get_conn() as c:
        cur = c.cursor()
        cur.execute("SELECT id,title,group_key FROM products WHERE slug=%s AND active=TRUE", (product_slug,))
        prod = cur.fetchone()
        if not prod:
            return []
        cur.execute(
            """SELECT * FROM product_plans
               WHERE product_id=%s AND active=TRUE
               ORDER BY group_name, price_usd""",
            (prod["id"],),
        )
        plans = cur.fetchall()
        groups = []
        by = {}
        for p in plans:
            key = p["group_key"]
            if key not in by:
                by[key] = {
                    "group_key": key,
                    "group_name": p["group_name"],
                    "plans": []
                }
                groups.append(by[key])
            by[key]["plans"].append(p)
        return groups

def get_plan(plan_id: int):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """SELECT pp.*, pr.slug AS product_slug, pr.title AS product_title
               FROM product_plans pp
               JOIN products pr ON pr.id = pp.product_id
               WHERE pp.id=%s""",
            (plan_id,),
        )
        return cur.fetchone()

def create_premium_order(user_id: int, plan_id: int, fx_rate: int):
    plan = get_plan(plan_id)
    if not plan:
        raise ValueError("Plan not found")
    usd = float(plan["price_usd"])
    deducted = int(round(usd * fx_rate))
    # deduct from user balance
    with get_conn() as c:
        cur = c.cursor()
        cur.execute("SELECT balance FROM users WHERE id=%s", (user_id,))
        bal = int(cur.fetchone()["balance"])
        if bal < deducted:
            raise ValueError("Insufficient balance")
        cur.execute("UPDATE users SET balance = balance - %s WHERE id=%s", (deducted, user_id))
        cur.execute(
            """INSERT INTO premium_orders(user_id,plan_id,status,fx_rate,deducted_lbp,created_at)
               VALUES (%s,%s,'pending',%s,%s,%s) RETURNING id""",
            (user_id, plan_id, fx_rate, deducted, datetime.utcnow()),
        )
        return int(cur.fetchone()["id"])

def get_premium_order(oid: int):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """SELECT po.*, u.phone,
                      pr.title AS product_title,
                      pp.group_name,
                      pp.duration_label,
                      pp.price_usd
               FROM premium_orders po
               JOIN users u ON u.id = po.user_id
               JOIN product_plans pp ON pp.id = po.plan_id
               JOIN products pr ON pr.id = pp.product_id
               WHERE po.id=%s""",
            (oid,),
        )
        return cur.fetchone()

def update_premium_order_status(oid: int, status: str):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute("UPDATE premium_orders SET status=%s WHERE id=%s", (status, oid))

def upsert_delivery(order_type: str, order_id: int, phone: str=None, email: str=None, password: str=None, notes: str=None):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """DELETE FROM order_deliveries WHERE order_type=%s AND order_id=%s""",
            (order_type, order_id),
        )
        cur.execute(
            """INSERT INTO order_deliveries(order_type,order_id,phone,email,password,notes,delivered_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (order_type, order_id, phone, email, password, notes, datetime.utcnow()),
        )

def get_delivery(order_type: str, order_id: int):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """SELECT * FROM order_deliveries WHERE order_type=%s AND order_id=%s""",
            (order_type, order_id),
        )
        return cur.fetchone()

def list_all_user_orders(user_id: int, limit: int=100):
    """Combine uShare and premium orders."""
    with get_conn() as c:
        cur = c.cursor()

        # uShare
        cur.execute(
            """SELECT o.id, 'ushare' AS order_type, o.status,
                      (p.name || ' (uShare)') AS item,
                      o.created_at
               FROM orders o
               JOIN packages p ON p.id = o.package_id
               WHERE o.user_id=%s
               ORDER BY o.id DESC
               LIMIT %s""",
            (user_id, limit),
        )
        ushare = cur.fetchall()

        # Premium
        cur.execute(
            """SELECT po.id, 'premium' AS order_type, po.status,
                      (pp.group_name || ' - ' || pp.duration_label || ' (' || pr.title || ')') AS item,
                      po.created_at
               FROM premium_orders po
               JOIN product_plans pp ON pp.id = po.plan_id
               JOIN products pr ON pr.id = pp.product_id
               WHERE po.user_id=%s
               ORDER BY po.id DESC
               LIMIT %s""",
            (user_id, limit),
        )
        prem = cur.fetchall()

    combined = []
    for row in ushare + prem:
        d = get_delivery(row["order_type"], int(row["id"]))
        if d:
            parts=[]
            if d.get("phone"): parts.append(f"Phone: {d['phone']}")
            if d.get("email"): parts.append(f"Email: {d['email']}")
            if d.get("password"): parts.append(f"Password: {d['password']}")
            if d.get("notes"): parts.append(f"Notes: {d['notes']}")
            row["delivery"] = " | ".join(parts)
        else:
            row["delivery"] = None
        combined.append(row)

    combined.sort(key=lambda r: (str(r["created_at"])), reverse=True)
    return combined
