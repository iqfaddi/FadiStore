import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

DATABASE_URL = os.getenv("DATABASE_URL")

# Used only when USD-priced products need to be deducted from an LBP balance.
# Override in Render env variables (example: 89000, 90000, ...)
FX_RATE_LBP_PER_USD = int(os.getenv("FX_RATE_LBP_PER_USD", "90000"))

# Used only when USD-priced products need to be deducted from an LBP balance.
# You can override on Render/Supabase via environment variable.
FX_RATE_LBP_PER_USD = int(os.getenv("FX_RATE_LBP_PER_USD", "90000"))

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
            -- for Alfa Ushare requests
            user_number TEXT,
            -- for premium subscriptions (Netflix/Shahid/...)
            product_id INTEGER,
            plan_id INTEGER,
            -- amounts captured at time of order (so pricing changes won't affect old orders)
            amount_lbp BIGINT,
            amount_usd NUMERIC(10,2),
            item_label TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP NOT NULL
        )
        """)

        # Add missing columns if the table existed from an older version
        cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS user_number TEXT")
        cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS product_id INTEGER")
        cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS plan_id INTEGER")
        cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS amount_lbp BIGINT")
        cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS amount_usd NUMERIC(10,2)")
        cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS item_label TEXT")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            active BOOLEAN DEFAULT TRUE,
            features TEXT DEFAULT ''
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS product_plans (
            id SERIAL PRIMARY KEY,
            product_id INTEGER REFERENCES products(id),
            group_name TEXT DEFAULT '',
            name TEXT NOT NULL,
            duration_label TEXT NOT NULL,
            price_usd NUMERIC(10,2) NOT NULL,
            active BOOLEAN DEFAULT TRUE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS order_deliveries (
            id SERIAL PRIMARY KEY,
            order_id INTEGER UNIQUE REFERENCES orders(id),
            account_phone TEXT,
            account_email TEXT,
            account_password TEXT,
            notes TEXT,
            created_at TIMESTAMP NOT NULL
        )
        """)

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

        # Seed subscription products/plans (you can add more from Supabase/Postgres later)
        cur.execute("SELECT COUNT(*) FROM products")
        if cur.fetchone()["count"] == 0:
            cur.execute(
                "INSERT INTO products(name, active, features) VALUES (%s, TRUE, %s) RETURNING id",
                (
                    "Alfa ushare",
                    "Premium Subscription\n-Instant Delivery\n-4k Quality\n-4 Screens\n-Unlimited Offline Downloads",
                ),
            )
            alfa_pid = cur.fetchone()["id"]

            cur.execute(
                "INSERT INTO products(name, active, features) VALUES (%s, TRUE, %s) RETURNING id",
                (
                    "Netflix",
                    "",
                ),
            )
            netflix_pid = cur.fetchone()["id"]

            cur.execute(
                "INSERT INTO products(name, active, features) VALUES (%s, TRUE, %s) RETURNING id",
                (
                    "Shahid VIP",
                    "Premium Subscription\n-Instant Delivery\n-4k Quality",
                ),
            )
            shahid_pid = cur.fetchone()["id"]

            # Netflix plans
            cur.executemany(
                """INSERT INTO product_plans(product_id, group_name, name, duration_label, price_usd, active)
                   VALUES (%s,%s,%s,%s,%s,TRUE)""",
                [
                    (netflix_pid, "Netflix 1 user", "Netflix 1 user", "1 Month", Decimal("3.6")),
                    (netflix_pid, "Netflix 1 user", "Netflix 1 user", "3 Months", Decimal("6.9")),
                    (netflix_pid, "Netflix 1 user", "Netflix 1 user", "6 Months", Decimal("12.5")),
                    (netflix_pid, "Netflix 1 user", "Netflix 1 user", "1 Year", Decimal("21")),
                    (netflix_pid, "Netflix Full Account", "Netflix Full Account", "1 Month", Decimal("8.9")),
                    (netflix_pid, "Netflix Full Account", "Netflix Full Account", "1 Year", Decimal("90")),
                ],
            )

            # Shahid plans
            cur.executemany(
                """INSERT INTO product_plans(product_id, group_name, name, duration_label, price_usd, active)
                   VALUES (%s,%s,%s,%s,%s,TRUE)""",
                [
                    (shahid_pid, "Shahid 1 User VIP", "Shahid 1 User VIP", "1 Month", Decimal("2.5")),
                    (shahid_pid, "Shahid 1 User VIP", "Shahid 1 User VIP", "3 Months", Decimal("4.5")),
                    (shahid_pid, "Shahid 1 User VIP", "Shahid 1 User VIP", "1 Year", Decimal("10")),
                    (shahid_pid, "Shahid VIP Full Account", "Shahid VIP Full Account", "1 Month", Decimal("5")),
                    (shahid_pid, "Shahid VIP Full Account", "Shahid VIP Full Account", "3 Months", Decimal("10")),
                    (shahid_pid, "Shahid VIP Full Account", "Shahid VIP Full Account", "1 Year", Decimal("35")),
                ],
            )

