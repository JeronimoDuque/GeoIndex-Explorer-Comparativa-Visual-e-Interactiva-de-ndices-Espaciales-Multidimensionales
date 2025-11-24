class Rectangle:
    def __init__(self, xmin, ymin, xmax, ymax):
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax

    def intersects(self, other):
        return not (self.xmax < other.xmin or
                    self.xmin > other.xmax or
                    self.ymax < other.ymin or
                    self.ymin > other.ymax)

    def enlarge_to_contain(self, other):
        self.xmin = min(self.xmin, other.xmin)
        self.ymin = min(self.ymin, other.ymin)
        self.xmax = max(self.xmax, other.xmax)
        self.ymax = max(self.ymax, other.ymax)

    def area(self):
        return (self.xmax - self.xmin) * (self.ymax - self.ymin)

    @staticmethod
    def bounding(rectangles):
        xmin = min(r.xmin for r in rectangles)
        ymin = min(r.ymin for r in rectangles)
        xmax = max(r.xmax for r in rectangles)
        ymax = max(r.ymax for r in rectangles)
        return Rectangle(xmin, ymin, xmax, ymax)

