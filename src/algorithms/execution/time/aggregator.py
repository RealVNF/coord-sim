import csv
import os

config = ['c1']
runs = [str(x) for x in range(10)]
networks = ['dfn_58.graphml']
algos = ['gpasp', 'spr1', 'spr2']

metric_sets = {'flow': ['total_flows', 'successful_flows', 'dropped_flows', 'in_network_flows'],
               'delay': ['avg_path_delay_of_processed_flows', 'avg_ingress_2_egress_path_delay_of_processed_flows',
                         'avg_end2end_delay_of_processed_flows'],
               'load': ['avg_node_load', 'avg_link_load']}

metrics2index = {'time': 0,
                 'total_flows': 1,
                 'successful_flows': 2,
                 'dropped_flows': 3,
                 'in_network_flows': 4,
                 'avg_end2end_delay_of_dropped_flows': 5,
                 'avg_end2end_delay_of_processed_flows': 6,
                 'avg_sf_processing_delay': 7,
                 'avg_sfc_length': 8,
                 'avg_crossed_link_delay': 9,
                 'avg_path_delay': 10,
                 'avg_path_delay_of_processed_flows': 11,
                 'avg_ingress_2_egress_path_delay_of_processed_flows': 12,
                 'avg_node_load': 13,
                 'avg_link_load': 14
                 }
index2metric = {0: 'time',
                1: 'total_flows',
                2: 'successful_flows',
                3: 'dropped_flows',
                4: 'in_network_flows',
                5: 'avg_end2end_delay_of_dropped_flows',
                6: 'avg_end2end_delay_of_processed_flows',
                7: 'avg_sf_processing_delay',
                8: 'avg_sfc_length',
                9: 'avg_crossed_link_delay',
                10: 'avg_path_delay',
                11: 'avg_path_delay_of_processed_flows',
                12: 'avg_ingress_2_egress_path_delay_of_processed_flows',
                13: 'avg_node_load',
                14: 'avg_link_load'
                }


def read_output_file(path):
    with open(path) as csvfile:
        filereader = csv.reader(csvfile)
        content = []
        for row in filereader:
            content.append(row)
        return content


def remove_first(content):
    return content[1:]


def collect_data():
    data = {}
    for c in config:
        data[c] = {}
        for r in runs:
            data[c][r] = {}
            for net in networks:
                data[c][r][net] = {}
                for a in algos:
                    data[c][r][net][a] = remove_first(read_output_file(f'scenarios/{c}/{r}/{net}/{a}/metrics.csv'))
    return data


def transform_data(data, metric_set, metric_set_id):
    for c in config:
        for net in networks:
            os.makedirs(f'transformed/{c}/{net}/{metric_set_id}/', exist_ok=False)
            with open(f'transformed/{c}/{net}/{metric_set_id}/t-metrics.csv', 'a+', newline='') as csvfile:
                writer = csv.writer(csvfile)
                for r in runs:
                    for a in algos:
                        for drow in data[c][r][net][a]:
                            for m in metric_set:
                                # x(time), y(value), hue(metric), style(algo)
                                row = [drow[metrics2index['time']], drow[metrics2index[m]], f'{m}', f'{a}']
                                writer.writerow(row)


def main():
    #avg_data = average_data(data)
    for key, value in metric_sets.items():
        transform_data(data, value, key)
    print('')


if __name__ == "__main__":
    main()