def fmt_lbp(amount: int) -> str:
    return f"{amount:,}"

def fmt_usd(amount: Decimal) -> str:
    q = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{q}"

def usd_to_lbp(amount_usd: Decimal) -> int:
    # Convert USD to LBP using env rate.
    lbp = (amount_usd * Decimal(FX_RATE_LBP_PER_USD)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(lbp)

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


def list_products(active_only=True):
    """Returns products with their plans grouped by product."""
    with get_conn() as c:
        cur = c.cursor()
        if active_only:
            cur.execute("SELECT * FROM products WHERE active=TRUE ORDER BY name")
        else:
            cur.execute("SELECT * FROM products ORDER BY name")
        products = cur.fetchall()

        cur.execute(
            """SELECT * FROM product_plans
               WHERE active=TRUE
               ORDER BY product_id, group_name, price_usd"""
        )
        plans = cur.fetchall()

        by_pid = {}
        for pl in plans:
            by_pid.setdefault(pl["product_id"], []).append(pl)

        for p in products:
            p["plans"] = by_pid.get(p["id"], [])
        return products

def get_plan(plan_id: int):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """SELECT pl.*, pr.name AS product_name, pr.features AS product_features
               FROM product_plans pl
               JOIN products pr ON pr.id = pl.product_id
               WHERE pl.id=%s""",
            (plan_id,),
        )
        return cur.fetchone()

def create_order(user_id, package_id, user_number):
    """Create Alfa ushare order (legacy/packages)."""
    with get_conn() as c:
        cur = c.cursor()

        # Capture amount at order time
        cur.execute("SELECT name, price FROM packages WHERE id=%s", (package_id,))
        pkg = cur.fetchone()
        if not pkg:
            raise ValueError("Package not found")

        cur.execute(
            """INSERT INTO orders(user_id,package_id,user_number,amount_lbp,item_label,status,created_at)
               VALUES (%s,%s,%s,%s,%s,'pending',%s) RETURNING id""",
            (user_id, package_id, user_number, int(pkg["price"]), f"Alfa ushare - {pkg['name']}", datetime.utcnow()),
        )
        return cur.fetchone()["id"]

def create_subscription_order(user_id: int, plan_id: int):
    """Create order for any Premium Subscription product (Netflix/Shahid/etc.)."""
    plan = get_plan(plan_id)
    if not plan or not plan.get("active", True):
        raise ValueError("Plan not found")

    amount_usd = Decimal(str(plan["price_usd"]))
    amount_lbp = usd_to_lbp(amount_usd)
    item_label = f"{plan['product_name']} - {plan['name']} - {plan['duration_label']}"

    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO orders(user_id,product_id,plan_id,amount_lbp,amount_usd,item_label,status,created_at)
               VALUES (%s,%s,%s,%s,%s,%s,'pending',%s) RETURNING id""",
            (
                user_id,
                int(plan["product_id"]),
                int(plan["id"]),
                amount_lbp,
                amount_usd,
                item_label,
                datetime.utcnow(),
            ),
        )
        return cur.fetchone()["id"]
def list_user_orders(user_id, limit=50):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """SELECT o.id, o.status, o.user_number,
                      o.amount_lbp, o.amount_usd,
                      COALESCE(o.item_label, p.name, pr.name) AS item_label,
                      d.account_phone, d.account_email, d.account_password, d.notes
               FROM orders o
               LEFT JOIN packages p ON p.id = o.package_id
               LEFT JOIN products pr ON pr.id = o.product_id
               LEFT JOIN order_deliveries d ON d.order_id = o.id
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
            """SELECT o.id, o.status, o.user_number,
                      u.phone, u.balance,
                      o.amount_lbp, o.amount_usd,
                      COALESCE(o.item_label,
                               CASE WHEN o.package_id IS NOT NULL THEN 'Alfa ushare' ELSE NULL END,
                               pr.name) AS item_label,
                      p.name AS package_name,
                      p.price AS package_price,
                      pr.name AS product_name,
                      pl.name AS plan_name,
                      pl.duration_label
               FROM orders o
               JOIN users u ON u.id = o.user_id
               LEFT JOIN packages p ON p.id = o.package_id
               LEFT JOIN products pr ON pr.id = o.product_id
               LEFT JOIN product_plans pl ON pl.id = o.plan_id
               WHERE o.id = %s""",
            (oid,),
        )
        return cur.fetchone()

def deliver_order(order_id: int, account_phone: str = None, account_email: str = None, account_password: str = None, notes: str = None):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO order_deliveries(order_id, account_phone, account_email, account_password, notes, created_at)
               VALUES (%s,%s,%s,%s,%s,%s)
               ON CONFLICT (order_id)
               DO UPDATE SET account_phone=EXCLUDED.account_phone,
                             account_email=EXCLUDED.account_email,
                             account_password=EXCLUDED.account_password,
                             notes=EXCLUDED.notes""",
            (order_id, account_phone, account_email, account_password, notes, datetime.utcnow()),
        )
def update_order_status(oid: int, status: str):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(
            "UPDATE orders SET status = %s WHERE id = %s",
            (status, oid),
        )
