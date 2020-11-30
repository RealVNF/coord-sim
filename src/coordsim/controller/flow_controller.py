import logging
import numpy as np
from coordsim.network.flow import Flow
from coordsim.simulation.simulatorparams import SimulatorParams
from coordsim.controller import BaseController
from spinterface import SimulatorAction, SimulatorState
log = logging.getLogger(__name__)


class SPRState:
    def __init__(self, flow: Flow, network: dict, sfcs: dict, network_stats: dict):
        """
        SPRState Class for SPR algorithm
        """
        self.flow = flow
        self.network = network
        self.sfcs = sfcs
        self.network_stats = network_stats


class FlowController(BaseController):
    """
    This is a flow controller class. It makes per-flow decisions based on an external decision
    """

    def __init__(self, env, params, simulator):
        super().__init__(env, params, simulator)
        self.episode = 0

    def get_init_state(self):
        # Run the environment for one step to get initial stats.
        flow = self.env.run(until=self.params.flow_trigger)

        # Parse the NetworkX object into a dict format specified in SimulatorState. This is done to account
        # for changing node remaining capacities.
        # Also, parse the network stats and prepare it in SimulatorState format.
        self.parse_network()
        self.network_metrics()
        if self.params.prediction:
            self.update_prediction()
        simulator_state = SPRState(flow, self.params.network, self.params.sfc_list, self.network_stats)
        return simulator_state

    def get_next_state(self, action: SimulatorAction) -> SimulatorState:
        """
        Apply a decision and run until next flow arrives
        """

        # self.writer.write_action_result(self.episode, self.env.now, action)

        # Get the new placement from the action passed by the RL agent
        # Modify and set the placement parameter of the instantiated simulator object.
        flow = action.flow
        currrent_node = flow.current_node_id
        current_sf = flow.current_sf
        # Apply placement if decision is 0: process at this node and no instance is there
        if action.destination_node_id == flow.current_node_id:
            # check if instance is already here
            available_sf = self.simulator.params.network.nodes[flow.current_node_id]['available_sf']
            if flow.current_sf not in list(available_sf.keys()) and not flow.current_sf == "EG":
                # If no instance exists: place instance in the node
                self.simulator.params.network.nodes[currrent_node]['available_sf'][current_sf] = {
                    'load': 0.0,
                    'last_active': self.simulator.env.now,
                    'startup_time': self.simulator.env.now
                }

        # Check active VNFs in the network
        self.update_vnf_active_status()

        # Create a placement
        sf_placement = {}
        for node in self.simulator.params.network.nodes(data=True):
            node_id = node[0]
            node_available_sf = list(node[1]['available_sf'].keys())
            sf_placement[node_id] = node_available_sf
        self.simulator.params.sf_placement = sf_placement
        self.env.process(
            self.simulator.handle_flow(
                flow,
                decision=action.destination_node_id
            )
        )
        flow = self.env.run(until=self.params.flow_trigger)
        self.parse_network()
        self.network_metrics()
        # Check to see if traffic prediction is enabled to provide future traffic not current traffic
        if self.params.prediction:
            self.update_prediction()
        # Create a new SimulatorState object to pass to the RL Agent
        simulator_state = SPRState(flow, self.params.network, self.params.sfc_list, self.network_stats)
        return simulator_state

    def update_vnf_active_status(self):
        """ Update the VNF status in nodes and remove inactive VNFs """
        for node in self.params.network.nodes(data=True):
            n_id = node[0]
            now = self.env.now
            timeout = self.params.vnf_timeout
            # Using dict here to create a copy. Solves RuntimeError: dict size changed during iteration
            available_sf: dict = dict(self.simulator.params.network.nodes[n_id]['available_sf'])
            for sf, sf_params in available_sf.items():
                # Remove VNFs if not active and timeout passed
                if sf_params['load'] == 0.0:
                    # VNF is not active
                    if sf_params['last_active'] < now - timeout:
                        # VNF has not been active for `timeout` time: remove
                        del self.simulator.params.network.nodes[n_id]['available_sf'][sf]

                else:
                    # Node is active: update `last_active` time to be `now`
                    self.simulator.params.network.nodes[n_id]['available_sf'][sf]['last_active'] = now
