from simpy import Environment
from coordsim.network.flow import Flow
from coordsim.simulation.simulatorparams import SimulatorParams


class BaseFlowProcessor:
    """ Base Flow Processor class
    All flow processor classes must inherit this class
    """
    def __init__(self, env: Environment, params: SimulatorParams):
        pass

    def process_flow(self, flow: Flow) -> bool:
        """ Process the flow at its requested SF if resources are available
        Returns:
            - bool: the status of the flow whether it was processed or not
        """
        pass
