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
    param = sys.argv[1]
    print(param)
    with open(f't.yml', 'w') as outfile:
        yaml.dump({'name': 'a'}, outfile)


if __name__ == "__main__":
    main()