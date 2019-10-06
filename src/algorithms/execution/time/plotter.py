import subprocess

config = ['c1']
networks = ['dfn_58.graphml']

metric_sets = {'flow': ['total_flows', 'successful_flows', 'dropped_flows', 'in_network_flows'],
               'delay': ['avg_path_delay_of_processed_flows', 'avg_ingress_2_egress_path_delay_of_processed_flows',
                         'avg_end2end_delay_of_processed_flows'],
               'load': ['avg_node_load', 'avg_link_load']}


def plot_all():
    processes = []
    for c in config:
        for net in networks:
            for key, value in metric_sets.items():
                processes.append(subprocess.Popen(['python', 'plot_runner.py', c, net, key]))
    for p in processes:
        p.wait()


def main():
    plot_all()


if __name__ == "__main__":
    main()