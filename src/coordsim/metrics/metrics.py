"""

Metrics collection module

"""
import numpy as np
from collections import defaultdict
import logging
logger = logging.getLogger(__name__)


class MetricStore:
    """
    Conventional singelton.
    """

    instance = None

    def __init__(self):
        self.metric_dict = {}

    @staticmethod
    def get_instance():
        if MetricStore.instance is None:
            MetricStore.instance = MetricStore()
        return MetricStore.instance

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

        self['total_processing_delay'] = 0.0
        self['num_processing_delays'] = 0
        self['avg_processing_delay'] = 0.0

        self['total_path_delay'] = 0.0
        self['avg_path_delay'] = 0.0

        self['total_path_delay_of_processed_flows'] = 0.0
        self['avg_path_delay_of_processed_flows'] = 0.0

        self['total_end2end_delay'] = 0.0
        self['avg_end2end_delay'] = 0.0

        self['avg_total_delay'] = 0.0
        self['running_time'] = 0.0

        # Current number of active flows per each node
        self['current_active_flows'] = defaultdict(lambda: defaultdict(lambda: defaultdict(np.int)))
        self['current_traffic'] = defaultdict(lambda: defaultdict(lambda: defaultdict(np.float64)))

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

    def generated_flow(self):
        self['generated_flows'] += 1
        self['total_active_flows'] += 1

    def processed_flow(self):
        self['processed_flows'] += 1
        self['total_active_flows'] -= 1
        assert self['total_active_flows'] >= 0, "Cannot have negative active flows"

    def dropped_flow(self):
        self['dropped_flows'] += 1
        self['total_active_flows'] -= 1
        assert self['total_active_flows'] >= 0, "Cannot have negative active flows"

    def add_processing_delay(self, delay):
        self['num_processing_delays'] += 1
        self['total_processing_delay'] += delay

    def add_path_delay(self, delay):
        self['total_path_delay'] += delay

    def add_path_delay_of_processed_flows(self, delay):
        self['total_path_delay_of_processed_flows'] += delay

    def add_end2end_delay(self, delay):
        self['total_end2end_delay'] += delay

    def running_time(self, start_time, end_time):
        self['running_time'] = end_time - start_time

    def calc_avg_processing_delay(self):
        if self['num_processing_delays'] > 0:
            self['avg_processing_delay'] = self['total_processing_delay'] / self['num_processing_delays']
        else:
            self['avg_processing_delay'] = 9999

    def calc_avg_path_delay(self):
        if self['generated_flows'] > 0:
            self['avg_path_delay'] = self['total_path_delay'] / self['generated_flows']
        else:
            self['avg_path_delay'] = 9999

    def calc_avg_path_delay_of_processed_flows(self):
        if self['processed_flows'] > 0:
            self['avg_path_delay_of_processed_flows'] = self['total_path_delay_of_processed_flows'] / self[
                'processed_flows']
        else:
            self['avg_path_delay_of_processed_flows'] = 9999

    def calc_avg_end2end_delay(self):
        # We devide by number of processed flows to get end2end delays for processed flows only
        if self['processed_flows'] > 0:
            self['avg_end2end_delay'] = self['total_end2end_delay'] / self['processed_flows']
        else:
            self['avg_end2end_delay'] = 9999  # No avg end2end delay yet (no processed flows yet)

    def calc_avg_total_delay(self):
        avg_processing_delay = self['avg_processing_delay']
        avg_path_delay = self['avg_path_delay']
        self['avg_total_delay'] = np.mean([avg_path_delay, avg_processing_delay])

    def get_active_flows(self):
        return self['current_active_flows']

    def get_metrics(self):
        self.calc_avg_processing_delay()
        self.calc_avg_path_delay()
        self.calc_avg_total_delay()
        self.calc_avg_end2end_delay()
        self.calc_avg_path_delay()
        self.calc_avg_path_delay_of_processed_flows()
        return self.metric_dict
