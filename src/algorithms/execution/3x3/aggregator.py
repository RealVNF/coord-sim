import csv
import os
import sys
import importlib

settings = importlib.import_module('algorithms.execution.3x3.settings')

start = int(sys.argv[1])
end = int(sys.argv[2]) + 1
runs = [str(x) for x in range(start, end)]

# Sync settings
scenarios = settings.scenarios
networks = settings.networks
ingress = settings.ingress
algos = settings.algos
metric_sets = settings.metric_sets
metrics2index = settings.metrics2index

# Custom settings
# scenarios = ['llc', 'lnc', 'hc']
# networks = ['bics_34.graphml', 'dfn_58.graphml', 'intellifiber_73.graphml']
# ingress = ['0.1', '0.15', '0.2', '0.25', '0.3', '0.35', '0.4', '0.45', '0.5']
# algos = ['gpasp', 'spr1', 'spr2']
# metric_sets = {'flow': ['total_flows', 'successful_flows', 'dropped_flows', 'in_network_flows'],
#                'delay': ['avg_path_delay_of_processed_flows', 'avg_ingress_2_egress_path_delay_of_processed_flows',
#                          'avg_end2end_delay_of_processed_flows'],
#                'load': ['avg_node_load', 'avg_link_load']}


def read_output_file(path):
    with open(path) as csvfile:
        filereader = csv.reader(csvfile)
        content = []
        for row in filereader:
            content.append(row)
        return content


def get_last_row(content):
    return content[-1]


def collect_data():
    data = {}
    for r in runs:
        data[r] = {}
        for s in scenarios:
            data[r][s] = {}
            for net in networks:
                data[r][s][net] = {}
                for ing in ingress:
                    data[r][s][net][ing] = {}
                    for a in algos:
                        data[r][s][net][ing][a] = get_last_row(
                            read_output_file(f'scenarios/{r}/{s}/{net}/{ing}/{a}/metrics.csv'))
    return data


def average_data(data):
    avg_data = {}
    for s in scenarios:
        avg_data[s] = {}
        for net in networks:
            avg_data[s][net] = {}
            for ing in ingress:
                avg_data[s][net][ing] = {}
                for a in algos:
                    avg_data[s][net][ing][a] = []
                    for m in range(15):
                        sum = 0
                        for r in runs:
                            sum += float(data[r][s][net][ing][a][m])
                        avg_data[s][net][ing][a].append(sum / len(runs))
    return avg_data


def transform_data(avg_data, metric_set, metric_set_id):
    for s in scenarios:
        for net in networks:
            os.makedirs(f'transformed/{s}/{net}/{metric_set_id}/', exist_ok=True)
            with open(f'transformed/{s}/{net}/{metric_set_id}/t-metrics.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                for a in algos:
                    for ing in ingress:
                        for m in metric_set:
                            # x(ing), y(value), hue(metric), style(algo)
                            row = [ing, avg_data[s][net][ing][a][metrics2index[m]], f'{m}', f'{a}']
                            writer.writerow(row)


def transform_data_confidence_intervall(data, metric_set, metric_set_id):
    for s in scenarios:
        for net in networks:
            os.makedirs(f'transformed/{s}/{net}/{metric_set_id}/', exist_ok=True)
            with open(f'transformed/{s}/{net}/{metric_set_id}/ci-t-metrics.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                for r in runs:
                    for a in algos:
                        for ing in ingress:
                            for m in metric_set:
                                # x(ing), y(value), hue(metric), style(algo)
                                row = [ing, data[r][s][net][ing][a][metrics2index[m]], f'{m}', f'{a}']
                                writer.writerow(row)


def main():
    data = collect_data()
    avg_data = average_data(data)
    for key, value in metric_sets.items():
        transform_data(avg_data, value, key)
        transform_data_confidence_intervall(data, value, key)
    print('')


if __name__ == "__main__":
    main()
