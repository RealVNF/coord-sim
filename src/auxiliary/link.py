import copy

class Link:
    def __init__(self, a: str, b: str, **kwargs):
        self.edge = (a, b)
        self.attributes = {}
        for key, value in kwargs.items():
            self.attributes[key] = copy.deepcopy(value)

    def __eq__(self, other):
        if isinstance(other, Link):
            return (self.edge[0] == other.edge[0] and self.edge[1] == other.edge[1]) \
                   or (self.edge[0] == other.edge[1] and self.edge[1] == other.edge[0])
        return False

    def __hash__(self):
        """
        Simple commutative property
        """
        return hash(self.edge[0]) ^ hash(self.edge[1])

    def __setitem__(self, key, item: str):
        if key == 0 or key == 1:
            raise KeyError('Cannot set nodes.')
        else:
            self.attributes[key] = item

    def __getitem__(self, key):
        if key == 0 or key == 1:
            return self.edge[key]
        else:
            return self.attributes[key]

    def __repr__(self):
        return f'({self.edge[0]}, {self.edge[1]})'