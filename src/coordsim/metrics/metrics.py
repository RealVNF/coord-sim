"""

Metrics collection module

"""
import numpy as np
from collections import defaultdict
import logging
logger = logging.getLogger(__name__)

# Metrics global dict
# metrics = {}


class Metrics:
    def __init__(self, network, sfs):
        self.metrics = {}
        self.network = network
        self.sfs = sfs
        self.reset_metrics()

    def reset_metrics(self):
        """Set/Reset all metrics"""

        # successful flows
        self.metrics['generated_flows'] = 0
        self.metrics['processed_flows'] = 0
        self.metrics['dropped_flows'] = 0
        self.metrics['total_active_flows'] = 0
        # number of dropped flows per node and SF (locations)
        self.metrics['dropped_flows_locs'] = {
            v: {sf: 0 for sf in list(self.sfs.keys()) + ['EG']} for v in self.network.nodes.keys()}
        self.metrics['dropped_flow_reasons'] = {
            "TTL": 0,
            "DECISION": 0,
            "LINK_CAP": 0,
            "NODE_CAP": 0
        }
        # number of dropped flow per node - reset every run
        self.metrics['run_dropped_flows_per_node'] = {v: 0 for v in self.network.nodes.keys()}

        # delay
        self.metrics['total_processing_delay'] = 0.0
        self.metrics['num_processing_delays'] = 0
        self.metrics['avg_processing_delay'] = 0.0

        self.metrics['total_path_delay'] = 0.0
        self.metrics['num_path_delays'] = 0
        # avg path delay per used path, not per entire service chain
        self.metrics['avg_path_delay'] = 0.0

        self.metrics['total_end2end_delay'] = 0.0
        self.metrics['avg_end2end_delay'] = 0.0
        self.metrics['avg_total_delay'] = 0.0

        self.metrics['running_time'] = 0.0

        # Current number of active flows per each node
        self.metrics['current_active_flows'] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        self.metrics['current_traffic'] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

        self.reset_run_metrics()

    def reset_run_metrics(self):
        """Set/Reset metrics belonging to one run"""
        self.metrics['run_dropped_flows_per_node'] = {v: 0 for v in self.network.nodes.keys()}
        # Record total dropped flows per run
        self.metrics['run_dropped_flows'] = 0

        self.metrics['run_end2end_delay'] = 0
        self.metrics['run_avg_end2end_delay'] = 0.0
        self.metrics['run_max_end2end_delay'] = 0.0
        self.metrics['run_total_path_delay'] = 0
        # path delay averaged over all generated flows in the run
        # not 100% accurate due to flows still in the network from previous runs
        self.metrics['run_avg_path_delay'] = 0
        self.metrics['run_generated_flows'] = 0
        self.metrics['run_in_network_flows'] = 0
        self.metrics['run_processed_flows'] = 0
        self.metrics['run_max_node_usage'] = defaultdict(float)

        # total requested traffic: increased whenever a flow is requesting processing before scheduling or processing
        self.metrics['run_total_requested_traffic'] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        # record actual requested traffic for when traffic prediction is enabled
        self.metrics['run_act_total_requested_traffic'] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        # total generated traffic. traffic generate on ingress nodes is recorded
        #   this value could also be extracted from network and sim config file.
        self.metrics['run_total_requested_traffic_node'] = defaultdict(float)
        # total processed traffic (aggregated data rate) per node per SF within one run
        self.metrics['run_total_processed_traffic'] = defaultdict(lambda: defaultdict(float))

        # per-run flow counter for all destination nodes for all src nodes, sfcs, sfs in the scheduling table
        # only relevant for weighted round robin scheduling
        self.metrics['run_flow_counts'] = \
            defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))

    def calc_max_node_usage(self, node_id, current_usage):
        """
        Calculate the run's max node usage
        """
        if current_usage > self.metrics['run_max_node_usage'][node_id]:
            self.metrics['run_max_node_usage'][node_id] = current_usage

    def add_requesting_flow(self, flow):
        self.metrics['run_total_requested_traffic'][flow.current_node_id][flow.sfc][flow.current_sf] += flow.dr
        self.metrics['run_act_total_requested_traffic'][flow.current_node_id][flow.sfc][flow.current_sf] += flow.dr

    # call when new flows starts processing at an SF
    def add_active_flow(self, flow, current_node_id, current_sf):
        self.metrics['current_active_flows'][current_node_id][flow.sfc][current_sf] += 1
        self.metrics['current_traffic'][current_node_id][flow.sfc][current_sf] += flow.dr
        self.metrics['run_total_processed_traffic'][current_node_id][current_sf] += flow.dr

    def remove_active_flow(self, flow, current_node_id, current_sf):
        self.metrics['current_active_flows'][current_node_id][flow.sfc][current_sf] -= 1
        self.metrics['current_traffic'][current_node_id][flow.sfc][current_sf] -= flow.dr

        try:
            assert self.metrics['current_active_flows'][flow.current_node_id][flow.sfc][flow.current_sf] >= 0, "\
            Nodes cannot have negative current active flows"

            assert self.metrics['total_active_flows'] >= 0, "\
            Nodes cannot have negative active flows"

            assert self.metrics['current_traffic'][flow.current_node_id][flow.sfc][flow.current_sf] >= 0.00, "\
            Nodes cannot have negative traffic"

        except Exception as e:
            logger.critical(e)

    def generated_flow(self, flow, current_node):
        self.metrics['generated_flows'] += 1
        self.metrics['run_generated_flows'] += 1
        self.metrics['total_active_flows'] += 1
        self.metrics['run_total_requested_traffic_node'][current_node] += flow.dr

    # call when flow was successfully completed, ie, processed by all required SFs
    def completed_flow(self):
        self.metrics['processed_flows'] += 1
        self.metrics['run_processed_flows'] += 1
        self.metrics['total_active_flows'] -= 1
        assert self.metrics['total_active_flows'] >= 0, "Cannot have negative active flows"

    def dropped_flow(self, flow, reason):

        flow.dropped = True
        self.metrics['dropped_flows'] += 1
        self.metrics['total_active_flows'] -= 1
        # Check flows that finished processing
        if flow.current_sf is None:
            # Set 'current_sf' as EG to mark flow on its way out of the network
            current_sf = 'EG'
        else:
            current_sf = flow.current_sf
        self.metrics['dropped_flows_locs'][flow.current_node_id][current_sf] += 1
        self.metrics['run_dropped_flows_per_node'][flow.current_node_id] += 1
        self.metrics['run_dropped_flows'] += 1
        assert self.metrics['total_active_flows'] >= 0, "Cannot have negative active flows"

        assert reason in list(self.metrics['dropped_flow_reasons'].keys())
        if reason == "DECISION":
            if flow.ttl <= 0:
                reason = "TTL"
        self.metrics['dropped_flow_reasons'][reason] += 1

    def add_processing_delay(self, delay):
        self.metrics['num_processing_delays'] += 1
        self.metrics['total_processing_delay'] += delay

    def add_path_delay(self, delay):
        self.metrics['num_path_delays'] += 1
        self.metrics['total_path_delay'] += delay

        # calc path delay per run; average over num generated flows in run
        self.metrics['run_total_path_delay'] += delay
        if self.metrics['run_generated_flows'] > 0:
            self.metrics[
                'run_avg_path_delay'
            ] = self.metrics['run_total_path_delay'] / self.metrics['run_generated_flows']

    def add_end2end_delay(self, delay):
        self.metrics['total_end2end_delay'] += delay
        self.metrics['run_end2end_delay'] += delay
        if delay > self.metrics['run_max_end2end_delay']:
            self.metrics['run_max_end2end_delay'] = delay

    def running_time(self, start_time, end_time):
        self.metrics['running_time'] = end_time - start_time

    def calc_avg_processing_delay(self):
        if self.metrics['num_processing_delays'] > 0:
            self.metrics['avg_processing_delay'] \
                = self.metrics['total_processing_delay'] / self.metrics['num_processing_delays']
        else:
            self.metrics['avg_processing_delay'] = 0

    def calc_avg_path_delay(self):
        if self.metrics['num_path_delays'] > 0:
            self.metrics['avg_path_delay'] = self.metrics['total_path_delay'] / self.metrics['num_path_delays']
        else:
            self.metrics['avg_path_delay'] = 0

    def calc_avg_end2end_delay(self):
        # We divide by number of processed flows to get end2end delays for processed flows only
        if self.metrics['processed_flows'] > 0:
            self.metrics['avg_end2end_delay'] = self.metrics['total_end2end_delay'] / self.metrics['processed_flows']
        else:
            self.metrics['avg_end2end_delay'] = 0  # No avg end2end delay yet (no processed flows yet)

        if self.metrics['run_processed_flows'] > 0:
            self.metrics[
                'run_avg_end2end_delay'
            ] = self.metrics['run_end2end_delay'] / self.metrics['run_processed_flows']
        else:
            self.metrics['run_avg_end2end_delay'] = 0  # No run avg end2end delay yet (no processed flows yet)

    def calc_avg_total_delay(self):
        avg_processing_delay = self.metrics['avg_processing_delay']
        avg_path_delay = self.metrics['avg_path_delay']
        self.metrics['avg_total_delay'] = np.mean([avg_path_delay, avg_processing_delay])

    def get_active_flows(self):
        return self.metrics['current_active_flows']

    def get_metrics(self):
        self.calc_avg_processing_delay()
        self.calc_avg_path_delay()
        self.calc_avg_total_delay()
        self.calc_avg_end2end_delay()
        return self.metrics
