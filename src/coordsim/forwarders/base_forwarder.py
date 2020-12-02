from simpy import Environment
from coordsim.network.flow import Flow
from coordsim.simulation.simulatorparams import SimulatorParams


class BaseFlowForwarder:
    """ Base Flow Forwarder class
    All flow forwarder classes must inherit this class
    """
    def __init__(self, env: Environment, params: SimulatorParams):
        pass

    def forward_flow(self, flow: Flow, next_node) -> bool:
        pass
