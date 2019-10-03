import subprocess
from datetime import timedelta
from timeit import default_timer as timer
from collections import defaultdict
import os
import json

# for s in scenarios:
#     for r in runs:
#         for net in networks:
#             for ing in ingress:
#                 processes = []
#                 for a in algos:
#                     processes.append(subprocess.Popen(['python', 'iteration_runner.py', s, r, net, ing, a]))
#                 for p in processes:
#                     p.wait()

def main():
    scenarios = ['llc', 'lnc', 'hc']
    runs = ['0']
    networks = ['../../../../params/bics_34.graphml', '../../../../params/networks/dfn_58.graphml',
                '../../../../params/networks/intellifiber_73.graphml']
    ingress = ['0.1', '0.15', '0.2', '0.25', '0.3', '0.35', '0.4', '0.45', '0.5']
    algos = ['gpasp', 'spr1', 'spr2']

    os.makedirs('time/', exist_ok=True)
    time_tot_dict = defaultdict(str)
    time_sce_dict = defaultdict(str)
    time_run_dict = defaultdict(lambda: defaultdict(str))
    time_net_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(str)))
    time_ing_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(str))))

    total_start = timer()
    for s in scenarios:
        s_start = timer()
        for r in runs:
            run_start = timer()
            for net in networks:
                net_start = timer()
                for ing in ingress:
                    i_start = timer()
                    processes = []
                    for a in algos:
                        processes.append(subprocess.Popen(['python', 'iteration_runner.py', s, r, net, ing, a]))
                    for p in processes:
                        p.wait()
                    i_end = timer()
                    time_ing_dict[s][r][os.path.basename(net)][ing] = str(timedelta(i_end - i_start))
                net_end = timer()
                time_net_dict[s][r][os.path.basename(net)] = str(timedelta(net_end - net_start))
            run_end= timer()
            time_run_dict[s][r] = str(timedelta(run_end - run_start))
        s_end = timer()
        time_sce_dict[s] = str(timedelta(s_end - s_start))
    total_end = timer()
    time_tot_dict['total'] = str(timedelta(total_end - total_start))

    with open('time/total.json', 'w') as file:
        json.dump(time_tot_dict, file)
    with open('time/scenarios.json', 'w') as file:
        json.dump(time_sce_dict, file)
    with open('time/runs.json', 'w') as file:
        json.dump(time_run_dict, file)
    with open('time/networks.json', 'w') as file:
        json.dump(time_net_dict, file)
    with open('time/ing.json', 'w') as file:
        json.dump(time_ing_dict, file)


if __name__ == "__main__":
    main()
