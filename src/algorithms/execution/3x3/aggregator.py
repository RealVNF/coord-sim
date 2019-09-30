import csv
import os

scenarios = ['llc', 'lnc', 'hc']
runs = ['0']
networks = ['net_x', 'dfn_58.graphml', 'intellifiber_73.graphml']
ingress = ['0.1', '0.15', '0.2', '0.25', '0.3', '0.35', '0.4', '0.45', '0.5']
algos = ['g1', 'spr1', 'spr2']
metrics = [0, 1, 2, 3, 4, 5]
metrics_id = {0: 'ab', 1: 'cd', 2: 'ef', 3: 'gh', 4: 'ij', 5: 'kl'}


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
                        data[s][r][net][ing][a] = get_last_row(read_output_file(f'scenarios/{s}/{r}/{net}/{ing}/{a}/out.csv'))
    return data


def avgerage_data(data):
    avg_data = {}
    for s in scenarios:
        avg_data[s] = {}
        for net in networks:
            avg_data[s][net] = {}
            for ing in ingress:
                avg_data[s][net][ing] = {}
                for a in algos:
                    avg_data[s][net][ing][a] = []
                    for m in metrics:
                        sum = 0
                        for r in runs:
                            sum += int(data[s][r][net][ing][a][m])
                        avg_data[s][net][ing][a].append(sum / len(runs))
    return avg_data


def collect_series(avg_data):
    data = {}
    for s in scenarios:
        data[s] = {}
        for net in networks:
            data[s][net] = {}
            for m in metrics:
                series = {a: [] for a in algos}
                for ing in ingress:
                    for a in algos:
                        series[a].append(avg_data[s][net][ing][a][m])
                data[s][net][metrics_id[m]] = series
    return data


def main():
    data = collect_data()
    avg_data = avgerage_data(data)
    series = collect_series(avg_data)
    print('')


if __name__ == "__main__":
    main()