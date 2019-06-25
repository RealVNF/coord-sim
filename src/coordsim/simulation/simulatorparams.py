"""

Flow Simulator parameters.
- Allows for clean and quick access to parameters from the flow simulator.
- Facilitates the quick changing of schedule decisions and
other parameters for the simulator.

"""

import yaml


class SimulatorParams:
    def __init__(self, network, ing_nodes, sfc_list, sf_list, config_file, seed, schedule={}, sf_placement={}):
        # Seed for the random generator: int
        self.seed = seed
        # NetworkX network object: DiGraph
        self.network = network
        # Ingress nodes of the network (nodes at which flows arrive): list
        self.ing_nodes = ing_nodes
        # List of available SFCs and their child SFs: defaultdict(None)
        self.sfc_list = sfc_list
        # List of every SF and it's properties (e.g. processing_delay): defaultdict(None)
        self.sf_list = sf_list

        # read dummy placement and schedule if specified
        # Flow forwarding schedule: dict
        self.schedule = schedule
        # Placement of SFs in each node: defaultdict(list)
        self.sf_placement = sf_placement

        # read config params from file
        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        # Flow interarrival exponential distribution mean: float
        self.inter_arr_mean = config['inter_arrival_mean']
        # Flow data rate normal distribution mean: float
        self.flow_dr_mean = config['flow_dr_mean']
        # Flow data rate normal distribution standard deviation: float
        self.flow_dr_stdev = config['flow_dr_stdev']
        # Flow size Pareto heavy-tail distribtution shape: float
        self.flow_size_shape = config['flow_size_shape']
        # if deterministic = True, the simulator reinterprets and uses inter_arrival_mean and flow_size_shape as fixed
        # deterministic values rather than means of a random distribution
        self.deterministic = config['deterministic']

    # string representation for logging
    def __str__(self):
        params_str = "Simulator parameters: "
        params_str += "seed: {}\n".format(self.seed)
        params_str += "inter_arr_mean: {}\n".format(self.inter_arr_mean)
        params_str += "flow_dr_mean: {}\n".format(self.flow_dr_mean)
        params_str += "flow_dr_stdv: {}\n".format(self.flow_dr_stdev)
        params_str += "flow_size_shape: {}".format(self.flow_size_shape)
        return params_str
