from collections.abc import Iterable
from dataclasses import fields
from pathlib import Path

from image_diff.dom.parse import load_snapshot
from image_diff.model import Element, Snapshot

ElementTarget = tuple[tuple[str, ...], str]
StyleTarget = tuple[ElementTarget, tuple[str, ...]]


def _element_difference(expected: Element, actual: Element) -> str | None:
    for field in fields(Element):
        expected_value = getattr(expected, field.name)
        actual_value = getattr(actual, field.name)
        if field.name == "styles":
            expected_value, actual_value = dict(expected_value), dict(actual_value)
        if expected_value != actual_value:
            return f"{field.name}: expected {expected_value!r}, got {actual_value!r}"
    return None


def _target_element_difference(expected: Element, actual: Element) -> str | None:
    for field in fields(Element):
        if field.name in {"id", "parent", "frames", "selector", "paint_order"}:
            continue
        expected_value = getattr(expected, field.name)
        actual_value = getattr(actual, field.name)
        if field.name == "styles":
            expected_value, actual_value = dict(expected_value), dict(actual_value)
        if expected_value != actual_value:
            return f"{field.name}: expected {expected_value!r}, got {actual_value!r}"
    return None


def snapshot_difference(
    expected: Snapshot,
    actual: Snapshot,
    targets: Iterable[ElementTarget] | None = None,
    style_targets: Iterable[StyleTarget] | None = None,
) -> str | None:
    if style_targets is not None:
        if targets is not None:
            raise ValueError("Element targets and style targets cannot be compared together")
        target_styles: dict[ElementTarget, set[str]] = {}
        for key, styles in style_targets:
            target_styles.setdefault(key, set()).update(styles)
        if not target_styles:
            return "no target styles were specified"

        expected_by_key = {(element.frames, element.selector): element for element in expected.elements}
        actual_by_key = {(element.frames, element.selector): element for element in actual.elements}
        for key in sorted(target_styles):
            _, selector = key
            expected_element = expected_by_key.get(key)
            actual_element = actual_by_key.get(key)
            if expected_element is None:
                return f"element {selector} in frames {key[0]!r}: expected missing, got present"
            if actual_element is None:
                return f"element {selector} in frames {key[0]!r}: expected present, got missing"
            styles = target_styles[key]
            if not styles:
                return f"element {selector}: no changed styles were specified"
            for style in sorted(styles):
                if style not in expected_element.styles and style not in actual_element.styles:
                    return f"element {selector}: style {style!r} is missing from both snapshots"
                expected_value = expected_element.styles.get(style)
                actual_value = actual_element.styles.get(style)
                if expected_value != actual_value:
                    return f"element {selector}: style {style}: expected {expected_value!r}, got {actual_value!r}"
        return None

    if targets is not None:
        target_keys = set(targets)
        if not target_keys:
            return "no target elements were specified"

        expected_by_key = {(element.frames, element.selector): element for element in expected.elements}
        actual_by_key = {(element.frames, element.selector): element for element in actual.elements}
        for frames, selector in sorted(target_keys):
            key = (frames, selector)
            expected_element = expected_by_key.get(key)
            actual_element = actual_by_key.get(key)
            if expected_element is None and actual_element is None:
                continue
            if expected_element is None:
                return f"element {selector} in frames {frames!r}: expected missing, got present"
            if actual_element is None:
                return f"element {selector} in frames {frames!r}: expected present, got missing"
            difference = _target_element_difference(expected_element, actual_element)
            if difference:
                return f"element {selector}: {difference}"
        return None

    if expected.page_size != actual.page_size:
        return f"page size: expected {expected.page_size!r}, got {actual.page_size!r}"
    if len(expected.elements) != len(actual.elements):
        return f"element count: expected {len(expected.elements)}, got {len(actual.elements)}"

    for index, (expected_element, actual_element) in enumerate(zip(expected.elements, actual.elements)):
        difference = _element_difference(expected_element, actual_element)
        if difference:
            return f"element {index} ({expected_element.selector}): {difference}"
    return None


def assert_snapshot_matches(
    expected_path: Path,
    actual_path: Path,
    targets: Iterable[ElementTarget] | None = None,
    style_targets: Iterable[StyleTarget] | None = None,
) -> None:
    expected = load_snapshot(expected_path)
    actual = load_snapshot(actual_path)
    difference = snapshot_difference(expected, actual, targets, style_targets)
    if difference:
        raise AssertionError(f"DOM snapshot differs from expected {expected_path}:\n{difference}")
