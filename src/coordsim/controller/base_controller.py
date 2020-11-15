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

    def get_init_state(self):
        """ Return the init state """
        raise NotImplementedError

    def get_next_state(self, action=None):
        """
        Apply the action from the control algorithm
        Returns:
            - SimulatorState or a child class
        """
        raise NotImplementedError
