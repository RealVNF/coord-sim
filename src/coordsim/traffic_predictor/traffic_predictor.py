from coordsim.simulation.simulatorparams import SimulatorParams
from collections import defaultdict
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
        # init dicts
        self.flow_drs = {}
        self.flow_sizes = {}
        self.arrival_list = {}

    def gen_flow_lists(self):
        """
        Generate flow arrival lists for the simulator based on 'predicted' inter_arr_mean
        """
        # reset total requested traffic
        self.params.metrics.metrics['run_total_requested_traffic'] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(float)))

        # Add predicted data rate to ingress SFCs
        for node in self.params.ing_nodes:
            # get node_id
            node_id = node[0]
            # reset lists
            self.arrival_list[node_id] = []
            self.flow_drs[node_id] = []
            self.flow_sizes[node_id] = []
            inter_arr_mean = None

            # Poisson arrival -> exponential distributed inter-arrival time
            while sum(self.arrival_list[node_id]) <= self.params.run_duration:
                if self.params.deterministic_arrival:
                    inter_arr_mean = self.params.predicted_inter_arr_mean[node_id]
                else:
                    inter_arr_mean = random.expovariate(lambd=1.0/self.params.predicted_inter_arr_mean[node_id])
                # Sometimes adding the generated inter_arr_mean can still make sum > run_duration
                if sum(self.arrival_list[node_id]) + inter_arr_mean > self.params.run_duration:
                    break
                self.arrival_list[node_id].append(inter_arr_mean)
                if self.params.deterministic_size:
                    flow_size = self.params.flow_size_shape
                else:
                    # heavy-tail flow size
                    flow_size = np.random.pareto(self.params.flow_size_shape) + 1
                flow_dr = np.random.normal(self.params.flow_dr_mean, self.params.flow_dr_stdev)
                if flow_dr <= 0.00 or flow_size <= 0.00:
                    continue
                self.flow_sizes[node_id].append(flow_size)
                self.flow_drs[node_id].append(flow_dr)

        # Update lists in sim param
        self.params.arrival_list = self.arrival_list
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

    def predict_traffic(self):
        """
        Calculates the upcoming traffic at ingress nodes based on the current inter_arrival_mean
        Currently supports single SFC
        """
        self.gen_flow_lists()
        self.update_metrics()
