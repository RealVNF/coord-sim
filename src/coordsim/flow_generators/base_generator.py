import logging
import numpy as np
import random
from typing import Tuple
from coordsim.network.flow import Flow
from simpy import Environment
from coordsim.simulation.simulatorparams import SimulatorParams
log = logging.getLogger(__name__)


class BaseFlowGenerator:
    """ Base Flow Generator class
    All flow generator classes must inherit this class
    """
    def __init__(self, env: Environment, params: SimulatorParams):
        pass

    def generate_flow(self, flow_id, node_id) -> Tuple[float, Flow]:
        pass
