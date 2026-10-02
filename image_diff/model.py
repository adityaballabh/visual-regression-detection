from dataclasses import dataclass


@dataclass(frozen=True)
class Box:
    # Top left and bottom right corners, bottom right is one past the last pixel
    x1: int
    y1: int
    x2: int
    y2: int

    def is_near(self, other: "Box", distance: int) -> bool:
        # Negative when the boxes overlap on that axis
        horizontal_gap = max(self.x1 - other.x2, other.x1 - self.x2)
        vertical_gap = max(self.y1 - other.y2, other.y1 - self.y2)
        return horizontal_gap <= distance and vertical_gap <= distance

    def union(self, other: "Box") -> "Box":
        return Box(min(self.x1, other.x1), min(self.y1, other.y1), max(self.x2, other.x2), max(self.y2, other.y2))
