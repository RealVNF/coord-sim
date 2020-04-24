from coordsim.simulation.simulatorparams import SimulatorParams
from collections import defaultdict
from math import ceil
import numpy as np
import logging
log = logging.getLogger(__name__)


class TrafficPredictor():
    """
    Traffic Predictor class
    Updates traffic dict in metrics module to show upcoming traffic at ingress node.
    """

    def __init__(self, params: SimulatorParams):
        self.params = params

    def predict_traffic(self):
        """
        Calculates the upcoming traffic at ingress nodes based on the current inter_arrival_mean
        Currently only supports deterministic traffic and single SFC
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

            # Calculate flow count for each ingress node
            flow_dr = 0.0
            number_of_flows = self.params.run_duration / self.params.predicted_inter_arr_mean[node_id]

            # Predict data rate for expected number of flows
            for _ in range(ceil(number_of_flows)):
                flow_dr += np.random.normal(self.params.flow_dr_mean, self.params.flow_dr_stdev)

            # Update ingress traffic in metrics module
            self.params.metrics.metrics['run_total_requested_traffic'][node_id][sfc][ingress_sf] = flow_dr
