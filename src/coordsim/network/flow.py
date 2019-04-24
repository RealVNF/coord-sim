class Flow:

    def __init__(self, flow_id, sfc, dr, size, status=None, rate=None,
                 destination=None, current_sf=None, current_node_id=None):
        self.flow_id = flow_id
        self.sfc = sfc
        self.status = status
        self.dr = dr
        self.size = size
        self.destination = destination
        self.current_sf = current_sf
        self.current_node_id = current_node_id
        self.duration = float(size) / float(dr)
