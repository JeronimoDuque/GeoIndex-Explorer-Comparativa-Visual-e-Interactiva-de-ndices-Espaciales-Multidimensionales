from Nodes.Rectangle_Q import Rectangle_Q as Rectangle
from Nodes.R_node import R_node

class RTree:
    def __init__(self, max_entries=4):
        self.root = R_node(max_entries=max_entries, leaf=True)

    def insert(self, rect, data=None):
        split = self.root.insert(rect, data)
        if split:
            # Crear nueva raíz
            new_root = R_node(max_entries=self.root.max_entries, leaf=False)
            new_root.children = [self.root, split]
            new_root.rectangles = [self.root.compute_mbr(), split.compute_mbr()]
            self.root = new_root

    def search(self, query_rect):
        return self._search_node(self.root, query_rect)

    def _search_node(self, node, query_rect):
        result = []
        for child, rect in zip(node.children, node.rectangles):
            if rect.intersects(query_rect):
                if node.leaf:
                    result.append(child)
                else:
                    result.extend(self._search_node(child, query_rect))
        return result
