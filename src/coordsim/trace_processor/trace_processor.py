from coordsim.simulation.simulatorparams import SimulatorParams
from coordsim.simulation.flowsimulator import FlowSimulator
from simpy import Environment
import numpy as np
import logging
log = logging.getLogger(__name__)


class TraceProcessor():
    """
    Trace processor class
    """

    def __init__(self, params: SimulatorParams, env: Environment, trace: list, simulator: FlowSimulator):
        self.params = params
        self.env = env
        self.trace_index = 0
        self.prediction_trace_index = 0
        self.trace = trace
        self.simulator = simulator
        self.env.process(self.process_trace())

    def process_trace(self):
        """
        Changes the inter arrival mean during simulation
        The initial time is read from the the config file, so if the inter_arrival_time set in the trace CSV
        file does not start from 0, then the simulator will use the value set in sim_config

        """
        self.timeout = float(self.trace[self.trace_index]['time']) - self.env.now - 1
        self.timeout = np.clip(self.timeout, 0, None)
        inter_arrival_mean = self.trace[self.trace_index]['inter_arrival_mean']
        yield self.env.timeout(self.timeout)
        log.debug(f"Inter arrival mean changed to {inter_arrival_mean} at {self.env.now}")
        if 'node' in self.trace[self.trace_index]:
            node_id = self.trace[self.trace_index]['node']
            if inter_arrival_mean == 'None':
                self.params.inter_arr_mean[node_id] = None
            else:
                inter_arrival_mean = float(inter_arrival_mean)
                # old_mean = self.params.inter_arr_mean.get(node_id, None)
                self.params.inter_arr_mean[node_id] = inter_arrival_mean
                # Check for changing capacities in the trace file. Currently limited to only increasing capacites.
                if 'cap' in self.trace[self.trace_index]:
                    cap = self.trace[self.trace_index]["cap"]
                    self.params.network.nodes[node_id]["cap"] = float(cap)
                # if old_mean is None:
                #     self.env.process(self.simulator.init_arrival(node_id))
        else:
            inter_arrival_mean = float(inter_arrival_mean)
            self.params.update_single_inter_arr_mean(inter_arrival_mean)
        if self.trace_index < len(self.trace) - 1:
            self.trace_index += 1
            self.env.process(self.process_trace())
