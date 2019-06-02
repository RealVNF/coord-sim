"""

Flow Simulator parameters.
- Allows for clean and quick access to parameters from the flow simulator.
- Facilitates the quick changing of schedule decisions and
other parameters for the simulator.

"""


class SimulatorParams:
    def __init__(self, network, ing_nodes, sf_placement, sfc_list, sf_list, seed, schedule, inter_arr_mean=1.0,
                 flow_dr_mean=1.0, flow_dr_stdev=1.0, flow_size_shape=1.0):
        self.network = network
        self.sf_placement = sf_placement
        self.sfc_list = sfc_list
        self.sf_list = sf_list
        self.seed = seed
        self.inter_arr_mean = inter_arr_mean
        self.flow_dr_mean = flow_dr_mean
        self.flow_dr_stdev = flow_dr_stdev
        self.flow_size_shape = flow_size_shape
        self.schedule = schedule
        self.ing_nodes = ing_nodes
