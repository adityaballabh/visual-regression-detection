# Adapted from Similo (Nass et al., 2023)

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import NamedTuple

import numpy as np
from rapidfuzz import process
from rapidfuzz.distance import LCSseq
from scipy.optimize import linear_sum_assignment
from scipy.sparse import csr_matrix
from scipy.spatial import distance

from image_diff.model import Element, Snapshot

# Similo's weights
_STRONG_WEIGHT = 1.5
_WEAK_WEIGHT = 0.5
# Lower scoring pairs count as a removal plus an addition
_MIN_SCORE = 0.5
# Centers this far apart get no location similarity
_LOCATION_RANGE_PX = 250
_ANCHOR_ATTRIBUTES = ("id", "data-testid")
_WORD = re.compile(r"\w+")


class ElementPair(NamedTuple):
    before: Element
    after: Element


@dataclass(frozen=True)
class Matching:
    pairs: tuple[ElementPair, ...]
    removed: tuple[Element, ...]
    added: tuple[Element, ...]


def _words(text: str) -> frozenset[str]:
    return frozenset(_WORD.findall(text.lower()))


def _path(element: Element) -> list[str]:
    steps = []
    for selector in (*element.frames, element.selector):
        steps += selector.split(" > ")
    return steps


def _content_words(snapshot: Snapshot, own: list[frozenset[str]]) -> list[frozenset[str]]:
    # All the words inside each element, like innerText
    content = list(own)
    # Go backwards so each element is complete before it is added to its parent
    for element in reversed(snapshot.elements):
        if element.parent is not None:
            content[element.parent] |= content[element.id]
    return content


def _neighbor_words(snapshot: Snapshot, own: list[frozenset[str]]) -> list[frozenset[str]]:
    words_directly_inside: dict[int, frozenset[str]] = defaultdict(frozenset)
    for element in snapshot.elements:
        if element.parent is not None:
            words_directly_inside[element.parent] |= own[element.id]

    # Use the parent and everything directly inside it, including this element
    neighbors = []
    for element in snapshot.elements:
        if element.parent is None:
            neighbors.append(frozenset())
        else:
            neighbors.append(own[element.parent] | words_directly_inside[element.parent])
    return neighbors


class _PageWords:
    def __init__(self, snapshot: Snapshot):
        own = [_words(element.own_text) if element.visible else frozenset() for element in snapshot.elements]
        self.content = _content_words(snapshot, own)
        self.neighbors = _neighbor_words(snapshot, own)


def _center(element: Element) -> tuple[float, float]:
    return (element.box.x1 + element.box.x2) / 2, (element.box.y1 + element.box.y2) / 2


class _Features:
    def __init__(self, elements: list[Element], words: _PageWords):
        self.elements = elements
        self.ids = [element.attributes.get("id", "") for element in elements]
        self.names = [element.attributes.get("name", "") for element in elements]
        self.content = [words.content[element.id] for element in elements]
        self.classes = [frozenset(element.attributes.get("class", "").split()) for element in elements]
        self.hrefs = [_words(element.attributes.get("href", "")) for element in elements]
        self.alts = [_words(element.attributes.get("alt", "")) for element in elements]
        self.paths = [_path(element) for element in elements]
        self.centers = np.array([_center(element) for element in elements])
        self.areas = np.array([element.box.area for element in elements])
        self.shapes = np.array([element.box.width / element.box.height for element in elements])
        self.neighbors = [words.neighbors[element.id] for element in elements]


def _number_words(word_sets: list[frozenset[str]]) -> dict[str, int]:
    numbers: dict[str, int] = {}
    for words in word_sets:
        for word in words:
            numbers.setdefault(word, len(numbers))
    return numbers


def _exact(before_values: list[str], after_values: list[str]) -> np.ndarray:
    before, after = np.array(before_values)[:, None], np.array(after_values)[None, :]
    # NaN where neither element has a value
    present = (before != "") | (after != "")
    return np.where(present, before == after, np.nan)


def _word_table(sets: list[frozenset[str]], word_ids: dict[str, int]) -> csr_matrix:
    rows, columns = [], []
    for row, words in enumerate(sets):
        for word in words:
            rows.append(row)
            columns.append(word_ids[word])
    return csr_matrix((np.ones(len(rows)), (rows, columns)), shape=(len(sets), len(word_ids)))


def _jaccard(before_sets: list[frozenset[str]], after_sets: list[frozenset[str]]) -> np.ndarray:
    word_ids = _number_words(before_sets + after_sets)
    # Count the shared words of every pair at once
    shared = (_word_table(before_sets, word_ids) @ _word_table(after_sets, word_ids).T).toarray()
    before_sizes = np.array([len(words) for words in before_sets])[:, None]
    after_sizes = np.array([len(words) for words in after_sets])[None, :]

    union = before_sizes + after_sizes - shared
    # NaN where neither element has any words
    return np.divide(shared, union, out=np.full(shared.shape, np.nan), where=union > 0)


