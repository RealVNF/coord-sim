"""

Flow class.
This identifies the flow and its parameters.
TODO: Add get/set methods

"""


class Flow:

    def __init__(self, flow_id, sfc, dr, size, creation_time, destination=None, egress_node_id=None, current_sf=None,
                 current_node_id=None, current_position=0, end2end_delay=0.0, ttl=50):

        # Flow ID: Unique ID string
        self.flow_id = flow_id
        # The requested SFC
        self.sfc = sfc
        # The requested data rate in Megabits per second (Mbit/s)
        self.dr = dr
        # The size of the flow in Megabit (Mb)
        self.size = size
        # The current SF that the flow is being processed in.
        self.current_sf = current_sf
        # The current node that the flow is being processed in
        self.current_node_id = current_node_id
        # The specified ingress node of the flow. The flow will spawn at the ingress node.
        self.ingress_node_id = current_node_id
        # The specified egress node of the flow. The flow will depart at the egress node. Might be non-existent.
        self.egress_node_id = egress_node_id
        # The duration of the flow calculated in ms.
        self.duration = (float(size) / float(dr)) * 1000  # Converted flow duration to ms
        # Current flow position within the SFC
        self.current_position = current_position
        # End to end delay of the flow, used for metrics
        self.end2end_delay = end2end_delay
        # Specify a flow TTL
        self.ttl = ttl
        # Flow creation time
        self.creation_time = creation_time
        # Flag whether the flow departed
        self.departed = False
        self.forward_to_eg = False
