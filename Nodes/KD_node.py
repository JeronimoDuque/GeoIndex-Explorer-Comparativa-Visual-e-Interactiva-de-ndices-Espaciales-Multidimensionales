import numpy as np

class AdaptiveKDNode:
    def __init__(self, points=None, depth=0):
        self.left = None
        self.right = None
        self.axis = None
        self.point = None
        
        if points is not None and len(points) > 0:
            self.build(points, depth)

    def build(self, points, depth):
        """Construye un nodo eligiendo el eje de mayor varianza."""
        points = np.array(points)
        variances = np.var(points, axis=0)
        self.axis = np.argmax(variances)   # eje de mayor varianza

        # ordenar por el eje adaptativo
        points = points[points[:, self.axis].argsort()]

        median_idx = len(points)//2
        self.point = points[median_idx]

        left_points = points[:median_idx]
        right_points = points[median_idx+1:]

        if len(left_points) > 0:
            self.left = AdaptiveKDNode(left_points, depth+1)
        if len(right_points) > 0:
            self.right = AdaptiveKDNode(right_points, depth+1)

    def insert(self, point):
        """Inserta un nuevo punto manteniendo el eje adaptativo local."""
        if point[self.axis] < self.point[self.axis]:
            if self.left:
                self.left.insert(point)
            else:
                self.left = AdaptiveKDNode([point])
        else:
            if self.right:
                self.right.insert(point)
            else:
                self.right = AdaptiveKDNode([point])

        # Rebalanceo adaptativo simple
        self.rebalance()

    def rebalance(self):
        """Rebalanceo local: si la diferencia de tamaños es grande, reconstruye el nodo."""
        def size(node):
            if node is None:
                return 0
            return 1 + size(node.left) + size(node.right)

        left_size = size(self.left)
        right_size = size(self.right)

        # criterio simple de desbalance
        if max(left_size, right_size) > 3 * min(left_size, right_size + 1):
            # reconstruir el nodo con todos sus puntos
            points = self.collect_points()
            self.build(points, 0)

    def collect_points(self):
        """Recolecta todos los puntos del subárbol."""
        pts = [self.point]
        if self.left:  pts.extend(self.left.collect_points())
        if self.right: pts.extend(self.right.collect_points())
        return pts

    def nearest_neighbor(self, target, best=None, best_dist=float("inf")):
        """Búsqueda de vecino más cercano."""
        if self.point is None:
            return best, best_dist

        dist = np.linalg.norm(target - self.point)
        if dist < best_dist:
            best = self.point
            best_dist = dist

        # decidir qué lado explorar primero
        go_left = target[self.axis] < self.point[self.axis]

        first = self.left if go_left else self.right
        second = self.right if go_left else self.left

        if first:
            best, best_dist = first.nearest_neighbor(target, best, best_dist)

        # verificar si vale la pena explorar el otro lado
        if second and abs(target[self.axis] - self.point[self.axis]) < best_dist:
            best, best_dist = second.nearest_neighbor(target, best, best_dist)

        return best, best_dist

