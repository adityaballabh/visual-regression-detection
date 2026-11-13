A visual regression detector found that a code change broke a page. Write ONE Python `unittest` that pins down the
correct page: it must PASS on the DOM snapshot of the page before the change and FAIL on the snapshot after it. The
test will later be run against a snapshot captured from any build of the app, so it must not depend on this repository
or its code, only on the snapshot.

## Detected regression
The page redesign updates typography, footer spacing, and content structure, but introduces a visual regression where the 'Savings Accounts' card background color inappropriately changes from green to red.

Flagged boxes. `selector` and `frames` locate the element in the snapshots, `before` and `after` are pixel boxes in the
screenshots, `detail` is the DOM change behind the box when known:
[
 {
  "id": 3,
  "type": "color",
  "before": {
   "x": 443,
   "y": 293,
   "width": 394,
   "height": 97
  },
  "after": {
   "x": 443,
   "y": 311,
   "width": 394,
   "height": 97
  },
  "element": "<div> containing 'Savings Accounts'",
  "selector": "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)",
  "frames": [],
  "detail": "background-color rgb(220, 252, 231) -> rgb(254, 202, 202)",
  "category": "color",
  "severity": "medium",
  "explanation": "The background color of the 'Savings Accounts' section changed from light green (rgb(220, 252, 231)) to light red (rgb(254, 202, 202)). Red background styling connotes danger, loss, or warning, which is incorrect for a savings account product feature.",
  "violated_rule": null
 }
]

What the two snapshots say about those elements (values come straight from the snapshots):
[
 {
  "selector": "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)",
  "in_before": true,
  "in_after": true,
  "tag": "div",
  "own_text": "",
  "box_before": {
   "x1": 443,
   "y1": 293,
   "x2": 837,
   "y2": 390
  },
  "box_after": {
   "x1": 443,
   "y1": 311,
   "x2": 837,
   "y2": 408
  },
  "styles_that_differ": {
   "background-color": {
    "before": "rgb(220, 252, 231)",
    "after": "rgb(254, 202, 202)"
   }
  },
  "attributes": {
   "before": {
    "style": "flex:1;padding:16px;background:#dcfce7;border-radius:8px"
   },
   "after": {
    "style": "flex:1;padding:16px;background:#fecaca;border-radius:8px"
   }
  }
 }
]

## Design intent of the change
The "About" link was removed from the navigation, the main heading was made larger, the "Savings Accounts" card was not changed at all, a "Personal finance coaching" item was added to the list, and the footer was made taller by increasing its padding.

## Design language
Dark navy header and footer framing a light content area.
Blue marks primary actions, and soft pastel cards group related content.
Plain sans-serif text with bold headings, comfortable spacing and rounded corners on cards and buttons.

## Files
- Before snapshot (the correct page): examples/general/synthetic_five_changes/captures/before_snapshot.json
- After snapshot (the regressed page): examples/general/synthetic_five_changes/captures/after_snapshot.json
- Code behind the change: examples/general/synthetic_five_changes/html (before.html and after.html, the whole page)
- Changes between before and after: examples/general/synthetic_five_changes/out/test_generation/llm/claude-sonnet-5-5/detection-gemini-3.6-flash/boxes/baseline/code_changes.diff

Inspect the code and the diff to understand which component renders the flagged elements and what change broke
them. The diff may include unrelated changes (tests, capture helpers), ignore those. The snapshot format is defined
by `image_diff/model.py` and `image_diff/dom/parse.py` in the repo root.

## Snapshot API
`from image_diff.dom.parse import load_snapshot` gives `load_snapshot(Path) -> Snapshot`, with `snapshot.elements`
in document order. Each `Element` has:
- `selector`: positional CSS selector, unique within its frame, and `frames`: the selectors of the enclosing iframes
- `tag`, `attributes` (dict), `own_text`, `parent` and `id`
- `box`: page pixels with `x1`, `y1`, `x2`, `y2`, `width`, `height`
- `styles`: computed CSS, property name to value string, like `"background-color": "rgb(220, 252, 231)"`
- `visible`, `paint_order`, `text_box`

## The test
Write exactly one file, examples/general/synthetic_five_changes/out/test_generation/llm/claude-sonnet-5-5/detection-gemini-3.6-flash/boxes/baseline/test_generated_regression.py, and nothing else. It must:
1. Read the snapshot under test from the `ACTUAL_SNAPSHOT` environment variable, like this skeleton:

```python
import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))
```

2. Find each flagged element by `frames` and `selector`. If a box has no selector, find the element by its text, tag
   and position from the snapshots. Prefer a more stable id, class or `data-` attribute found in the code only if it
   is present in both snapshots.
3. Assert on the property that is wrong: computed styles, size or position, text, attributes, or presence. Take every
   expected value from the BEFORE snapshot, never guess one. Sizes and positions may differ by 1 px.
4. Assert only on what was flagged. Do not compare the whole page, and do not assert on changes the design intent
   says are intended, since those differ between before and after by design.
5. Fail with a message naming the selector, the property, the expected and the actual value.
6. Use only the standard library and `image_diff`, no absolute paths, no network.
7. Put a docstring on the test saying which regression it guards and which code change caused it.

## Verify before you finish
Run both commands from your working directory, each one on its own, exactly as written: no `cd`, no chaining and no
pipes. The first must pass and the second must fail with an assertion about a flagged element, not an import error or
a crash. Fix the test until both hold.
```
ACTUAL_SNAPSHOT=examples/general/synthetic_five_changes/captures/before_snapshot.json PYTHONPATH=. .venv/bin/python -m unittest test_generated_regression
ACTUAL_SNAPSHOT=examples/general/synthetic_five_changes/captures/after_snapshot.json PYTHONPATH=. .venv/bin/python -m unittest test_generated_regression
```
Finish with one or two sentences on what the test asserts.