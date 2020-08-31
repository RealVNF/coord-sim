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

    def __init__(self, params: SimulatorParams, lstm_predictor=None):
        self.params = params
        self.lstm_predictor = lstm_predictor
        self.last_flow_idx = {ing[0]: 0 for ing in self.params.ing_nodes}
        self.last_arrival_sum = {ing[0]: 0 for ing in self.params.ing_nodes}

    def predict_traffic(self, now, current_traffic=None):
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
            if self.lstm_predictor is None:
                # check for each flow if it will arrive before run_end; if so, add it to the prediction
                run_end = now + self.params.run_duration
                # Check to see if next flow arrival is before end of run
                while self.last_arrival_sum[node_id] < run_end:
                    flow_dr += self.params.flow_dr_list[node_id][self.last_flow_idx[node_id]]
                    self.last_arrival_sum[node_id] += self.params.flow_arrival_list[
                        node_id][self.last_flow_idx[node_id]]
                    self.last_flow_idx[node_id] += 1
            else:
                # Predict traffic using LSTM
                assert len(self.params.ing_nodes) == 1
                flow_dr = self.lstm_predictor.predict_traffic(current_traffic)

            # Update ingress traffic in metrics module
            self.params.metrics.metrics['run_total_requested_traffic'][node_id][sfc][ingress_sf] = flow_dr
