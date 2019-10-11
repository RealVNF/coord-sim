import subprocess

scenarios = ['llc', 'lnc', 'hc']
networks = ['bics_34.graphml', 'dfn_58.graphml', 'intellifiber_73.graphml']

metric_sets = {'flow': ['total_flows', 'successful_flows', 'dropped_flows', 'in_network_flows'],
               'delay': ['avg_path_delay_of_processed_flows', 'avg_ingress_2_egress_path_delay_of_processed_flows',
                         'avg_end2end_delay_of_processed_flows'],
               'load': ['avg_node_load', 'avg_link_load']}


def plot_all():
    processes = []
    for s in scenarios:
        for net in networks:
            for ms_id, _ in metric_sets.items():
                processes.append(subprocess.Popen(['E:/Paderborn/Bachelorarbeit/Code_working/adapted_simulator/env/Scripts/python', 'plot_runner.py', s, net, ms_id]))
    for p in processes:
        p.wait()


def main():
    plot_all()


if __name__ == "__main__":
    main()
