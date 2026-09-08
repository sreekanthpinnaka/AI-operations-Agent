from __future__ import annotations

import binascii
import hashlib
import uuid
from typing import Any

from sqlalchemy import types
from sqlalchemy.engine import Dialect


def to_bin(val: str | bytes | uuid.UUID | None) -> bytes | None:
    if val is None:
        return None
    if isinstance(val, bytes):
        if len(val) == 16:
            return val
        raise ValueError(f"Expected 16 bytes for binary ID, got {len(val)}")
    if isinstance(val, uuid.UUID):
        return val.bytes
    if isinstance(val, str):
        clean = val.replace("-", "").strip()
        if len(clean) == 32:
            try:
                return bytes.fromhex(clean)
            except ValueError:
                pass
        # Fallback to deterministic MD5 for text keys (matching UNHEX(MD5(...)))
        return hashlib.md5(val.encode("utf-8")).digest()
    raise TypeError(f"Cannot convert {type(val)} to 16-byte binary")


def to_hex(val: bytes | str | uuid.UUID | None) -> str | None:
    if val is None:
        return None
    if isinstance(val, bytes):
        return binascii.hexlify(val).decode("ascii")
    if isinstance(val, uuid.UUID):
        return val.hex
    if isinstance(val, str):
        clean = val.replace("-", "").strip()
        if len(clean) == 32:
            return clean.lower()
        return hashlib.md5(val.encode("utf-8")).hexdigest()
    return str(val)


def deterministic_id(seed: str) -> str:
    """Generates a 32-character hex ID matching MySQL UNHEX(MD5('seed'))."""
    return hashlib.md5(seed.encode("utf-8")).hexdigest()


def new_id() -> str:
    """Generates a random 32-character hex ID."""
    return uuid.uuid4().hex


class Binary16(types.TypeDecorator):
    """
    SQLAlchemy type decorator that transparently stores BINARY(16) in MySQL / BLOB in SQLite,
    while representing the value as a clean 32-character hex string in Python.
    """

    impl = types.BINARY(16)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(types.BLOB(16))
        return dialect.type_descriptor(types.BINARY(16))

    def process_bind_param(self, value: Any, dialect: Dialect) -> bytes | None:
        return to_bin(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> str | None:
        return to_hex(value)
