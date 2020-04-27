from coordsim.simulation.simulatorparams import SimulatorParams
from collections import defaultdict
from math import ceil
import numpy as np
import random
import logging
log = logging.getLogger(__name__)


class TrafficPredictor():
    """
    Traffic Predictor class
    Updates traffic dict in metrics module to show upcoming traffic at ingress node.
    """

    def __init__(self, params: SimulatorParams):
        self.params = params
        self.flow_drs = {}
        self.flow_sizes = {}
        self.arrival_list = {}

    def gen_flow_lists(self):
        """
        Calculates the upcoming traffic at ingress nodes based on the current inter_arrival_mean
        Currently supports single SFC
        """
        # reset total requested traffic
        self.params.metrics.metrics['run_total_requested_traffic'] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(float)))

        # Add predicted data rate to ingress SFCs
        for node in self.params.ing_nodes:
            # get node_id
            node_id = node[0]

            inter_arr_mean = None
            flow_dr = np.random.normal(self.params.flow_dr_mean, self.params.flow_dr_stdev)

            # if self.params.deterministic_arrival:
            #     # inter_arr_mean = self.params.predicted_inter_arr_mean[node_id]
            # else:
            inter_arr_times = []
            # Poisson arrival -> exponential distributed inter-arrival time
            while sum(inter_arr_times) <= self.params.run_duration:
                if self.params.deterministic_arrival:
                    inter_arr_mean = self.params.predicted_inter_arr_mean[node_id]
                else:
                    inter_arr_mean = random.expovariate(lambd=1.0/self.params.predicted_inter_arr_mean[node_id])
                inter_arr_times.append(inter_arr_mean)
                # inter_arr_mean = np.mean(inter_arr_times)
            # Calculate flow count for each ingress node
            flow_dr = 0.0
            # number_of_flows = self.params.run_duration / inter_arr_mean

            # Predict data rate for expected number of flows
            for _ in inter_arr_times:
                if self.params.deterministic_size:
                    self.flow_sizes[node_id].append(self.params.flow_size_shape)
                else:
                    # heavy-tail flow size
                    self.flow_sizes[node_id].append(np.random.pareto(self.params.flow_size_shape) + 1)
                self.flow_
                flow_dr += np.random.normal(self.params.flow_dr_mean, self.params.flow_dr_stdev)

            # Update ingress traffic in metrics module
            self.params.arrival_list = inter_arr_times
            self.params.flow_drs = self.flow_drs
            self.params.flow_sizes = self.flow_sizes

    def update_metrics(self):
        for node in self.params.ing_nodes:
            # get node_id
            node_id = node[0]
            # get sfc_id - currently assumes one SFC
            sfc_ids = self.params.sfc_list.keys()
            sfc_ids = [*sfc_ids]  # New unpacking trick in python 3.5+
            sfc = sfc_ids[0]
            ingress_sf = self.params.sfc_list[sfc][0] 
            flow_dr = sum(self.flow_drs[node_id])
            self.params.metrics.metrics['run_total_requested_traffic'][node_id][sfc][ingress_sf] = flow_dr
