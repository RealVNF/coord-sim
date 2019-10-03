import csv
import os

scenarios = ['llc', 'lnc', 'hc']
runs = ['0']
networks = ['bics_34.graphml', 'dfn_58.graphml', 'intellifiber_73.graphml']
ingress = ['0.1', '0.15', '0.2', '0.25', '0.3', '0.35', '0.4', '0.45', '0.5']
algos = ['g1', 'spr1', 'spr2']

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


def get_last_row(content):
    return content[-1]


def collect_data():
    data = {}
    for s in scenarios:
        data[s] = {}
        for r in runs:
            data[s][r] = {}
            for net in networks:
                data[s][r][net] = {}
                for ing in ingress:
                    data[s][r][net][ing] = {}
                    for a in algos:
                        data[s][r][net][ing][a] = get_last_row(
                            read_output_file(f'scenarios/{s}/{r}/{net}/{ing}/{a}/out.csv'))
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
                            sum += int(data[s][r][net][ing][a][m])
                        avg_data[s][net][ing][a].append(sum / len(runs))
    return avg_data


def transform_data(data, metric_set, metric_set_id):
    os.makedirs(f'transformed/{metric_set_id}', exist_ok=False)

    for s in scenarios:
        for net in networks:
            for a in algos:
                for ing in ingress:
                    with open(f'transformed/{metric_set_id}/{s}/{net}/t-metrics.csv', 'a+') as csvfile:
                        for m in metric_set:
                            row = [ing, data[s][net][ing][a][metrics2index[m]], f'{a}-{m}']
                            writer = csv.writer(row)


def main():
    data = collect_data()
    avg_data = average_data(data)
    transform_data(avg_data, ['total_flows', 'successful_flows'], 'flows')
    print('')


if __name__ == "__main__":
    main()
