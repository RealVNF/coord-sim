"""

Flow Simulator parameters.
- Allows for clean and quick access to parameters from the flow simulator.
- Facilitates the quick changing of schedule decisions and
other parameters for the simulator.

"""


class SimulatorParams:
    def __init__(self, network, ing_nodes, sfc_list, sf_list, seed, inter_arr_mean=1.0,
                 flow_dr_mean=1.0, flow_dr_stdev=1.0, flow_size_shape=1.0, schedule={}, sf_placement={}):

        # NetworkX network object: DiGraph
        self.network = network
        # Ingress nodes of the network (nodes at which flows arrive): list
        self.ing_nodes = ing_nodes
        # Placement of SFs in each node: defaultdict(list)
        self.sf_placement = sf_placement
        # List of available SFCs and their child SFs: defaultdict(None)
        self.sfc_list = sfc_list
        # List of every SF and it's properties (e.g. processing_delay): defaultdict(None)
        self.sf_list = sf_list
        # Seed for the random generator: int
        self.seed = seed
        # Flow interarrival exponential distribution mean: float
        self.inter_arr_mean = inter_arr_mean
        # Flow data rate normal distribution mean: float
        self.flow_dr_mean = flow_dr_mean
        # Flow data rate normal distribution standard deviation: float
        self.flow_dr_stdev = flow_dr_stdev
        # Flow size Pareto heavy-tail distribtution shape: float
        self.flow_size_shape = flow_size_shape
        # Flow forwarding schedule: dict
        self.schedule = schedule

    # string representation for logging
    def __str__(self):
        params_str = "Simulator parameters: "
        params_str += "seed: {}\n".format(self.seed)
        params_str += "inter_arr_mean: {}\n".format(self.inter_arr_mean)
        params_str += "flow_dr_mean: {}\n".format(self.flow_dr_mean)
        params_str += "flow_dr_stdv: {}\n".format(self.flow_dr_stdev)
        params_str += "flow_size_shape: {}".format(self.flow_size_shape)
        return params_str
