import numpy as np

from Nodes.KD_node import AdaptiveKDNode

class AdaptiveKDTree:
    def __init__(self, points=None):
        self.root = None
        if points:
            self.root = AdaptiveKDNode(points)

    def insert(self, point):
        point = np.array(point)
        if self.root is None:
            self.root = AdaptiveKDNode([point])
        else:
            self.root.insert(point)

    def nearest(self, point):
        point = np.array(point)
        return self.root.nearest_neighbor(point)
