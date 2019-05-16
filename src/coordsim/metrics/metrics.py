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

    metrics['current_active_flows'] = defaultdict(int)


def add_active_flow(flow):
    metrics['current_active_flows'][flow.current_node_id] += 1


def remove_active_flow(flow):
    metrics['current_active_flows'][flow.current_node_id] -= 1
    assert metrics['current_active_flows'][flow.current_node_id] >= 0, "Nodes cannot have negative active flows"


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
    metrics['avg_processing_delay'] = metrics['total_processing_delay'] / metrics['num_processing_delays']


def calc_avg_path_delay():
    metrics['avg_path_delay'] = metrics['total_path_delay'] / metrics['num_path_delays']


def calc_avg_end2end_delay():
    # We devide by number of processed flows to get end2end delays for processed flows only
    if metrics['processed_flows'] > 0:
        metrics['avg_end2end_delay'] = metrics['total_end2end_delay'] / metrics['processed_flows']
    else:
        metrics['avg_end2end_delay'] = math.inf


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