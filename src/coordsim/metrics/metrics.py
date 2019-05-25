"""

Metrics collection module

"""
import numpy as np
from collections import defaultdict
import math
# Metrics global dict
metrics = {}


# Initialize the metrics module
def reset():
    metrics['generated_flows'] = 0
    metrics['processed_flows'] = 0
    metrics['dropped_flows'] = 0

    metrics['total_processing_delay'] = 0.0
    metrics['num_processing_delays'] = 0
    metrics['avg_processing_delay'] = 0.0

    metrics['total_path_delay'] = 0.0
    metrics['num_path_delays'] = 0
    metrics['avg_path_delay'] = 0.0

    metrics['total_end2end_delay'] = 0.0
    metrics['avg_end2end_delay'] = 0.0

    metrics['avg_total_delay'] = 0.0

    metrics['running_time'] = 0.0

    # Current number of active flows per each node
    metrics['current_active_flows'] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    metrics['total_active_flows'] = 0
    metrics['current_traffic'] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))


def add_active_flow(flow):
    metrics['total_active_flows'] += 1
    metrics['current_active_flows'][flow.current_node_id][flow.sfc][flow.current_sf] += 1
    metrics['current_traffic'][flow.current_node_id][flow.sfc][flow.current_sf] += flow.dr


def remove_active_flow(flow):
    metrics['total_active_flows'] -= 1
    metrics['current_active_flows'][flow.current_node_id][flow.sfc][flow.current_sf] -= 1
    metrics['current_traffic'][flow.current_node_id][flow.sfc][flow.current_sf] -= flow.dr
    assert metrics['current_traffic'][flow.current_node_id][flow.sfc][flow.current_sf] >= 0, ""
    "Nodes cannot have negative active flows"
    assert metrics['current_active_flows'][flow.current_node_id][flow.sfc][flow.current_sf] >= 0, ""
    "Nodes cannot have negative active flows"
    assert metrics['total_active_flow'] >= 0, ""
    "Nodes cannot have negative active flows"


def generated_flow():
    metrics['generated_flows'] += 1


def processed_flow():
    metrics['processed_flows'] += 1


def dropped_flow():
    metrics['dropped_flows'] += 1


def add_processing_delay(delay):
    metrics['num_processing_delays'] += 1
    metrics['total_processing_delay'] += delay


def add_path_delay(delay):
    metrics['num_path_delays'] += 1
    metrics['total_path_delay'] += delay


def add_end2end_delay(delay):
    metrics['total_end2end_delay'] += delay


def running_time(start_time, end_time):
    metrics['running_time'] = end_time - start_time


def calc_avg_processing_delay():
    if metrics['num_processing_delays'] > 0:
        metrics['avg_processing_delay'] = metrics['total_processing_delay'] / metrics['num_processing_delays']
    else:
        metrics['avg_processing_delay'] = 9999


def calc_avg_path_delay():
    if metrics['num_path_delays'] > 0:
        metrics['avg_path_delay'] = metrics['total_path_delay'] / metrics['num_path_delays']
    else:
        metrics['avg_path_delay'] = 9999


def calc_avg_end2end_delay():
    # We devide by number of processed flows to get end2end delays for processed flows only
    if metrics['processed_flows'] > 0:
        metrics['avg_end2end_delay'] = metrics['total_end2end_delay'] / metrics['processed_flows']
    else:
        metrics['avg_end2end_delay'] = 9999  # No avg end2end delay yet (no processed flows yet)


def calc_avg_total_delay():
    avg_processing_delay = metrics['avg_processing_delay']
    avg_path_delay = metrics['avg_path_delay']
    metrics['avg_total_delay'] = np.mean([avg_path_delay, avg_processing_delay])


def get_active_flows():
    return metrics['current_active_flows']


def get_metrics():
    calc_avg_processing_delay()
    calc_avg_path_delay()
    calc_avg_total_delay()
    calc_avg_end2end_delay()
    return metrics
