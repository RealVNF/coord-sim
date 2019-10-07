import sys
import subprocess
from datetime import timedelta
from timeit import default_timer as timer
from collections import defaultdict
import os
import json

# for r in runs:
#     for s in scenarios:
#         for net in networks:
#             for ing in ingress:
#                 processes = []
#                 for a in algos:
#                     processes.append(subprocess.Popen(['python', 'iteration_runner.py', s, r, net, ing, a]))
#                 for p in processes:
#                     p.wait()


def main():
    runs = [sys.argv[1]]
    scenarios = ['llc', 'lnc', 'hc']
    networks = ['../../../../params/networks/bics_34.graphml', '../../../../params/networks/dfn_58.graphml',
                '../../../../params/networks/intellifiber_73.graphml']
    ingress = ['0.1', '0.15', '0.2', '0.25', '0.3', '0.35', '0.4', '0.45', '0.5']
    algos = ['gpasp', 'spr1', 'spr2']

    for r in runs:
        for s in scenarios:
            for net in networks:
                for ing in ingress:
                    processes = []
                    for a in algos:
                        processes.append(subprocess.Popen(['python', 'iteration_runner.py', r, s, net, ing, a]))
                    for p in processes:
                        p.wait()


if __name__ == "__main__":
    main()
