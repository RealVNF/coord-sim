from simpy import Environment
from coordsim.network.flow import Flow
from coordsim.simulation.simulatorparams import SimulatorParams
from typing import Union


class BaseController:
    """
    BaseController class
    Controls the duration between decisions and returns a simulator state to be passed
    to the controlling algorithm
    """
    def __init__(self, env: Environment, params: SimulatorParams):
        self.env = env
        self.params = params

    def apply_action(self, action, init=False):
        """
        Apply the action from the control algorithm
        Returns:
            - SimulatorState or a child class
        """
        raise NotImplementedError
