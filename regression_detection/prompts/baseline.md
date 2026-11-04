{% include "boxes_guide.md" if variant == "boxes" else "image_guide.md" %}

Decide whether the change introduces a visual regression (an unintended visual
defect). You have no information about what the change was meant to do.

{% if variant != "images" %}
## Detected changes (boxes.json)
{{ boxes }}

{% endif %}
Report only boxes {{ "numbered in the images" if variant == "images" else "whose ids appear above" }}. If nothing is a regression set
is_regression to false and leave regressions empty.
