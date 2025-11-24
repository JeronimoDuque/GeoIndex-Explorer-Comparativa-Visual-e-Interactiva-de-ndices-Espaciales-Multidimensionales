from Nodes.Rectangle_Q import Rectangle_Q
from Nodes.Point import Point

class QuadTree:
    def __init__(self, boundary, capacity=4):
        self.boundary = boundary
        self.capacity = capacity
        self.points = []
        self.divided = False

        # hijos
        self.northeast = None
        self.northwest = None
        self.southeast = None
        self.southwest = None

    def subdivide(self):
        x, y = self.boundary.x, self.boundary.y
        w, h = self.boundary.w / 2, self.boundary.h / 2

        ne = Rectangle_Q(x + w, y - h, w, h)
        nw = Rectangle_Q(x - w, y - h, w, h)
        se = Rectangle_Q(x + w, y + h, w, h)
        sw = Rectangle_Q(x - w, y + h, w, h)

        self.northeast = QuadTree(ne, self.capacity)
        self.northwest = QuadTree(nw, self.capacity)
        self.southeast = QuadTree(se, self.capacity)
        self.southwest = QuadTree(sw, self.capacity)

        self.divided = True

    def insert(self, point):
        if not self.boundary.contains(point):
            return False

        if len(self.points) < self.capacity:
            self.points.append(point)
            return True
        else:
            if not self.divided:
                self.subdivide()

            if self.northeast.insert(point): return True
            if self.northwest.insert(point): return True
            if self.southeast.insert(point): return True
            if self.southwest.insert(point): return True

        return False

    def query(self, range_rect, found=None):
        if found is None:
            found = []

        if not self.boundary.intersects(range_rect):
            return found

        for p in self.points:
            if range_rect.contains(p):
                found.append(p)

        if self.divided:
            self.northwest.query(range_rect, found)
            self.northeast.query(range_rect, found)
            self.southwest.query(range_rect, found)
            self.southeast.query(range_rect, found)

        return found
