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


def sec2str(s):
    days, dr = divmod(s, 60*60*24)
    hours, hr = divmod(dr, 3600)
    minutes, seconds = divmod(hr, 60)
    return f'{int(days)}:{int(hours)}:{int(minutes)}:{int(seconds)}'


def main():
    scenarios = ['llc', 'lnc', 'hc']
    runs = ['0']
    networks = ['../../../../params/networks/bics_34.graphml', '../../../../params/networks/dfn_58.graphml',
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
                    time_ing_dict[s][r][os.path.basename(net)][ing] = sec2str(timedelta(i_end - i_start).seconds)
                net_end = timer()
                time_net_dict[s][r][os.path.basename(net)] = sec2str(timedelta(net_end - net_start).seconds)
            run_end= timer()
            time_run_dict[s][r] = sec2str(timedelta(run_end - run_start).seconds)
        s_end = timer()
        time_sce_dict[s] = sec2str(timedelta(s_end - s_start).seconds)
    total_end = timer()
    time_tot_dict['total'] = sec2str(timedelta(total_end - total_start).seconds)

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
