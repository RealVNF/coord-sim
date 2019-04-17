class Node:

    def __init__(self, node_id, name, node_type, cap):
        self.node_id = node_id
        self.name = name
        self.cap = cap
        # Type of node. For now it is either "Normal" or "Ingress"
        self.node_type = node_type
        self.available_sf = {}
