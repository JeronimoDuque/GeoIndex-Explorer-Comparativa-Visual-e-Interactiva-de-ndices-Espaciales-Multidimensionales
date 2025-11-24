from Nodes.R_tree.Rectangle_R import Rectangle

class R_node:
    def __init__(self, max_entries=4, leaf=False):
        self.children = []      # hijos o datos
        self.rectangles = []    # MBR de cada hijo
        self.leaf = leaf
        self.max_entries = max_entries

    def choose_subtree(self, rectangle):
        """ Regla heurística simple: mínima expansión de área """
        best = None
        best_inc = float("inf")

        for child, rect in zip(self.children, self.rectangles):
            old_area = rect.area()
            new_rect = Rectangle(rect.xmin, rect.ymin, rect.xmax, rect.ymax)
            new_rect.enlarge_to_contain(rectangle)
            inc = new_rect.area() - old_area

            if inc < best_inc:
                best_inc = inc
                best = child

        return best

    def compute_mbr(self):
        return Rectangle.bounding(self.rectangles)

    def recalc_mbr(self):
        if self.rectangles:
            return Rectangle.bounding(self.rectangles)

    def linear_split(self):
        """ División lineal simple """
        max_dist = -1
        idx1, idx2 = 0, 1

        for i in range(len(self.rectangles)):
            for j in range(i + 1, len(self.rectangles)):
                r1 = self.rectangles[i]
                r2 = self.rectangles[j]
                d = abs(r1.xmin - r2.xmin) + abs(r1.ymin - r2.ymin)
                if d > max_dist:
                    max_dist = d
                    idx1, idx2 = i, j

        all_idx = list(range(len(self.rectangles)))
        all_idx.remove(idx2)

        return [idx1], [idx2] + all_idx[1:]

    def split(self):
        idx1, idx2 = self.linear_split()

        new_node = R_node(self.max_entries, leaf=self.leaf)

        new_node.children   = [self.children[i]   for i in idx2]
        new_node.rectangles = [self.rectangles[i] for i in idx2]

        self.children   = [self.children[i]   for i in idx1]
        self.rectangles = [self.rectangles[i] for i in idx1]

        return new_node

    def insert(self, rectangle, data):
        """ Inserta en hoja o nodo interno """
        if self.leaf:
            self.children.append(data)
            self.rectangles.append(rectangle)

            if len(self.children) > self.max_entries:
                return self.split()
            return None
        
        # Nodo interno: buscar subárbol
        best = self.choose_subtree(rectangle)
        split_child = best.insert(rectangle, data)

        if split_child:
            self.children.append(split_child)
            self.rectangles.append(split_child.compute_mbr())

        self.recalc_mbr()

        if len(self.children) > self.max_entries:
            return self.split()

        return None
