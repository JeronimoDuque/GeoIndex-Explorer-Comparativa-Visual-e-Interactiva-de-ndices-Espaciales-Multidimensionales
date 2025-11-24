import time
import random
import tracemalloc
import gc
from statistics import mean

from .Grid_file import GridFile
from .R_tree import RTree
from Nodes.R_tree.Rectangle_R import Rectangle


def _get_rtree_leaf_stats(root):
    # devuelve (num_leaves, total_entries, list_entries_per_leaf)
    leaves = []

    def walk(node):
        if node.leaf:
            leaves.append(len(node.children))
        else:
            for child in node.children:
                walk(child)

    walk(root)
    if not leaves:
        return 0, 0, []
    return len(leaves), sum(leaves), leaves


def benchmark_gridfile(sizes, capacity=4):
    """Inserta puntos aleatorios y devuelve métricas para cada tamaño.
    Retorna dict con listas: sizes, times, mem_peaks, load_factors, avg_occupancies, num_cells
    """
    sizes = list(sizes)
    times = []
    mem_peaks = []
    load_factors = []
    avg_occupancies = []
    num_cells = []

    for n in sizes:
        gc.collect()
        tracemalloc.start()
        start = time.perf_counter()

        gf = GridFile(capacity=capacity)
        for _ in range(n):
            x = random.random()
            y = random.random()
            gf.insert(x, y)

        elapsed = time.perf_counter() - start
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # load factor: avg occupancy / capacity
        total_buckets = len(gf.directory)
        avg_occ = (n / total_buckets) if total_buckets > 0 else 0
        lf = avg_occ / capacity if capacity > 0 else 0

        times.append(elapsed)
        mem_peaks.append(peak)
        load_factors.append(lf)
        avg_occupancies.append(avg_occ)
        num_cells.append(total_buckets)

    return {
        'sizes': sizes,
        'times': times,
        'mem_peaks': mem_peaks,
        'load_factors': load_factors,
        'avg_occupancies': avg_occupancies,
        'num_cells': num_cells
    }


def benchmark_rtree(sizes, max_entries=4, rect_size=0.001, center=(6.24, -75.58)):
    """Inserta rectángulos pequeños alrededor del centro y devuelve métricas.
    Retorna dict con sizes, times, mem_peaks, load_factors, avg_entries_per_leaf, num_leaves
    """
    sizes = list(sizes)
    times = []
    mem_peaks = []
    load_factors = []
    avg_entries = []
    num_leaves_list = []

    for n in sizes:
        gc.collect()
        tracemalloc.start()
        start = time.perf_counter()

        tree = RTree(max_entries=max_entries)
        cx, cy = center
        for i in range(n):
            # distribuir aleatoriamente alrededor del centro
            lon = cx + (random.random() - 0.5) * 0.1
            lat = cy + (random.random() - 0.5) * 0.1
            r = Rectangle(lon, lat, lon + rect_size, lat + rect_size)
            data = {"id": i, "mbr": r}
            tree.insert(r, data)

        elapsed = time.perf_counter() - start
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # obtener estadísticas de hojas
        num_leaves, total_entries, leaves = _get_rtree_leaf_stats(tree.root)
        avg_ent = (total_entries / num_leaves) if num_leaves > 0 else 0
        lf = avg_ent / max_entries if max_entries > 0 else 0

        times.append(elapsed)
        mem_peaks.append(peak)
        load_factors.append(lf)
        avg_entries.append(avg_ent)
        num_leaves_list.append(num_leaves)

    return {
        'sizes': sizes,
        'times': times,
        'mem_peaks': mem_peaks,
        'load_factors': load_factors,
        'avg_entries': avg_entries,
        'num_leaves': num_leaves_list
    }


def analyze_gridfile_instance(gf: GridFile):
    """Analiza un GridFile existente y devuelve métricas similares a benchmark_gridfile para un único tamaño."""
    import tracemalloc, time
    gc.collect()
    tracemalloc.start()
    start = time.perf_counter()

    # computar número total de puntos
    total_points = 0
    for bucket in gf.directory.values():
        # Bucket.points es la lista de puntos
        try:
            total_points += len(bucket.points)
        except Exception:
            # estructura inesperada
            pass

    elapsed = time.perf_counter() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    total_buckets = len(gf.directory)
    avg_occ = (total_points / total_buckets) if total_buckets > 0 else 0
    lf = avg_occ / gf.capacity if getattr(gf, 'capacity', 1) > 0 else 0

    return {
        'sizes': [total_points],
        'times': [elapsed],
        'mem_peaks': [peak],
        'load_factors': [lf],
        'avg_occupancies': [avg_occ],
        'num_cells': [total_buckets]
    }


def analyze_rtree_instance(tree: RTree):
    """Analiza un RTree existente y devuelve métricas similares a benchmark_rtree para un único tamaño."""
    import tracemalloc, time
    gc.collect()
    tracemalloc.start()
    start = time.perf_counter()

    # contar entradas totales y hojas
    num_leaves, total_entries, leaves = _get_rtree_leaf_stats(tree.root)

    elapsed = time.perf_counter() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    max_entries = getattr(tree.root, 'max_entries', 4)
    avg_ent = (total_entries / num_leaves) if num_leaves > 0 else 0
    lf = avg_ent / max_entries if max_entries > 0 else 0

    return {
        'sizes': [total_entries],
        'times': [elapsed],
        'mem_peaks': [peak],
        'load_factors': [lf],
        'avg_entries': [avg_ent],
        'num_leaves': [num_leaves]
    }
