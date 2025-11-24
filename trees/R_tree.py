from Nodes.R_tree.Rectangle_R import Rectangle
from Nodes.R_node import R_node
from Nodes.R_tree.Geometry_Utils import polygon_mbr, rect_polygon_intersection

class RTree:
    def __init__(self, max_entries=4):
        self.root = R_node(max_entries=max_entries, leaf=True)

    def insert(self, rect, data=None):
        split = self.root.insert(rect, data)
        if split:
            new_root = R_node(max_entries=self.root.max_entries, leaf=False)
            new_root.children = [self.root, split]
            new_root.rectangles = [self.root.compute_mbr(), split.compute_mbr()]
            self.root = new_root

    def search(self, query_rect):
        # devuelve lista de tuplas (data, rect) para las hojas
        return self._search_node(self.root, query_rect)

    def _search_node(self, node, query_rect):
        result = []
        for child, rect in zip(node.children, node.rectangles):
            if rect.intersects(query_rect):
                if node.leaf:
                    # devolver tanto el dato como su rectángulo asociado
                    result.append((child, rect))
                else:
                    result.extend(self._search_node(child, query_rect))
        return result
    
    # -------------------------------------------
    #     CONSULTA POR INTERSECCIÓN DE POLÍGONO
    # -------------------------------------------
    def intersect_polygon(self, polygon):
        # 1. MBR del polígono
        mbr_vals = polygon_mbr(polygon)
        # polygon_mbr puede devolver una tupla (xmin, ymin, xmax, ymax) o un objeto con .bounds
        if isinstance(mbr_vals, tuple) and len(mbr_vals) == 4:
            xmin, ymin, xmax, ymax = mbr_vals
            mbr = Rectangle(xmin, ymin, xmax, ymax)
        else:
            # si viene algo con .bounds
            try:
                xmin, ymin, xmax, ymax = mbr_vals
                mbr = Rectangle(xmin, ymin, xmax, ymax)
            except Exception:
                raise TypeError('polygon_mbr debe devolver (xmin,ymin,xmax,ymax)')

        # 2. Búsqueda rápida con el R-Tree
        candidatos = self.search(mbr)

        # 3. Filtrado exacto: candidatos es lista de (data, rect)
        resultados = []
        for data_obj, rect in candidatos:
            # compatibilidad: si el dato almacenado incluye su propia MBR bajo 'mbr', úsala
            try:
                candidate_rect = None
                if isinstance(data_obj, dict) and 'mbr' in data_obj:
                    candidate_rect = data_obj['mbr']
                else:
                    candidate_rect = rect
                if rect_polygon_intersection(candidate_rect, polygon):
                    # devolver tanto el dato como la MBR utilizada para facilitar la presentación
                    resultados.append({'data': data_obj, 'rect': candidate_rect})
            except Exception:
                # en caso de error con el objeto, omitirlo
                continue

        return resultados