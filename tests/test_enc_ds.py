"""Regression tests for enc_ds.enc_ds.

Place this file at:

    tests/test_enc_ds.py

and run from the repository root with:

    python -m pytest tests/test_enc_ds.py

These tests intentionally avoid a real SSH agent by monkeypatching
EncDSUtil.SignBySSHkey() to return a deterministic test signature.

The first test imports enc_ds.enc_ds normally. If invalid imports such as

    import cryptography.hazmat.backends.default_backend
    import cryptography.hazmat.primitives.ciphers.Cipher
    import cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC

remain in enc_ds.py, this test should fail.
"""

from __future__ import annotations

import hashlib
import importlib

import pytest


class DummySSHKey:
    """Small test double for the parts of a Paramiko key used by enc_ds."""

    def get_fingerprint(self) -> bytes:
        return b"dummy-ssh-key-fingerprint"


def import_enc_ds_module():
    return importlib.import_module("enc_ds.enc_ds")


@pytest.fixture()
def enc_mod(monkeypatch):
    mod = import_enc_ds_module()

    def fake_sign_by_sshkey(cls, ssh_private_key, data, algorithm="rsa-sha2-512", **kwds):
        raw = mod.paramiko.util.asbytes(data)
        return hashlib.sha512(b"enc-ds-test-signature:" + raw).digest()

    # SSHSignKDF calls EncDSUtil.SignBySSHkey via eval("EncDSUtil"), so patch
    # the base class directly.
    monkeypatch.setattr(
        mod.EncDSUtil,
        "SignBySSHkey",
        classmethod(fake_sign_by_sshkey),
    )

    return mod


def make_unit(mod):
    return mod.EncipherStorageUnit(
        master_key="0123456789abcdef",
        sshkey=DummySSHKey(),
        kdf_iterations=1,
    )


def is_v2_encrypted_leaf(mod, obj):
    return isinstance(obj, dict) and mod.EncipherStorageUnit.ENC_DICT_KEYS_V2.issubset(obj)


# ---------------------------------------------------------------------------
# Import and utility tests
# ---------------------------------------------------------------------------


def test_enc_ds_module_imports():
    mod = import_enc_ds_module()

    assert mod.__version__


def test_tobytes_frombytes_roundtrip_basic_types(enc_mod):
    cls = enc_mod.EncStoreUnit

    values = [
        None,
        True,
        False,
        0,
        1,
        -5,
        2**80,
        1.25,
        complex(1.5, -2.25),
        "hello",
        b"raw-bytes",
    ]

    for value in values:
        assert cls.FromBytes(cls.ToBytes(value)) == value

    assert cls.FromBytes(cls.ToBytes(bytearray(b"abc"))) == b"abc"


def test_rehash_string_returns_requested_length(enc_mod):
    got = enc_mod.EncDSUtil.RehashBytesIfNeeded("abc", key_bits=256)

    assert isinstance(got, bytes)
    assert len(got) == 32


def test_checkbyteslength_short_salt_raises_valueerror(enc_mod):
    with pytest.raises(ValueError, match="salt is too short"):
        enc_mod.EncDSUtil.CheckBytesLength(b"short", key_bits=256)


def test_checkbyteslength_none_generates_requested_length(enc_mod):
    got = enc_mod.EncDSUtil.CheckBytesLength(None, key_bits=256)

    assert isinstance(got, bytes)
    assert len(got) == 32


def test_is_encrypted_data_class_and_instance(enc_mod):
    cls = enc_mod.EncStoreUnit
    obj = cls.EncryptedData(
        data=b"data",
        iv=b"iv",
        salt=b"salt",
        key_prefix="prefix",
        key_suffix="suffix",
    )

    assert cls.is_encrypted_data(obj)
    assert cls.is_encrypted_data(cls.EncryptedData)


# ---------------------------------------------------------------------------
# Low-level encryption/decryption tests
# ---------------------------------------------------------------------------


def test_low_level_enciphering_with_direct_key_roundtrip(enc_mod):
    cls = enc_mod.EncStoreUnit
    key = b"\x01" * 32

    encrypted = cls.Enciphering(
        "secret",
        master_key="0123456789abcdef",
        sshkey=None,
        key=key,
    )

    assert cls.is_encrypted_data(encrypted)
    assert len(encrypted.iv) == 12
    assert len(encrypted.salt) == 32

    decrypted = cls.Decipher(
        encrypted.data,
        enc_iv=encrypted.iv,
        salt=encrypted.salt,
        master_key="0123456789abcdef",
        sshkey=None,
        key=key,
    )

    assert decrypted == "secret"


def test_low_level_direct_key_reuses_no_iv_by_default(enc_mod):
    cls = enc_mod.EncStoreUnit
    key = b"\x02" * 32

    encrypted1 = cls.Enciphering("same plaintext", master_key="0123456789abcdef", key=key)
    encrypted2 = cls.Enciphering("same plaintext", master_key="0123456789abcdef", key=key)

    assert encrypted1.iv != encrypted2.iv
    assert encrypted1.data != encrypted2.data


# ---------------------------------------------------------------------------
# EncipherStorageUnit tree roundtrip tests
# ---------------------------------------------------------------------------


