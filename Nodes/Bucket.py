class Bucket:
    def __init__(self, capacity=4):
        self.points = []
        self.capacity = capacity

    def insert(self, point):
        if len(self.points) < self.capacity:
            self.points.append(point)
            return True
        return False

    def __repr__(self):
        return f"Bucket({self.points})"

