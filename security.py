import hashlib
import hmac
import os
import secrets

def hash_password(password: str, salt: str | None = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${dk.hex()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt, hexdigest = stored.split("$", 2)
        if algo != "pbkdf2_sha256":
            return False
        check = hash_password(password, salt).split("$", 2)[2]
        return hmac.compare_digest(check, hexdigest)
    except Exception:
        return False

def gen_password(length: int = 6) -> str:
    # digits only (easier to send to customers)
    return "".join(secrets.choice("0123456789") for _ in range(length))

def parse_amount(s: str) -> int:
    # Accept: 1000000 or 1,000,000 or 1_000_000
    s = s.replace(",", "").replace("_", "").strip()
    return int(s)