def test_storage_unit_nested_roundtrip(enc_mod):
    unit = make_unit(enc_mod)

    raw = {
        "name": "enc-ds",
        "count": 3,
        "flags": [True, False, None],
        "tuple": ("x", 1, None),
        "number": 1.25,
    }

    encrypted = unit.encipher(raw)
    decrypted = unit.decipher(encrypted)

    assert decrypted == raw


def test_storage_unit_v2_leaf_shape(enc_mod):
    unit = make_unit(enc_mod)

    encrypted = unit.encipher({"secret": "value"})

    leaf = encrypted["secret"]

    assert is_v2_encrypted_leaf(enc_mod, leaf)
    assert isinstance(leaf[unit.ENC_KEY_DATA], bytes)
    assert isinstance(leaf[unit.ENC_KEY_IV], bytes)
    assert isinstance(leaf[unit.ENC_KEY_SALT], bytes)
    assert isinstance(leaf[unit.ENC_KEY_PREFIX], str)
    assert isinstance(leaf[unit.ENC_KEY_SUFFIX], str)


def test_storage_unit_per_leaf_iv_and_prefix_are_unique(enc_mod):
    unit = make_unit(enc_mod)

    encrypted = unit.encipher({"a": "same", "b": "same"})

    a = encrypted["a"]
    b = encrypted["b"]

    assert is_v2_encrypted_leaf(enc_mod, a)
    assert is_v2_encrypted_leaf(enc_mod, b)
    assert a[unit.ENC_KEY_IV] != b[unit.ENC_KEY_IV]
    assert a[unit.ENC_KEY_PREFIX] != b[unit.ENC_KEY_PREFIX]
    assert a[unit.ENC_KEY_SUFFIX] != b[unit.ENC_KEY_SUFFIX]


def test_storage_unit_wrong_master_key_does_not_decrypt(enc_mod):
    unit1 = make_unit(enc_mod)
    unit2 = enc_mod.EncipherStorageUnit(
        master_key="fedcba9876543210",
        sshkey=DummySSHKey(),
        kdf_iterations=1,
    )

    encrypted = unit1.encipher({"secret": "value"})
    decrypted = unit2.decipher(encrypted)

    assert decrypted == encrypted


def test_encipher_data_dict_key_true_verbose_does_not_crash(enc_mod):
    """Dictionary-key encryption is currently unsupported, but verbose mode should not crash."""

    unit = enc_mod.EncipherStorageUnit(
        master_key="0123456789abcdef",
        sshkey=DummySSHKey(),
        kdf_iterations=1,
        encipher_data_dict_key=True,
    )

    encrypted = unit.encipher({"plain_key": "secret"}, verbose=True)

    # Current intended behavior: dict keys are left plain, values are encrypted.
    assert "plain_key" in encrypted
    assert is_v2_encrypted_leaf(enc_mod, encrypted["plain_key"])
    assert unit.decipher(encrypted) == {"plain_key": "secret"}


# ---------------------------------------------------------------------------
# CipherDataTree integration tests
# ---------------------------------------------------------------------------


def test_cipherdatatree_entire_data_roundtrip(enc_mod):
    raw = {"secret": "abc", "other": ["x", 1, True, None]}

    tree = enc_mod.CipherDataTree(
        master_key="0123456789abcdef",
        sshkey=DummySSHKey(),
        base_obj=raw,
        kdf_iterations=1,
    )

    encrypted = tree.encipher_node(entire_data=True)

    assert tree.root_node == encrypted
    assert tree.root_node != raw

    decrypted = tree.decipher_node(entire_data=True)

    assert decrypted == raw
    assert tree.root_node == raw


def test_cipherdatatree_key_only_encrypts_only_requested_node(enc_mod):
    """Regression test for accidentally adding the empty path when key=... is used.

    encipher_node(key=("secret",)) should encrypt only root_node["secret"],
    not the entire root tree first.
    """

    raw = {"secret": "abc", "other": "plain"}

    tree = enc_mod.CipherDataTree(
        master_key="0123456789abcdef",
        sshkey=DummySSHKey(),
        base_obj=raw,
        kdf_iterations=1,
    )

    tree.encipher_node(key=("secret",))

    assert is_v2_encrypted_leaf(enc_mod, tree.root_node["secret"])
    assert tree.root_node["other"] == "plain"

    tree.decipher_node(key=("secret",))

    assert tree.root_node == raw


def test_cipherdatatree_keys_encrypt_requested_nodes(enc_mod):
    raw = {"a": "A", "b": "B", "c": "C"}

    tree = enc_mod.CipherDataTree(
        master_key="0123456789abcdef",
        sshkey=DummySSHKey(),
        base_obj=raw,
        kdf_iterations=1,
    )

    tree.encipher_node(keys=[("a",), ("c",)])

    assert is_v2_encrypted_leaf(enc_mod, tree.root_node["a"])
    assert tree.root_node["b"] == "B"
    assert is_v2_encrypted_leaf(enc_mod, tree.root_node["c"])

    tree.decipher_node(keys=[("a",), ("c",)])

    assert tree.root_node == raw
