import numpy as np

# Metrics global dict
metrics = {}


# Initialize the metrics module
def reset():
    metrics['generated_flows'] = 0
    metrics['processed_flows'] = 0
    metrics['dropped_flows'] = 0
    metrics['processing_delays'] = []
    metrics['path_delays'] = []
    metrics['avg_processing_delay'] = 0.0
    metrics['avg_path_delay'] = 0.0
    metrics['avg_total_delay'] = 0.0


def generated_flow():
    metrics['generated_flows'] += 1


def processed_flow():
    metrics['processed_flows'] += 1


def dropped_flow():
    metrics['dropped_flows'] += 1


def add_processing_delay(delay):
    metrics['processing_delays'].append(delay)


def add_path_delay(delay):
    metrics['path_delays'].append(delay)


def calc_avg_processing_delay():
    metrics['avg_processing_delay'] = np.mean(metrics['processing_delays'])


def calc_avg_path_delay():
    metrics['avg_path_delay'] = np.mean(metrics['path_delays'])


def calc_avg_total_delay():
    avg_processing_delay = metrics['avg_processing_delay']
    avg_path_delay = metrics['avg_path_delay']
    metrics['avg_total_delay'] = np.mean([avg_path_delay, avg_processing_delay])


def get_metrics():
    calc_avg_processing_delay()
    calc_avg_path_delay()
    calc_avg_total_delay()
    return metrics
