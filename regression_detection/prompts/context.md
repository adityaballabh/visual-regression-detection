{% include "boxes_guide.md" if variant == "boxes" else "image_guide.md" %}

Decide whether the change introduces a visual REGRESSION: an unintended
visual defect. Changes that match the design intent are NOT regressions, even if
large. Changes that contradict the design intent or break the design language
are regressions, as are defects such as overlap, clipping, misalignment,
broken spacing, unreadable text or unexpected missing elements.

## Design intent
{{ design_intent }}

## Design language
{{ design_language }}

{% if variant != "images" %}
## Detected changes (boxes.json)
Coordinates are pixels in the screenshot. "detail", when present, describes the
DOM property change behind the box.
{{ boxes }}

{% endif %}
Report only boxes {{ "numbered in the images" if variant == "images" else "whose ids appear above" }}. Put every box you judge to be an
intended change in intended_box_ids. If nothing is a regression set
is_regression to false and leave regressions empty.
