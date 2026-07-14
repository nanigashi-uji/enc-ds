"""Regression tests for enc_ds.datatree.

Place this file at:

    tests/test_datatree.py

and run from the repository root with:

    python -m pytest

If the package is not installed in editable mode, run:

    python -m pip install -e .
    python -m pytest
"""

from __future__ import annotations

import json

import pytest

from enc_ds.datatree import DataTree, DataTreeBase


# ---------------------------------------------------------------------------
# accessor / getter
# ---------------------------------------------------------------------------


def test_get_tuple_index_zero():
    d = DataTree(base_obj=(10, 20))

    assert d[(0,)] == 10


def test_get_tuple_string_index_zero():
    d = DataTree(base_obj=(10, 20))

    assert d[("0",)] == 10


def test_get_nested_tuple_value():
    d = DataTree(base_obj=(("a", "b"), ("c", "d")))

    assert d[(0, 1)] == "b"
    assert d[("1", "0")] == "c"


def test_get_missing_dict_key_returns_none():
    """accessor_w_chk() should fail softly on a missing dict key.

    This is the desired behavior because list/tuple failures already return
    (None, False), and DataTree.getter() returns only the value part.
    """

    d = DataTree(base_obj={})

    assert d.getter("missing") is None


# ---------------------------------------------------------------------------
# setter / __setitem__
# ---------------------------------------------------------------------------


def test_tuple_setitem_updates_root_node():
    d = DataTree(base_obj=(10, 20))

    d[(1,)] = 99

    assert d.root_node == (10, 99)


def test_tuple_setitem_string_index_updates_root_node():
    d = DataTree(base_obj=(10, 20))

    d[("1",)] = 99

    assert d.root_node == (10, 99)


def test_setitem_string_key_on_dict():
    d = DataTree(base_obj={})

    d["a"] = 1

    assert d.root_node == {"a": 1}


def test_set_missing_nested_dict():
    d = DataTree(base_obj={})

    d[("a", "b")] = 1

    assert d.root_node == {"a": {"b": 1}}


def test_set_missing_deep_nested_dict():
    d = DataTree(base_obj={})

    d[("a", "b", "c")] = 1

    assert d.root_node == {"a": {"b": {"c": 1}}}


def test_setter_negative_no_padding_does_not_crash():
    got, ok = DataTreeBase.setter_w_chk([1, 2], (-3,), 99, padding=False)

    assert got == [1, 2]
    assert ok is False


def test_setter_negative_auto_create_with_mixedtype():
    got, ok = DataTreeBase.setter_w_chk(
        None,
        (-1,),
        99,
        padding=True,
        mixedtype=True,
    )

    assert ok is True
    assert got[-1] == 99


def test_set_tuple_nested_value_preserves_tuple_type():
    d = DataTree(base_obj=(("a", "b"), ("c", "d")))

    d[(1, 0)] = "C"

    assert d.root_node == (("a", "b"), ("C", "d"))
    assert isinstance(d.root_node, tuple)
    assert isinstance(d.root_node[1], tuple)


# ---------------------------------------------------------------------------
# skim_data_tree
# ---------------------------------------------------------------------------


def test_skim_tuple_leaf():
    obj = (("a", "b"), ("c", "d"))

    assert DataTreeBase.skim_data_tree(obj, [(0, 1)]) == (
        (None, "b"),
        None,
    )


def test_skim_tuple_multiple_leaves():
    obj = (("a", "b"), ("c", "d"))

    assert DataTreeBase.skim_data_tree(obj, [(0, 1), (1, 0)]) == (
        (None, "b"),
        ("c", None),
    )


def test_skim_dict_with_tuple_child():
    obj = {"x": ("a", "b"), "y": {"z": 3}}

    assert DataTreeBase.skim_data_tree(obj, [("x", 1), ("y", "z")]) == {
        "x": (None, "b"),
        "y": {"z": 3},
    }


def test_skim_tuple_with_dict_child():
    obj = ({"a": 1}, {"b": 2})

    assert DataTreeBase.skim_data_tree(obj, [(1, "b")]) == (
        None,
        {"b": 2},
    )


def test_skim_no_match_tuple_returns_empty_tuple():
    obj = (("a", "b"), ("c", "d"))

    assert DataTreeBase.skim_data_tree(obj, [(3,)]) == ()


def test_skim_no_match_dict_returns_empty_dict():
    obj = {"a": 1}

    assert DataTreeBase.skim_data_tree(obj, [("missing",)]) == {}


def test_skim_preserves_real_none_value():
    obj = (("a", None), ("c", "d"))

    assert DataTreeBase.skim_data_tree(obj, [(0, 1)]) == (
        (None, None),
        None,
    )


# ---------------------------------------------------------------------------
# rest_data_tree
# ---------------------------------------------------------------------------


def test_rest_tuple_leaf():
    obj = (("a", "b"), ("c", "d"))

    assert DataTreeBase.rest_data_tree(obj, [(0, 1)]) == (
        ("a", None),
        ("c", "d"),
    )


def test_rest_tuple_multiple_leaves():
    obj = (("a", "b"), ("c", "d"))

    assert DataTreeBase.rest_data_tree(obj, [(0, 1), (1, 0)]) == (
        ("a", None),
        (None, "d"),
    )


