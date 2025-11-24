# ================================
# Geometry Utils para R-Tree
# Compatibiliza la API con Shapely o con la clase Polygon personalizada
# ================================

def rect_bounds(rect):
    return rect.xmin, rect.ymin, rect.xmax, rect.ymax


def point_in_rect(px, py, rect):
    xmin, ymin, xmax, ymax = rect_bounds(rect)
    return (xmin <= px <= xmax) and (ymin <= py <= ymax)


def rects_intersect(r1, r2):
    a_xmin, a_ymin, a_xmax, a_ymax = rect_bounds(r1)
    b_xmin, b_ymin, b_xmax, b_ymax = rect_bounds(r2)

    return not (a_xmax < b_xmin or
                a_xmin > b_xmax or
                a_ymax < b_ymin or
                a_ymin > b_ymax)


# ---- Helpers para polígonos que no sean Shapely
def _coords_from_polygon(polygon):
    # Shapely Polygon has .exterior.coords
    if hasattr(polygon, 'exterior') and hasattr(polygon.exterior, 'coords'):
        return list(polygon.exterior.coords)

    # Custom Polygon in this repo: has to_tuples() or .points
    if hasattr(polygon, 'to_tuples'):
        return polygon.to_tuples()

    if hasattr(polygon, 'points'):
        return [(p.x, p.y) for p in polygon.points]

    raise TypeError('Objeto polígono no soportado')


def polygon_mbr(polygon):
    """
    Retorna (xmin, ymin, xmax, ymax)
    Soporta objetos Shapely o la clase Polygon personalizada del proyecto.
    """
    if hasattr(polygon, 'bounds'):
        return polygon.bounds

    coords = _coords_from_polygon(polygon)
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return min(xs), min(ys), max(xs), max(ys)


def _point_in_polygon(px, py, poly_coords):
    # Ray casting algorithm
    inside = False
    n = len(poly_coords)
    for i in range(n):
        x1, y1 = poly_coords[i]
        x2, y2 = poly_coords[(i + 1) % n]
        if ((y1 > py) != (y2 > py)) and (
            px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-12) + x1
        ):
            inside = not inside
    return inside


def _segments_intersect(a1, a2, b1, b2):
    # Helper for segment intersection using orientation
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    o1 = orient(a1, a2, b1)
    o2 = orient(a1, a2, b2)
    o3 = orient(b1, b2, a1)
    o4 = orient(b1, b2, a2)

    if o1 == 0 and min(a1[0], a2[0]) <= b1[0] <= max(a1[0], a2[0]) and min(a1[1], a2[1]) <= b1[1] <= max(a1[1], a2[1]):
        return True
    if o2 == 0 and min(a1[0], a2[0]) <= b2[0] <= max(a1[0], a2[0]) and min(a1[1], a2[1]) <= b2[1] <= max(a1[1], a2[1]):
        return True
    if o3 == 0 and min(b1[0], b2[0]) <= a1[0] <= max(b1[0], b2[0]) and min(b1[1], b2[1]) <= a1[1] <= max(b1[1], b2[1]):
        return True
    if o4 == 0 and min(b1[0], b2[0]) <= a2[0] <= max(b1[0], b2[0]) and min(b1[1], b2[1]) <= a2[1] <= max(b1[1], b2[1]):
        return True

    return (o1 * o2 < 0) and (o3 * o4 < 0)


def rect_polygon_intersection(rect, polygon):
    xmin, ymin, xmax, ymax = rect_bounds(rect)

    # 1. Descarta rápido usando bounding box del polígono
    pminx, pminy, pmaxx, pmaxy = polygon_mbr(polygon)
    if (pmaxx < xmin or pminx > xmax or
        pmaxy < ymin or pminy > ymax):
        return False

    coords = _coords_from_polygon(polygon)

    # 2. Comprueba intersección de aristas del polígono con aristas del rect
    rect_edges = [
        ((xmin, ymin), (xmax, ymin)),
        ((xmax, ymin), (xmax, ymax)),
        ((xmax, ymax), (xmin, ymax)),
        ((xmin, ymax), (xmin, ymin)),
    ]

    for i in range(len(coords)):
        a1 = coords[i]
        a2 = coords[(i + 1) % len(coords)]
        for b1, b2 in rect_edges:
            if _segments_intersect(a1, a2, b1, b2):
                return True

    # 3. Un punto del polígono dentro del rect
    for px, py in coords:
        if point_in_rect(px, py, rect):
            return True

    # 4. Un punto del rect dentro del polígono
    rect_pts = [
        (xmin, ymin),
        (xmax, ymin),
        (xmax, ymax),
        (xmin, ymax)
    ]

    for rx, ry in rect_pts:
        if _point_in_polygon(rx, ry, coords):
            return True

    return False


def enlarge_rect(rect, other):
    rect.xmin = min(rect.xmin, other.xmin)
    rect.ymin = min(rect.ymin, other.ymin)
    rect.xmax = max(rect.xmax, other.xmax)
    rect.ymax = max(rect.ymax, other.ymax)
    return rect


def rect_area(rect):
    return (rect.xmax - rect.xmin) * (rect.ymax - rect.ymin)


def area_increase(rect, other):
    current = rect_area(rect)

    new_xmin = min(rect.xmin, other.xmin)
    new_ymin = min(rect.ymin, other.ymin)
    new_xmax = max(rect.xmax, other.xmax)
    new_ymax = max(rect.ymax, other.ymax)

    new_area = (new_xmax - new_xmin) * (new_ymax - new_ymin)
    return new_area - current
