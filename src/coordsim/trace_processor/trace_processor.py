from coordsim.simulation.simulatorparams import SimulatorParams
from simpy import Environment
import logging
log = logging.getLogger(__name__)


class TraceProcessor():
    """
    Trace processor class
    """

    def __init__(self, params: SimulatorParams, env: Environment, trace: list,):
        self.params = params
        self.env = env
        self.trace_index = 0
        self.trace = trace
        self.env.process(self.change_inter_arrival_time())

    def change_inter_arrival_time(self):
        """
        Changes the inter arrival mean during simulation
        """
        self.timeout = float(self.trace[self.trace_index]['time']) - self.env.now
        inter_arrival_mean = float(self.trace[self.trace_index]['inter_arrival_mean'])
        yield self.env.timeout(self.timeout)
        log.debug(f"Inter arrival mean changed to {inter_arrival_mean} at {self.env.now}")
        self.params.inter_arr_mean = inter_arrival_mean
        if self.trace_index < len(self.trace)-1:
            self.trace_index += 1
            self.env.process(self.change_inter_arrival_time())