def _path_similarity(before_paths: list[list[str]], after_paths: list[list[str]]) -> np.ndarray:
    # Steps both paths share in order divided by the longer path's length
    return process.cdist(before_paths, after_paths, scorer=LCSseq.normalized_similarity)


def _location_similarity(before_centers: np.ndarray, after_centers: np.ndarray) -> np.ndarray:
    distances = distance.cdist(before_centers, after_centers)
    return np.clip(1 - distances / _LOCATION_RANGE_PX, 0, 1)


def _ratio(before_values: np.ndarray, after_values: np.ndarray) -> np.ndarray:
    smaller = np.minimum(before_values[:, None], after_values[None, :])
    larger = np.maximum(before_values[:, None], after_values[None, :])
    return smaller / larger


# Similo's attributes, how each is compared and its weight
_ATTRIBUTES = [
    ("ids", _exact, _STRONG_WEIGHT),
    ("names", _exact, _STRONG_WEIGHT),
    ("content", _jaccard, _STRONG_WEIGHT),
    ("neighbors", _jaccard, _STRONG_WEIGHT),
    ("classes", _jaccard, _WEAK_WEIGHT),
    ("hrefs", _jaccard, _WEAK_WEIGHT),
    ("alts", _jaccard, _WEAK_WEIGHT),
    ("paths", _path_similarity, _WEAK_WEIGHT),
    ("centers", _location_similarity, _WEAK_WEIGHT),
    ("areas", _ratio, _WEAK_WEIGHT),
    ("shapes", _ratio, _WEAK_WEIGHT),
]


def _scores(before: _Features, after: _Features) -> np.ndarray:
    similarities = []
    for attribute, compare, _ in _ATTRIBUTES:
        similarities.append(compare(getattr(before, attribute), getattr(after, attribute)))
    weights = [weight for _, _, weight in _ATTRIBUTES]

    # Hide attributes neither element has so the average skips them
    masked = np.ma.masked_invalid(similarities)
    average = np.ma.average(masked, axis=0, weights=weights)
    return average.filled()


def _best_pairs(before: _Features, after: _Features) -> list[ElementPair]:
    scores = _scores(before, after)
    rows, columns = linear_sum_assignment(scores, maximize=True)
    pairs = []
    for row, column in zip(rows, columns):
        if scores[row, column] >= _MIN_SCORE:
            pairs.append(ElementPair(before.elements[row], after.elements[column]))
    return pairs


def _anchor_keys(element: Element) -> list[tuple]:
    keys = []
    for name in _ANCHOR_ATTRIBUTES:
        if value := element.attributes.get(name):
            keys.append((name, element.tag, value))
    # Add the text since a sibling inserted before this element ends up with its old path
    if element.own_text:
        keys.append(("path", element.tag, tuple(_path(element)), element.own_text))
    return keys


def _anchors(befores: list[Element], afters: list[Element]) -> list[ElementPair]:
    before_counts: Counter[tuple] = Counter()
    for element in befores:
        before_counts.update(_anchor_keys(element))

    after_counts: Counter[tuple] = Counter()
    after_by_key: dict[tuple, Element] = {}
    for element in afters:
        keys = _anchor_keys(element)
        after_counts.update(keys)
        for key in keys:
            after_by_key[key] = element

    # Pair elements whose key is unique on both pages
    pairs = []
    paired_after = set()
    for before in befores:
        for key in _anchor_keys(before):
            if before_counts[key] != 1 or after_counts[key] != 1:
                continue
            after = after_by_key[key]
            if after.id not in paired_after:
                pairs.append(ElementPair(before, after))
                paired_after.add(after.id)
                break
    return pairs


def _group_by_tag(elements: list[Element]) -> dict[str, list[Element]]:
    groups: dict[str, list[Element]] = defaultdict(list)
    for element in elements:
        groups[element.tag].append(element)
    return groups


def match(before: Snapshot, after: Snapshot) -> Matching:
    befores = [element for element in before.elements if element.visible]
    afters = [element for element in after.elements if element.visible]
    pairs = _anchors(befores, afters)

    anchored_before = {pair.before.id for pair in pairs}
    anchored_after = {pair.after.id for pair in pairs}
    unpaired_before = _group_by_tag([element for element in befores if element.id not in anchored_before])
    unpaired_after = _group_by_tag([element for element in afters if element.id not in anchored_after])

    # Pair the rest by best overall score within each tag
    before_words, after_words = _PageWords(before), _PageWords(after)
    for tag, group_before in unpaired_before.items():
        if group_after := unpaired_after.get(tag):
            pairs += _best_pairs(_Features(group_before, before_words), _Features(group_after, after_words))

    matched_before = {pair.before.id for pair in pairs}
    matched_after = {pair.after.id for pair in pairs}
    return Matching(
        pairs=tuple(sorted(pairs, key=lambda pair: pair.before.id)),
        removed=tuple(element for element in befores if element.id not in matched_before),
        added=tuple(element for element in afters if element.id not in matched_after),
    )
