"""

Flow constructor class

"""


class Flow:

    def __init__(self, flow_id, sfc, dr, size, status=None, rate=None,
                 destination=None, current_sf=None, current_node_id=None, current_position=0, end2end_delay=0.0):

        # DR is in Mbits/s
        # Duration is in ms
        # Size of flow is in Mbits

        self.flow_id = flow_id
        self.sfc = sfc
        self.status = status
        self.dr = dr
        self.size = size
        self.destination = destination
        self.current_sf = current_sf
        self.current_node_id = current_node_id
        self.duration = (float(size) / float(dr)) * 1000  # Converted flow duration to ms
        # Current flow position within the SFC
        self.current_position = current_position
        # End to end delay of the flow, used for metrics
        self.end2end_delay = end2end_delay
