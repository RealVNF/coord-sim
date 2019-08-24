"""

Flow class.
This identifies the flow and its parameters.
TODO: Add get/set methods

"""


class Flow:

    def __init__(self,
                 flow_id,
                 sfc,
                 sfc_components,
                 dr,
                 size,
                 creation_time,
                 destination_id=None,
                 current_sf=None,
                 current_node_id=None,
                 current_position=0,
                 end2end_delay=0.0,
                 path_delay=0.0):

        # Flow ID: Unique ID string
        self.flow_id = flow_id
        # The requested SFC id
        self.sfc = sfc
        # The requested SFC id
        self.sfc_components = sfc_components
        # The requested data rate in MiB (Mebibyte = 2^20 Byte) per second (MiB/s)
        self.dr = dr
        # The size of the flow in MiB (Mebibyte = 2^20 Byte)
        self.size = size
        # The current SF that the flow is being processed in.
        self.current_sf = current_sf
        # The node where the flows head currently resides at
        self.current_node_id = current_node_id
        # The specified egress node of the flow. The flow will depart at the egress node. Might be non-existent.
        self.destination_id = destination_id
        # The duration of the flow calculated in ms.
        self.duration = (float(size) / float(dr)) * 1000  # Converted flow duration to ms
        # Current flow position within the SFC
        self.current_position = current_position
        # Path delay of the flow. Sum of all link delays the flow has experienced so far. Used for metrics
        self.path_delay = path_delay
        # End to end delay of the flow, used for metrics
        self.end2end_delay = end2end_delay
        # FLow creation time
        self.creation_time = creation_time
        # Flow destination
        self.destination_id = destination_id
        # Flow user data, a dict to hold abitrary data. External algorithms should use this to enrich flow information
        self.user_data = {}

    def __setitem__(self, key, item):
        self.user_data[key] = item

    def __getitem__(self, key):
        return self.user_data[key]

    def is_processed(self):
        return self.current_position == len(self.sfc_components)
