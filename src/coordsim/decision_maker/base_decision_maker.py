from simpy import Environment
from coordsim.network.flow import Flow
from coordsim.simulation.simulatorparams import SimulatorParams
from typing import Union


class BaseDecisionMaker:
    """ Base Decision Maker class
    All decision maker classes must inherit this class
    """
    def __init__(self, env: Environment, params: SimulatorParams):
        self.env = env
        self.params: SimulatorParams = params

    def decide_next_node(self, flow: Flow) -> Union[None, str]:
        """ Decide next node for a flow
        Returns:
            - None if destination cannot be decided or unavailable
            - str: node_id of next node.
        """
        raise NotImplementedError
