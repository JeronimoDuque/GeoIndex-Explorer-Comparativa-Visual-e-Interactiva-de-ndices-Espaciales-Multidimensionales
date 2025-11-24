from Nodes.Rectangle_Q import Rectangle_Q as Rectangle

class R_node:
    def __init__(self, max_entries=4, leaf=False):
        self.children = []      # hijos o elementos
        self.rectangles = []    # MBR de cada hijo
        self.leaf = leaf
        self.max_entries = max_entries

    def insert(self, rectangle, data=None):
        if self.leaf:
            self.children.append(data)
            self.rectangles.append(rectangle)
            if len(self.children) > self.max_entries:
                return self.split()
            return None
        else:
            # Escoger el mejor hijo para insertar
            best = self.choose_subtree(rectangle)
            split_node = best.insert(rectangle, data)
            # Si el hijo se dividió, agregamos su nueva mitad
            if split_node:
                self.children.append(split_node)
                self.rectangles.append(split_node.compute_mbr())
            self.recalculate_mbr()
            if len(self.children) > self.max_entries:
                return self.split()
            return None

    def choose_subtree(self, rectangle):
        # Elegir el hijo cuyo MBR necesite menos aumento de área
        best = None
        best_increase = float('inf')
        for child, mbr in zip(self.children, self.rectangles):
            old_area = mbr.area()
            tmp = Rectangle(mbr.xmin, mbr.ymin, mbr.xmax, mbr.ymax)
            tmp.enlarge_to_contain(rectangle)
            increase = tmp.area() - old_area
            if increase < best_increase:
                best = child
                best_increase = increase
        return best

    def compute_mbr(self):
        return Rectangle.bounding(self.rectangles)

    def recalculate_mbr(self):
        if self.rectangles:
            mbr = Rectangle.bounding(self.rectangles)
            return mbr

    def split(self):
        # División lineal básica
        idx1, idx2 = self.linear_split()
        new_node = R_node(max_entries=self.max_entries, leaf=self.leaf)

        # Mover la mitad al nuevo nodo
        new_node.children = [self.children[i] for i in idx2]
        new_node.rectangles = [self.rectangles[i] for i in idx2]

        # Mantener mitad en nodo actual
        old_children = [self.children[i] for i in idx1]
        old_rects = [self.rectangles[i] for i in idx1]

        self.children = old_children
        self.rectangles = old_rects

        return new_node

    def linear_split(self):
        # Escoger dos entradas lejanas
        max_dist = -1
        idx1, idx2 = 0, 1
        for i in range(len(self.rectangles)):
            for j in range(i + 1, len(self.rectangles)):
                r1, r2 = self.rectangles[i], self.rectangles[j]
                dist = abs(r1.xmin - r2.xmin) + abs(r1.ymin - r2.ymin)
                if dist > max_dist:
                    max_dist = dist
                    idx1, idx2 = i, j
        # Dividir en dos grupos simples
        all_idx = list(range(len(self.rectangles)))
        all_idx.remove(idx2)
        return [idx1], [idx2] + all_idx[1:]
