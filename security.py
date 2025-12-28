import hashlib
import hmac
import secrets

# =========================
# Password hashing (PBKDF2)
# =========================

def hash_password(password: str, salt: str | None = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)

    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    )

    return f"pbkdf2_sha256${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt, hexdigest = stored.split("$", 2)

        if algo != "pbkdf2_sha256":
            return False

        new_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            120_000,
        ).hex()

        return hmac.compare_digest(new_hash, hexdigest)

    except Exception:
        return False


# =========================
# Helpers
# =========================

def gen_password(length: int = 6) -> str:
    # أرقام فقط – مناسب للإرسال للزبائن
    return "".join(secrets.choice("0123456789") for _ in range(length))


def parse_amount(s: str) -> int:
    # يقبل: 1000000 أو 1,000,000 أو 1_000_000
    return int(s.replace(",", "").replace("_", "").strip())
