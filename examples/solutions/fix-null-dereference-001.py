"""Reference solution for task fix-null-dereference-001.

Original buggy code (before the fix):

    def process(data: dict) -> list:
        return [transform(item) for item in data["items"]]

This crashes with AttributeError when data is None and with KeyError when the
"items" key is absent.

Fix strategy
------------
Guard against None and missing keys at the entry point so all downstream logic
can assume a valid list. This is the minimal change that satisfies all
acceptance criteria and hidden edge cases without altering the public signature.
"""


from __future__ import annotations

from typing import Any


def _transform(item: Any) -> dict:
    """Placeholder transform – keep this unchanged."""
    return {"value": item}


# ── FIXED version ─────────────────────────────────────────────────────────────

def process(data: dict | None) -> list:
    """Process upstream API response into a list of transformed items.

    Args:
        data: Dict from the upstream API, or None if the service is unavailable.

    Returns:
        List of transformed items, empty if data is None or contains no items.

    Raises:
        TypeError: If data is neither None nor a dict.
    """
    if data is None:
        return []

    if not isinstance(data, dict):
        raise TypeError(
            f"process() expects a dict or None, got {type(data).__name__!r}"
        )

    # Use .get() so a missing 'items' key returns [] instead of raising KeyError
    items = data.get("items", [])
    return [_transform(item) for item in items]


# ── Regression test (optional milestone 5) ────────────────────────────────────
# This would live in tests/test_pipeline.py in the real repo.

def _test_none_response():
    assert process(None) == []


def _test_empty_dict():
    assert process({}) == []


def _test_missing_items_key():
    assert process({"status": "ok"}) == []


def _test_list_raises_type_error():
    try:
        process([1, 2, 3])
        assert False, "Expected TypeError"
    except TypeError as exc:
        assert "list" in str(exc)


def _test_happy_path():
    assert process({"items": [1, 2]}) == [{"value": 1}, {"value": 2}]


if __name__ == "__main__":
    for fn in [
        _test_none_response,
        _test_empty_dict,
        _test_missing_items_key,
        _test_list_raises_type_error,
        _test_happy_path,
    ]:
        fn()
        print(f"  PASS  {fn.__name__}")
    print("All reference solution self-tests passed.")
