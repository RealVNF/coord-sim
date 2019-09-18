import numpy as np
from collections import defaultdict


class CustomMetric:
    """
    Custom metrics for the GPASP algorithm
    """
    def __init__(self):
        # The dict holding simulator metrics
        self.metric_dict = {}

    def __setitem__(self, key, item):
        self.metric_dict[key] = item

    def __getitem__(self, key):
        return self.metric_dict[key]

    def reset(self):
        self['total_intermediate_targets_of_processed_flows'] = 0
        self['avg_intermediate_targets_of_processed_flows'] = 0.0
        self['total_intermediate_targets_of_dropped_flows'] = 0
        self['avg_intermediate_targets_of_dropped_flows'] = 0.0

        self['total_evasive_routes_of_processed_flows'] = 0
        self['avg_evasive_routes_of_processed_flows'] = 0.0
        self['total_evasive_routes_of_dropped_flows'] = 0
        self['avg_evasive_routes_of_dropped_flows'] = 0.0

    def processed_flow(self, flow):
        self['total_intermediate_targets_of_processed_flows'] += flow['intermediate_targets']
        self['total_evasive_routes_of_processed_flows'] += flow['evasive_routes']

    def dropped_flow(self, flow):
        self['total_intermediate_targets_of_dropped_flows'] += flow['intermediate_targets']
        self['total_evasive_routes_of_dropped_flows'] += flow['evasive_routes']

    def calc_avg_intermediate_targets(self):
        if self['processed_flows'] > 0:
            self['avg_intermediate_targets_of_processed_flows'] = self['total_intermediate_targets_of_processed_flows'] / self[
                'processed_flows']
        else:
            self['avg_intermediate_targets_of_processed_flows'] = np.Inf

        if self['dropped_flows'] > 0:
            self['avg_intermediate_targets_of_dropped_flows'] = self['total_intermediate_targets_of_dropped_flows'] \
                                                          / self['dropped_flows']
        else:
            self['avg_intermediate_targets_of_dropped_flows'] = np.Inf

    def calc_avg_evasive_routes(self):
        if self['processed_flows'] > 0:
            self['avg_evasive_routes_of_processed_flows'] = self['total_evasive_routes_of_processed_flows'] / self[
                'processed_flows']
        else:
            self['avg_evasive_route_of_processed_flows'] = np.Inf

        if self['dropped_flows'] > 0:
            self['avg_evasive_routes_of_dropped_flows'] = self['total_evasive_routes_of_dropped_flows'] \
                                                         / self['dropped_flows']
        else:
            self['avg_evasive_routes_of_dropped_flows'] = np.Inf

    def get_metrics(self):
        self.calc_avg_intermediate_targets()
        self.calc_avg_evasive_routes()

        stats = {
            'avg_intermediate_targets_of_processed_flows': self['avg_intermediate_targets_of_processed_flows'],
            'avg_intermediate_targets_of_dropped_flows': self['avg_intermediate_targets_of_dropped_flows'],
            'avg_evasive_routes_of_processed_flows': self['avg_evasive_routes_of_processed_flows'],
            'avg_evasive_routes_of_dropped_flows': self['avg_evasive_routes_of_dropped_flows']
        }
        return stats
