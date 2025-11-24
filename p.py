from trees.R_tree import RTree
from Nodes.R_tree.Rectangle_R import Rectangle
from Nodes.R_tree.Polygon import Polygon
from Nodes.R_tree.Point import Point
tree = RTree()

# Insertar rectángulos
for i in range(8):
    r = Rectangle(i, i, i+2, i+3)
    data = {"id": i, "mbr": r}
    tree.insert(r, data)

# Polígono irregular
poly = Polygon([
    Point(1, 0),
    Point(6, 1),
    Point(5, 7),
    Point(2, 5)
])

# Consulta espacial
res = tree.intersect_polygon(poly)

for r in res:
    print("Interseca:", r["id"])