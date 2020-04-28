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
        self.last_dr_idx = {ing[0]: 0 for ing in self.params.ing_nodes}

    def predict_traffic(self):
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
            # get sfc_id - currently assumes one SFC
            sfc_ids = self.params.sfc_list.keys()
            sfc_ids = [*sfc_ids]  # New unpacking trick in python 3.5+
            sfc = sfc_ids[0]
            ingress_sf = self.params.sfc_list[sfc][0]
            flow_dr = 0
            # DDPG Weirdly calls `init()` twice which causes the second (more important) init call to
            # predict 0 traffic
            if self.last_dr_idx[node_id] == len(self.params.flow_dr_list[node_id]):
                self.last_dr_idx[node_id] = 0
            for dr in self.params.flow_dr_list[node_id][self.last_dr_idx[node_id]:]:
                flow_dr += dr
                self.last_dr_idx[node_id] += 1

            # Update ingress traffic in metrics module
            self.params.metrics.metrics['run_total_requested_traffic'][node_id][sfc][ingress_sf] = flow_dr
