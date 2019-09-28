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

log = logging.getLogger(__name__)


def main():
    scenario = sys.argv[1]
    run = sys.argv[2]
    network = sys.argv[3]
    ingress = sys.argv[4]
    algo = sys.argv[5]

    print(f'{scenario}-{run}-{os.path.basename(network)}-{ingress}-{algo}')

if __name__ == "__main__":
    main()