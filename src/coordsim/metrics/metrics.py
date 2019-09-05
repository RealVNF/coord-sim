"""

Metrics collection module

"""
import numpy as np
import networkx as nx
from collections import defaultdict
import logging
logger = logging.getLogger(__name__)


class MetricStore:

    def __init__(self, network):
        self.network = network
        self.metric_dict = {}

    def __setitem__(self, key, item):
        self.metric_dict[key] = item

    def __getitem__(self, key):
        return self.metric_dict[key]

    def reset(self):
        self['generated_flows'] = 0
        self['processed_flows'] = 0
        self['run_processed_flows'] = 0
        self['dropped_flows'] = 0
        self['total_active_flows'] = 0

        self['total_sf_processing_delay'] = 0.0
        self['num_sf_processing_delays'] = 0
        self['avg_sf_processing_delay'] = 0.0

        self['total_sfc_length'] = 0
        self['avg_sfc_length'] = 0.0

        self['total_crossed_link_delay'] = 0.0
        self['num_crossed_links'] = 0
        self['avg_crossed_link_delay'] = 0.0

        self['total_path_delay'] = 0.0
        self['avg_path_delay'] = 0.0

        self['total_path_delay_of_processed_flows'] = 0.0
        self['avg_path_delay_of_processed_flows'] = 0.0

        self['total_ingress_2_egress_path_delay_of_processed_flows'] = 0.0
        self['avg_ingress_2_egress_path_delay_of_processed_flows'] = 0.0

        self['total_end2end_delay_of_dropped_flows'] = 0.0
        self['avg_end2end_delay_of_dropped_flows'] = 0.0
        self['total_end2end_delay_of_processed_flows'] = 0.0
        self['avg_end2end_delay_of_processed_flows'] = 0.0

        self['avg_total_delay'] = 0.0
        self['running_time'] = 0.0

        # Current number of active flows per each node
        self['current_active_flows'] = defaultdict(lambda: defaultdict(lambda: defaultdict(np.int)))
        self['current_traffic'] = defaultdict(lambda: defaultdict(lambda: defaultdict(np.float64)))

        self['graveyard'] = defaultdict(int)

        # Record all flows, to access their trace
        self['flows'] = []

    def add_active_flow(self, flow, current_node_id, current_sf):
        self['current_active_flows'][current_node_id][flow.sfc][current_sf] += 1
        self['current_traffic'][current_node_id][flow.sfc][current_sf] += flow.dr

    def remove_active_flow(self, flow, current_node_id, current_sf):

        self['current_active_flows'][current_node_id][flow.sfc][current_sf] -= 1
        self['current_traffic'][current_node_id][flow.sfc][current_sf] -= flow.dr

        try:
            assert self['current_active_flows'][flow.current_node_id][flow.sfc][flow.current_sf] >= 0, "\
            Nodes cannot have negative current active flows"

            assert self['total_active_flows'] >= 0, "\
            Nodes cannot have negative active flows"

            assert self['current_traffic'][flow.current_node_id][flow.sfc][flow.current_sf] >= 0.00, "\
            Nodes cannot have negative traffic"

        except Exception as e:
            logger.critical(e)

    def generated_flow(self, flow):
        self['generated_flows'] += 1
        self['total_active_flows'] += 1
        #self['flows'].append(flow)
        self['total_sfc_length'] += len(flow.sfc_components)

    def processed_flow(self, flow):
        self['processed_flows'] += 1
        self['total_active_flows'] -= 1
        assert self['total_active_flows'] >= 0, "Cannot have negative active flows"
        self['total_ingress_2_egress_path_delay_of_processed_flows'] += nx.shortest_path_length(self.network,
                                                                                                flow.ingress_node_id,
                                                                                                flow.egress_node_id,
                                                                                                weight="delay")

    def dropped_flow(self, flow):
        self['dropped_flows'] += 1
        self['total_active_flows'] -= 1
        assert self['total_active_flows'] >= 0, "Cannot have negative active flows"
        self['graveyard'][flow.current_node_id] += 1

    def add_sf_processing_delay(self, delay):
        self['num_sf_processing_delays'] += 1
        self['total_sf_processing_delay'] += delay

    def add_crossed_link_delay(self, delay):
        self['num_crossed_links'] += 1
        self['total_crossed_link_delay'] += delay

    def add_path_delay(self, delay):
        self['total_path_delay'] += delay

    def add_path_delay_of_processed_flows(self, delay):
        self['total_path_delay_of_processed_flows'] += delay

    def add_end2end_delay_of_dropped_flows(self, delay):
        self['total_end2end_delay_of_dropped_flows'] += delay

    def add_end2end_delay_of_processed_flows(self, delay):
        self['total_end2end_delay_of_processed_flows'] += delay

    def running_time(self, start_time, end_time):
        self['running_time'] = end_time - start_time

    def calc_avg_sf_processing_delay(self):
        if self['num_sf_processing_delays'] > 0:
            self['avg_sf_processing_delay'] = self['total_sf_processing_delay'] / self['num_sf_processing_delays']
        else:
            self['avg_sf_processing_delay'] = np.Inf

    def calc_avg_sfc_length(self):
        if self['generated_flows'] > 0:
            self['avg_sfc_length'] = self['total_sfc_length'] / self['generated_flows']
        else:
            self['avg_sfc_length'] = np.Inf

    def avg_crossed_link_delay(self):
        if self['num_crossed_links'] > 0:
            self['avg_crossed_link_delay'] = self['total_crossed_link_delay'] / self['num_crossed_links']
        else:
            self['avg_crossed_link_delay'] = np.Inf

    def calc_avg_path_delay(self):
        if self['generated_flows'] > 0:
            self['avg_path_delay'] = self['total_path_delay'] / self['generated_flows']
        else:
            self['avg_path_delay'] = np.Inf

    def calc_avg_path_delay_of_processed_flows(self):
        if self['processed_flows'] > 0:
            self['avg_path_delay_of_processed_flows'] = self['total_path_delay_of_processed_flows'] / self[
                'processed_flows']
        else:
            self['avg_path_delay_of_processed_flows'] = np.Inf

    def calc_avg_ingress_2_egress_path_delay_of_processed_flows(self):
        if self['processed_flows'] > 0:
            self['avg_ingress_2_egress_path_delay_of_processed_flows'] = \
                self['total_ingress_2_egress_path_delay_of_processed_flows'] / self['processed_flows']
        else:
            self['avg_ingress_2_egress_path_delay_of_processed_flows'] = np.Inf

    def calc_avg_end2end_delay_of_dropped_flows(self):
        # We devide by number of processed flows to get end2end delays for processed flows only
        if self['dropped_flows'] > 0:
            self['avg_end2end_delay_of_dropped_flows'] = self['total_end2end_delay_of_dropped_flows'] \
                                                         / self['dropped_flows']
        else:
            self['avg_end2end_delay_of_dropped_flows'] = np.Inf  # No avg end2end delay yet (no dropped flows yet)

    def calc_avg_end2end_delay_of_processed_flows(self):
        # We devide by number of processed flows to get end2end delays for processed flows only
        if self['processed_flows'] > 0:
            self['avg_end2end_delay_of_processed_flows'] = self['total_end2end_delay_of_processed_flows'] \
                                                           / self['processed_flows']
        else:
            self['avg_end2end_delay_of_processed_flows'] = np.Inf  # No avg end2end delay yet (no processed flows yet)

    def calc_avg_total_delay(self):
        avg_sf_processing_delay = self['avg_sf_processing_delay']
        avg_path_delay = self['avg_path_delay']
        self['avg_total_delay'] = np.mean([avg_path_delay, avg_sf_processing_delay])

    def get_active_flows(self):
        return self['current_active_flows']

    def get_metrics(self):
        self.calc_avg_sf_processing_delay()
        self.calc_avg_sfc_length()
        self.avg_crossed_link_delay()
        self.calc_avg_path_delay()
        self.calc_avg_total_delay()
        self.calc_avg_end2end_delay_of_dropped_flows()
        self.calc_avg_end2end_delay_of_processed_flows()
        self.calc_avg_path_delay()
        self.calc_avg_path_delay_of_processed_flows()
        self.calc_avg_ingress_2_egress_path_delay_of_processed_flows()
        return self.metric_dict
