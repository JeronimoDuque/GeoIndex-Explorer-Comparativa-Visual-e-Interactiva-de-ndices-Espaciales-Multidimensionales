from Nodes.R_tree.Point import Point
from Nodes.R_tree.Rectangle_R import Rectangle

class Polygon:
    """ Polígono irregular definido por una lista de puntos """
    def __init__(self, points):
        self.points = points    # Lista de Point()

    def to_tuples(self):
        return [(p.x, p.y) for p in self.points]

    def bounding_rect(self):
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return Rectangle(min(xs), min(ys), max(xs), max(ys))