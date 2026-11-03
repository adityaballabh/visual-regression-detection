from dataclasses import fields
from pathlib import Path

from image_diff.dom.parse import load_snapshot
from image_diff.model import Element, Snapshot


def _element_difference(expected: Element, actual: Element) -> str | None:
    for field in fields(Element):
        expected_value = getattr(expected, field.name)
        actual_value = getattr(actual, field.name)
        if field.name == "styles":
            expected_value, actual_value = dict(expected_value), dict(actual_value)
        if expected_value != actual_value:
            return f"{field.name}: expected {expected_value!r}, got {actual_value!r}"
    return None


def snapshot_difference(expected: Snapshot, actual: Snapshot) -> str | None:
    if expected.page_size != actual.page_size:
        return f"page size: expected {expected.page_size!r}, got {actual.page_size!r}"
    if len(expected.elements) != len(actual.elements):
        return f"element count: expected {len(expected.elements)}, got {len(actual.elements)}"

    for index, (expected_element, actual_element) in enumerate(zip(expected.elements, actual.elements)):
        difference = _element_difference(expected_element, actual_element)
        if difference:
            return f"element {index} ({expected_element.selector}): {difference}"
    return None


def assert_snapshot_matches(expected_path: Path, actual_path: Path) -> None:
    expected = load_snapshot(expected_path)
    actual = load_snapshot(actual_path)
    difference = snapshot_difference(expected, actual)
    if difference:
        raise AssertionError(f"DOM snapshot differs from expected {expected_path}:\n{difference}")
