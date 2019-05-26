"""

Flow simulator Params class. This facilitates the quick changing of schedule decisions and
other parameters for the simulator.

"""


class SimulatorParams:
    def __init__(self, network, sf_placement, sfc_list, sf_list, seed, schedule, inter_arr_mean=1.0,
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
