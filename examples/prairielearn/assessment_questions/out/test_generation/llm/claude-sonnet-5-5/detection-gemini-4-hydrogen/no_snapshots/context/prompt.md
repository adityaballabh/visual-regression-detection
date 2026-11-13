A visual regression detector found that a code change broke a page. Write ONE Python `unittest` that pins down the
correct page: it must PASS on the DOM snapshot of the page before the change and FAIL on the snapshot after it. The
test will later be run against a snapshot captured from any build of the app, so it must not depend on this repository
or its code, only on the snapshot.

## Detected regression
Changing the spacing for question rows removed the right-side padding, shifting the right-aligned topic badges and point values 24 pixels to the right and clipping the points text against the right edge of the viewport.

Flagged boxes. `selector` and `frames` locate the element in the snapshots, `before` and `after` are pixel boxes in the
screenshots, `detail` is the DOM change behind the box when known:
[
 {
  "id": 1,
  "type": "shape",
  "before": {
   "x": 1086,
   "y": 297,
   "width": 67,
   "height": 25
  },
  "after": {
   "x": 1110,
   "y": 297,
   "width": 67,
   "height": 25
  },
  "category": "spacing",
  "severity": "medium",
  "explanation": "The 'Algebra' badge in the first question row shifted 24 pixels to the right due to missing right-side row spacing, misaligning it with the container's right margin.",
  "violated_rule": "Design for the available space: pages may use narrow panes, scrolling regions, or smaller screens. Avoid fixed dimensions when they would cause content to clip or become unusable."
 },
 {
  "id": 2,
  "type": "shape",
  "before": {
   "x": 1196,
   "y": 302,
   "width": 59,
   "height": 15
  },
  "after": {
   "x": 1220,
   "y": 302,
   "width": 59,
   "height": 15
  },
  "category": "overflow",
  "severity": "high",
  "explanation": "The points text ('10, 5, 1') in the first question row shifted 24 pixels to the right with zero right padding, causing the final digit to clip at the right edge of the viewport.",
  "violated_rule": "Design for the available space: pages may use narrow panes, scrolling regions, or smaller screens. Avoid fixed dimensions when they would cause content to clip or become unusable."
 },
 {
  "id": 3,
  "type": "shape",
  "before": {
   "x": 1086,
   "y": 392,
   "width": 67,
   "height": 24
  },
  "after": {
   "x": 1110,
   "y": 392,
   "width": 67,
   "height": 24
  },
  "category": "spacing",
  "severity": "medium",
  "explanation": "The 'Algebra' badge in the second question row shifted 24 pixels to the right due to missing right-side row spacing, misaligning it with the container's right margin.",
  "violated_rule": "Design for the available space: pages may use narrow panes, scrolling regions, or smaller screens. Avoid fixed dimensions when they would cause content to clip or become unusable."
 },
 {
  "id": 4,
  "type": "shape",
  "before": {
   "x": 1196,
   "y": 397,
   "width": 59,
   "height": 15
  },
  "after": {
   "x": 1220,
   "y": 397,
   "width": 59,
   "height": 15
  },
  "category": "overflow",
  "severity": "high",
  "explanation": "The points text ('10, 5, 1') in the second question row shifted 24 pixels to the right with zero right padding, causing the final digit to clip at the right edge of the viewport.",
  "violated_rule": "Design for the available space: pages may use narrow panes, scrolling regions, or smaller screens. Avoid fixed dimensions when they would cause content to clip or become unusable."
 },
 {
  "id": 5,
  "type": "shape",
  "before": {
   "x": 1086,
   "y": 446,
   "width": 169,
   "height": 24
  },
  "after": {
   "x": 1110,
   "y": 446,
   "width": 169,
   "height": 24
  },
  "category": "overflow",
  "severity": "high",
  "explanation": "The 'Algebra' badge and points text ('15, 10, 5, 1') in the third question row shifted 24 pixels to the right, removing right padding and clipping the final digit at the right edge of the viewport.",
  "violated_rule": "Design for the available space: pages may use narrow panes, scrolling regions, or smaller screens. Avoid fixed dimensions when they would cause content to clip or become unusable."
 },
 {
  "id": 6,
  "type": "shape",
  "before": {
   "x": 1065,
   "y": 500,
   "width": 190,
   "height": 24
  },
  "after": {
   "x": 1089,
   "y": 500,
   "width": 190,
   "height": 24
  },
  "category": "overflow",
  "severity": "high",
  "explanation": "The 'Algebra' badge and points text ('20, 15, 10, 5, 1') in the fourth question row shifted 24 pixels to the right, removing right padding and clipping the final digit at the right edge of the viewport.",
  "violated_rule": "Design for the available space: pages may use narrow panes, scrolling regions, or smaller screens. Avoid fixed dimensions when they would cause content to clip or become unusable."
 }
]

What the two snapshots say about those elements (values come straight from the snapshots):
[]

## Design intent of the change
Changed the spacing for question rows

## Design language
# PrairieLearn UI design standards

This guide summarizes the design language and UI conventions visible in the PrairieLearn
repository. It is intended to help contributors make new UI feel consistent with the existing
product. It is a practical guide to current patterns, not a complete or formally maintained design
system; follow the nearby implementation when a page has a more specific established pattern.

## Design principles

