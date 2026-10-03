from image_diff.model import Box, Element

_VISIBLE = {"visibility": "visible", "opacity": "1"}
_BOX = Box(0, 0, 100, 40)


def element(
    id: int,
    parent: int | None,
    tag: str = "div",
    own_text: str = "",
    attributes: dict[str, str] | None = None,
    box: Box = _BOX,
) -> Element:
    return Element(id, parent, tag, "", (), attributes or {}, own_text, box, _VISIBLE)
