import logging
import os

import random
import networkx as nx
import numpy as np
from datetime import datetime
from collections import defaultdict
from siminterface.simulator import ExtendedSimulatorAction
from siminterface.simulator import Simulator
from algorithms.greedy.g1 import G1Algo

import sys
import yaml
import csv

log = logging.getLogger(__name__)


def main():
    scenario = sys.argv[1]
    run = sys.argv[2]
    network_path = sys.argv[3]
    network = os.path.basename(network_path)
    ingress = sys.argv[4]
    algo = sys.argv[5]

    result_path = f'scenarios/{scenario}/{run}/{network}/{ingress}/{algo}'
    os.makedirs(result_path, exist_ok=True)

    with open(f'{result_path}/out.csv', 'w') as outfile:
        writer = csv.writer(outfile)
        writer.writerow([1, 2, 3, 4, 5, 6])

    print(f'{scenario}-{run}-{os.path.basename(network)}-{ingress}-{algo}')

if __name__ == "__main__":
    main()