from coordsim.simulation.simulatorparams import SimulatorParams
from collections import defaultdict
# from math import ceil
# import numpy as np
# import random
import logging
log = logging.getLogger(__name__)


class TrafficPredictor():
    """
    Traffic Predictor class
    Updates traffic dict in metrics module to show upcoming traffic at ingress node.
    """

    def __init__(self, params: SimulatorParams):
        self.params = params
        # point to the position in the flow data list from where to start next prediction
        self.last_flow_idx = {ing[0]: 0 for ing in self.params.ing_nodes}

    def predict_traffic(self, now):
        """
        Calculates the upcoming traffic (starting at now) at ingress nodes based on the current inter_arrival_mean
        Currently supports single SFC
        """
        # reset total requested traffic
        self.params.metrics.metrics['run_total_requested_traffic'] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(float)))

        # Add predicted data rate to ingress SFCs
        for node in self.params.ing_nodes:
            # get node_id
            node_id = node[0]
            # get sfc_id - currently assumes one SFC
            sfc = list(self.params.sfc_list.keys())[0]
            ingress_sf = self.params.sfc_list[sfc][0]
            flow_dr = 0
            # FIXME: DDPG Weirdly calls `init()` twice which causes the second (more important) init call to
            # predict 0 traffic
            if self.last_flow_idx[node_id] == len(self.params.flow_dr_list[node_id]):
                self.last_flow_idx[node_id] = 0

            # add dr of all flows that will arrive in the next run
            # check for each flow if it will arrive before run_end; if so, add it to the prediction
            run_end = now + self.params.run_duration
            # slice to idx+1 to include the inter-arrival time of the current flow at idx
            next_flow_arrives = sum(self.params.flow_arrival_list[node_id][0:self.last_flow_idx[node_id]+1])
            while next_flow_arrives < run_end:
                flow_dr += self.params.flow_dr_list[node_id][self.last_flow_idx[node_id]]
                self.last_flow_idx[node_id] += 1
                next_flow_arrives = sum(self.params.flow_arrival_list[node_id][0:self.last_flow_idx[node_id]+1])

            # Update ingress traffic in metrics module
            self.params.metrics.metrics['run_total_requested_traffic'][node_id][sfc][ingress_sf] = flow_dr
