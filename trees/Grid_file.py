from Nodes.Bucket import Bucket

class GridFile:
    def __init__(self, capacity=4):
        # Límites iniciales (una sola celda)
        self.x_splits = [0, 1]  # rangos de 0 a 1
        self.y_splits = [0, 1]

        self.capacity = capacity

        # Diccionario (i,j) → bucket
        self.directory = {(0, 0): Bucket(capacity)}

    # --- utilidades internas ---
    def _find_cell(self, x, y):
        """Encuentra la celda (i,j) del grid donde cae el punto"""
        i = max([k for k in range(len(self.x_splits)-1) if self.x_splits[k] <= x])
        j = max([k for k in range(len(self.y_splits)-1) if self.y_splits[k] <= y])
        return i, j

    def _split_x(self, i):
        """Divide la columna i en dos"""
        mid = (self.x_splits[i] + self.x_splits[i+1]) / 2
        self.x_splits.insert(i+1, mid)

        # redistribuir buckets
        new_directory = {}
        for (cx, cy), bucket in self.directory.items():
            if cx == i:
                # La celda se divide en dos
                b1 = Bucket(self.capacity)
                b2 = Bucket(self.capacity)
                for (x, y) in bucket.points:
                    if x < mid:
                        b1.insert((x, y))
                    else:
                        b2.insert((x, y))
                new_directory[(cx, cy)] = b1
                new_directory[(cx+1, cy)] = b2
            elif cx > i:
                # correr índices hacia la derecha
                new_directory[(cx+1, cy)] = bucket
            else:
                new_directory[(cx, cy)] = bucket

        self.directory = new_directory

    def _split_y(self, j):
        """Divide la fila j en dos"""
        mid = (self.y_splits[j] + self.y_splits[j+1]) / 2
        self.y_splits.insert(j+1, mid)

        new_directory = {}
        for (cx, cy), bucket in self.directory.items():
            if cy == j:
                b1 = Bucket(self.capacity)
                b2 = Bucket(self.capacity)
                for (x, y) in bucket.points:
                    if y < mid:
                        b1.insert((x, y))
                    else:
                        b2.insert((x, y))
                new_directory[(cx, cy)] = b1
                new_directory[(cx, cy+1)] = b2
            elif cy > j:
                new_directory[(cx, cy+1)] = bucket
            else:
                new_directory[(cx, cy)] = bucket

        self.directory = new_directory

    # --- operaciones principales ---
    def insert(self, x, y):
        i, j = self._find_cell(x, y)
        bucket = self.directory[(i, j)]

        if bucket.insert((x, y)):
            return

        # Bucket lleno → dividir
        width = self.x_splits[i+1] - self.x_splits[i]
        height = self.y_splits[j+1] - self.y_splits[j]

        # dividir la dimensión más grande
        if width >= height:
            self._split_x(i)
        else:
            self._split_y(j)

        # reintentar la inserción
        self.insert(x, y)

    def range_query(self, xmin, xmax, ymin, ymax):
        """Busca puntos dentro de un rectángulo"""
        result = []
        for (i, j), bucket in self.directory.items():
            # calcular límites reales de la celda
            x0, x1 = self.x_splits[i], self.x_splits[i+1]
            y0, y1 = self.y_splits[j], self.y_splits[j+1]

            # si no intersecta, continuar
            if x1 < xmin or x0 > xmax or y1 < ymin or y0 > ymax:
                continue

            # revisar puntos
            for (x, y) in bucket.points:
                if xmin <= x <= xmax and ymin <= y <= ymax:
                    result.append((x, y))
        return result

    def print_grid(self):
        print("Splits X:", self.x_splits)
        print("Splits Y:", self.y_splits)
        print("Directory:")
        for key, bucket in self.directory.items():
            print(f"  Cell {key}: {bucket}")
