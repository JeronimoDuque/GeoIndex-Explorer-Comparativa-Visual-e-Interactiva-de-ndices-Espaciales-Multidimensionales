from Nodes.R_tree.Point import Point

class Rectangle_Q:
    def __init__(self, x, y, w, h):
        # (x, y) = centro del rectángulo
        self.x = x
        self.y = y
        self.w = w  # mitad del ancho
        self.h = h  # mitad del alto

    def contains(self, point):
        return (self.x - self.w <= point.x <= self.x + self.w and
                self.y - self.h <= point.y <= self.y + self.h)

    def intersects(self, range_rect):
        return not (range_rect.x - range_rect.w > self.x + self.w or
                    range_rect.x + range_rect.w < self.x - self.w or
                    range_rect.y - range_rect.h > self.y + self.h or
                    range_rect.y + range_rect.h < self.y - self.h)