import uuid
from app.db.types import deterministic_id, new_id, to_bin, to_hex


def test_new_id_is_32_hex_chars():
    id_str = new_id()
    assert len(id_str) == 32
    assert int(id_str, 16) >= 0


def test_deterministic_id_is_consistent():
    id1 = deterministic_id("customer_alpha")
    id2 = deterministic_id("customer_alpha")
    id3 = deterministic_id("customer_beta")
    assert id1 == id2
    assert id1 != id3
    assert len(id1) == 32


def test_to_bin_and_to_hex_roundtrip():
    original_hex = "4a5e6b7c8d9e0f1a2b3c4d5e6f7a8b9c"
    binary_val = to_bin(original_hex)
    assert isinstance(binary_val, bytes)
    assert len(binary_val) == 16
    recovered_hex = to_hex(binary_val)
    assert recovered_hex == original_hex


def test_uuid_conversion():
    u = uuid.uuid4()
    b = to_bin(u)
    assert len(b) == 16
    h = to_hex(u)
    assert len(h) == 32
    assert h == u.hex
