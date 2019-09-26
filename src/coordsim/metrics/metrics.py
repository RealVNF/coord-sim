"""

Metrics collection module

"""
import numpy as np
from collections import defaultdict
import logging
logger = logging.getLogger(__name__)

# Metrics global dict
metrics = {}


def reset_metrics():
    """Set/Reset all metrics"""

    # successful flows
    metrics['generated_flows'] = 0
    metrics['processed_flows'] = 0
    metrics['dropped_flows'] = 0
    metrics['total_active_flows'] = 0

    # delay
    metrics['total_processing_delay'] = 0.0
    metrics['num_processing_delays'] = 0
    metrics['avg_processing_delay'] = 0.0

    metrics['total_path_delay'] = 0.0
    metrics['num_path_delays'] = 0
    # avg path delay per used path, not per entire service chain
    metrics['avg_path_delay'] = 0.0

    metrics['total_end2end_delay'] = 0.0
    metrics['avg_end2end_delay'] = 0.0
    metrics['avg_total_delay'] = 0.0

    metrics['running_time'] = 0.0

    # Current number of active flows per each node
    metrics['current_active_flows'] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    metrics['current_traffic'] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

    reset_run_metrics()


def reset_run_metrics():
    """Set/Reset metrics belonging to one run"""
    metrics['run_end2end_delay'] = 0
    metrics['run_avg_end2end_delay'] = 0.0
    metrics['run_max_end2end_delay'] = 0.0
    metrics['run_total_path_delay'] = 0
    # path delay averaged over all generated flows in the run
    metrics['run_avg_path_delay'] = 0
    metrics['run_generated_flows'] = 0
    metrics['run_in_network_flows'] = 0
    metrics['run_processed_flows'] = 0
    metrics['run_max_node_usage'] = defaultdict(float)

    # total requested traffic: increased whenever a flow is requesting processing before scheduling or processing
    metrics['run_total_requested_traffic'] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    # total generated traffic. traffic generate on ingress nodes is recorded
    #   this value could also be extracted from network and sim config file.
    metrics['run_total_requested_traffic_node'] = defaultdict(float)
    # total processed traffic (aggregated data rate) per node per SF within one run
    metrics['run_total_processed_traffic'] = defaultdict(lambda: defaultdict(float))


def calc_max_node_usage(node_id, current_usage):
    """
    Calculate the run's max node usage
    """
    if current_usage > metrics['run_max_node_usage'][node_id]:
        metrics['run_max_node_usage'][node_id] = current_usage


def add_requesting_flow(flow):
    metrics['run_total_requested_traffic'][flow.current_node_id][flow.sfc][flow.current_sf] += flow.dr


# call when new flows starts processing at an SF
def add_active_flow(flow, current_node_id, current_sf):
    metrics['current_active_flows'][current_node_id][flow.sfc][current_sf] += 1
    metrics['current_traffic'][current_node_id][flow.sfc][current_sf] += flow.dr
    metrics['run_total_processed_traffic'][current_node_id][current_sf] += flow.dr


def remove_active_flow(flow, current_node_id, current_sf):
    metrics['current_active_flows'][current_node_id][flow.sfc][current_sf] -= 1
    metrics['current_traffic'][current_node_id][flow.sfc][current_sf] -= flow.dr

    try:
        assert metrics['current_active_flows'][flow.current_node_id][flow.sfc][flow.current_sf] >= 0, "\
        Nodes cannot have negative current active flows"

        assert metrics['total_active_flows'] >= 0, "\
        Nodes cannot have negative active flows"

        assert metrics['current_traffic'][flow.current_node_id][flow.sfc][flow.current_sf] >= 0.00, "\
        Nodes cannot have negative traffic"

    except Exception as e:
        logger.critical(e)


def generated_flow(flow, current_node):
    metrics['generated_flows'] += 1
    metrics['run_generated_flows'] += 1
    metrics['total_active_flows'] += 1
    metrics['run_total_requested_traffic_node'][current_node] += flow.dr


# call when flow was successfully completed, ie, processed by all required SFs
def completed_flow():
    metrics['processed_flows'] += 1
    metrics['run_processed_flows'] += 1
    metrics['total_active_flows'] -= 1
    assert metrics['total_active_flows'] >= 0, "Cannot have negative active flows"


def dropped_flow():
    metrics['dropped_flows'] += 1
    metrics['total_active_flows'] -= 1
    assert metrics['total_active_flows'] >= 0, "Cannot have negative active flows"


def add_processing_delay(delay):
    metrics['num_processing_delays'] += 1
    metrics['total_processing_delay'] += delay


def add_path_delay(delay):
    metrics['num_path_delays'] += 1
    metrics['total_path_delay'] += delay

    # calc path delay per run; average over num generated flows in run
    metrics['run_total_path_delay'] += delay
    if metrics['run_processed_flows'] > 0:
        metrics['run_avg_path_delay'] = metrics['run_total_path_delay'] / metrics['run_generated_flows']


def add_end2end_delay(delay):
    metrics['total_end2end_delay'] += delay
    metrics['run_end2end_delay'] += delay
    if delay > metrics['run_max_end2end_delay']:
        metrics['run_max_end2end_delay'] = delay


def running_time(start_time, end_time):
    metrics['running_time'] = end_time - start_time


def calc_avg_processing_delay():
    if metrics['num_processing_delays'] > 0:
        metrics['avg_processing_delay'] = metrics['total_processing_delay'] / metrics['num_processing_delays']
    else:
        metrics['avg_processing_delay'] = 0


def calc_avg_path_delay():
    if metrics['num_path_delays'] > 0:
        metrics['avg_path_delay'] = metrics['total_path_delay'] / metrics['num_path_delays']
    else:
        metrics['avg_path_delay'] = 0


def calc_avg_end2end_delay():
    # We divide by number of processed flows to get end2end delays for processed flows only
    if metrics['processed_flows'] > 0:
        metrics['avg_end2end_delay'] = metrics['total_end2end_delay'] / metrics['processed_flows']
    else:
        metrics['avg_end2end_delay'] = 0  # No avg end2end delay yet (no processed flows yet)

    if metrics['run_processed_flows'] > 0:
        metrics['run_avg_end2end_delay'] = metrics['run_end2end_delay'] / metrics['run_processed_flows']
    else:
        metrics['run_avg_end2end_delay'] = 0  # No run avg end2end delay yet (no processed flows yet)


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