def test_rest_scalar_deeper_does_not_crash():
    obj = {"a": 1, "b": 2}

    assert DataTreeBase.rest_data_tree(obj, [("a", "x")]) == obj


def test_rest_out_of_range_tuple_does_not_crash():
    obj = (("a", "b"), ("c", "d"))

    assert DataTreeBase.rest_data_tree(obj, [(3, 0)]) == obj


def test_rest_missing_dict_key_does_not_crash():
    obj = {"a": 1, "b": 2}

    assert DataTreeBase.rest_data_tree(obj, [("missing",)]) == obj


# ---------------------------------------------------------------------------
# recursive_update
# ---------------------------------------------------------------------------


def test_recursive_update_tuple_tuple_preserves_tuple():
    got = DataTreeBase.recursive_update(
        new_value=(1, (2, 3)),
        base_value=(0, (0, 0)),
        type_override=False,
    )

    assert got == (1, (2, 3))
    assert isinstance(got, tuple)
    assert isinstance(got[1], tuple)


def test_recursive_update_list_dict_does_not_crash():
    got = DataTreeBase.recursive_update(
        new_value=[1, 2],
        base_value={"0": "a", "x": "b"},
        type_override=False,
    )

    assert got["0"] == 1
    assert got[1] == 2
    assert got["x"] == "b"


def test_recursive_update_dict_list_does_not_crash():
    got = DataTreeBase.recursive_update(
        new_value={"0": "a", "2": "c"},
        base_value=[0, 1],
        type_override=False,
    )

    assert got == ("a", 1, "c") or got == ["a", 1, "c"]


# ---------------------------------------------------------------------------
# conversion helpers
# ---------------------------------------------------------------------------


def test_to_tuple_returns_tuple():
    d = DataTree(base_obj=[1, 2])

    assert d.to_tuple() == (1, 2)
    assert isinstance(d.to_tuple(), tuple)


def test_to_list_from_tuple_returns_list():
    d = DataTree(base_obj=(1, 2))

    assert d.to_list() == [1, 2]


def test_to_dict_from_tuple_returns_indexed_dict():
    d = DataTree(base_obj=("a", "b"))

    assert d.to_dict() == {0: "a", 1: "b"}


# ---------------------------------------------------------------------------
# path format helpers
# ---------------------------------------------------------------------------


def test_path_format_extsplit_json():
    assert DataTree.path_format_extsplit("/tmp/a.json") == ("/tmp/a", "json", "")


def test_path_format_extsplit_json_gz():
    assert DataTree.path_format_extsplit("/tmp/a.json.gz") == (
        "/tmp/a",
        "json",
        "gz",
    )


def test_path_format_addext_existing_json():
    assert DataTree.path_format_addext("/tmp/a.json") == "/tmp/a.json"


def test_path_format_addext_add_yaml():
    assert DataTree.path_format_addext("/tmp/a", fmt="yaml") == "/tmp/a.yaml"


def test_path_format_addext_add_json_gz():
    assert DataTree.path_format_addext("/tmp/a", fmt="json", compress="gz") == (
        "/tmp/a.json.gz"
    )


# ---------------------------------------------------------------------------
# byte / tuple serialization helpers
# ---------------------------------------------------------------------------


def test_bytes_json_roundtrip():
    d = DataTree(base_obj={"payload": b"abc"})

    content = d.serialize(output_format="json", bulk=True)

    d2 = DataTree(base_obj={})
    d2.load_deserialized(content, update=False, input_format="json", getall=True)

    assert d2.root_node == {"payload": b"abc"}


def test_tuple_json_roundtrip():
    d = DataTree(base_obj={"payload": (1, 2, b"abc")})

    content = d.serialize(output_format="json", bulk=True)

    d2 = DataTree(base_obj={})
    d2.load_deserialized(content, update=False, input_format="json", getall=True)

    assert d2.root_node == {"payload": (1, 2, b"abc")}


def test_tuple_dict_key_json_roundtrip():
    d = DataTree(base_obj={(1, b"a"): "value"})

    content = d.serialize(output_format="json", bulk=True)

    d2 = DataTree(base_obj={})
    d2.load_deserialized(content, update=False, input_format="json", getall=True)

    assert d2.root_node == {(1, b"a"): "value"}


# ---------------------------------------------------------------------------
# Optional / design-choice tests
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason=(
        "Design choice: if list/tuple receives a non-integer key with a longer "
        "path, setter_w_chk() may either place the value directly at that key "
        "or recursively preserve the remaining path. Remove xfail if recursive "
        "behavior is adopted."
    ),
    strict=False,
)
def test_set_mixed_key_under_list_nested_recursive_behavior():
    d = DataTree(base_obj=[1, 2])

    d[("x", "y")] = 3

    assert d.root_node == {0: 1, 1: 2, "x": {"y": 3}}


@pytest.mark.xfail(
    reason=(
        "accessor_w_chk() currently returns None through DataTree.getter(), "
        "but __getitem__ also returns None rather than raising KeyError. "
        "Enable this if __getitem__ is changed to raise KeyError on missing keys."
    ),
    strict=False,
)
def test_getitem_missing_key_raises_keyerror():
    d = DataTree(base_obj={})

    with pytest.raises(KeyError):
        _ = d["missing"]