- **Prefer familiar, consistent interactions.** Reuse established page layouts, shared components,
  and interaction patterns rather than creating a one-off control for a common task.
- **Keep interfaces clear and focused.** Use concise labels, make the primary action apparent, and
  present related information together.
- **Make accessibility part of the design.** Support keyboard use, visible focus, understandable
  labels, sufficient contrast, and responsive text and layouts.
- **Use color to reinforce meaning, not to carry it alone.** Pair visual status or category
  differences with text, icons, or another perceivable cue.

## Visual language

### Layout and components

- PrairieLearn's application UI is built primarily with Bootstrap and React. Use the existing
  Bootstrap layout and utility classes where they fit.
- Before building a reusable control, check `apps/prairielearn/src/components/` and
  `packages/ui/`. Prefer a shared component when an equivalent already exists; use
  `@prairielearn/ui` for components intended to be shared across applications.
- Use React Bootstrap for basic controls that have a dedicated Bootstrap component. For more
  complex interactive controls, follow the existing React Aria patterns in `packages/ui/`.
- Keep page-specific UI with its page, and keep visual overrides scoped to that feature rather than
  changing global styles for a local need.
- Design for the available space: pages may use narrow panes, scrolling regions, or smaller
  screens. Avoid fixed dimensions when they would cause content to clip or become unusable.

### Typography, labels, and icons

- Use sentence case for titles, buttons, and other UI labels (for example, “Save course”).
- Prefer concise, plain-language labels that describe the action or information.
- Use Bootstrap Icons for new icons. Icons that convey information or an action need an accessible
  name; decorative icons should be hidden from assistive technology.
- Don't use visual emphasis alone to communicate meaning. Keep labels and supporting text available
  when color or an icon also signals status.

### Color and status

- Prefer Bootstrap's semantic CSS variables, such as `--bs-body-color`, `--bs-body-bg`, and
  `--bs-primary`, over hard-coded colors. This helps UI follow application themes.
- Use the repository's `color-*` badge classes for the established colored badge treatment. The
  available palette and rendered examples are maintained in
  [`apps/prairielearn/public/stylesheets/colors.scss`]
  and [`docs/course/colors.html`](course/colors.html). If changing that palette, also update the
  corresponding Python color lookup as described in the stylesheet.
- Use contextual Bootstrap styles for common states such as success, warning, and danger. Make sure
  the state is also described in text or otherwise available without color perception.
- Check text and control contrast against their actual backgrounds, including in themed and
  interactive states.

## Interaction and accessibility

- All interactive controls should work with a keyboard and show a visible focus state. Preserve
  expected keyboard behavior when adding custom interactions.
- Use semantic HTML and the correct control for the task. Give inputs programmatic labels, and
  connect validation messages to their inputs; invalid fields should expose `aria-invalid` and
  reference the associated error with `aria-errormessage` where applicable.
- Give icon-only buttons an accessible name. Provide useful alternative text for meaningful images,
  and avoid redundant labels for decorative imagery.
- Ensure hover-only affordances are also available on keyboard focus. Do not make hover the only
  way to discover or use an action.
- Respect reduced-motion preferences when introducing nonessential animation.
- Test layouts with longer text and resized viewports; avoid truncating essential information
  without a way to inspect it.

For content-specific accessibility guidance, see
[`docs/question/accessibility.md`](question/accessibility.md).

## Choosing where to make a UI change

- For a page-specific visual change, edit the page's React component or its feature stylesheet.
- For a repeated control or pattern, first look for an existing shared component; if the pattern is
  genuinely reusable, consider adding it to `packages/ui/`.
- For a global visual change, verify that it is meant to affect all relevant pages before changing
  shared or global styles.
- For hydrated React pages, the server page often supplies data and mounts the editor or component;
  the rendered interface itself may live in a component under that page's `components/` directory.

## Notes on scope

The repository contains established implementation conventions and shared visual primitives, but
this guide does not prescribe a complete brand identity, font scale, spacing scale, or exhaustive
component specification. Where this guide describes a convention inferred from existing code, use
the closest maintained component or local pattern as the source of truth.

## Files
- Before snapshot (the correct page): examples/prairielearn/assessment_questions/captures/before_snapshot.json
- After snapshot (the regressed page): examples/prairielearn/assessment_questions/captures/after_snapshot.json
- Code behind the change: ~/.cache/visual-regression-detection/checkouts/bzamansky__PrairieLearn-pr11-cd449778 (checkout of the PR head, https://github.com/bzamansky/PrairieLearn/pull/11)
- Changes between before and after: examples/prairielearn/assessment_questions/out/test_generation/llm/claude-sonnet-5-5/detection-gemini-4-hydrogen/no_snapshots/context/code_changes.diff

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
Write exactly one file, examples/prairielearn/assessment_questions/out/test_generation/llm/claude-sonnet-5-5/detection-gemini-4-hydrogen/no_snapshots/context/test_generated_regression.py, and nothing else. It must:
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
ACTUAL_SNAPSHOT=examples/prairielearn/assessment_questions/captures/before_snapshot.json PYTHONPATH=. .venv/bin/python -m unittest test_generated_regression
ACTUAL_SNAPSHOT=examples/prairielearn/assessment_questions/captures/after_snapshot.json PYTHONPATH=. .venv/bin/python -m unittest test_generated_regression
```
Finish with one or two sentences on what the test asserts.