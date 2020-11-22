import logging
import numpy as np
from coordsim.network.flow import Flow
from coordsim.simulation.simulatorparams import SimulatorParams
from coordsim.controller import BaseController
from spinterface import SimulatorAction, SimulatorState
log = logging.getLogger(__name__)


class DurationController(BaseController):
    """
    This is the default decision maker class. It makes flow decisions based on the scheduling table
    """

    def __init__(self, env, params, simulator):
        super().__init__(env, params, simulator)
        self.episode = 0
        self.duration = self.params.run_duration

    def get_init_state(self):
        # Run the environment for one step to get initial stats.
        self.env.step()

        # Parse the NetworkX object into a dict format specified in SimulatorState. This is done to account
        # for changing node remaining capacities.
        # Also, parse the network stats and prepare it in SimulatorState format.
        self.parse_network()
        self.network_metrics()
        if self.params.prediction:
            self.update_prediction()
        simulator_state = SimulatorState(self.network_dict, self.params.sf_placement, self.params.sfc_list,
                                         self.params.sf_list, self.traffic, self.network_stats)
        return simulator_state

    def get_next_state(self, action: SimulatorAction) -> SimulatorState:
        """ Apply a decision and run until a specified duration has finished
        """

        # self.writer.write_action_result(self.episode, self.env.now, action)

        # Get the new placement from the action passed by the RL agent
        # Modify and set the placement parameter of the instantiated simulator object.
        self.params.sf_placement = action.placement
        # Update which sf is available at which node
        for node_id, placed_sf_list in action.placement.items():
            available = {}
            # Keep only SFs which still process
            for sf, sf_data in self.params.network.nodes[node_id]['available_sf'].items():
                if sf_data['load'] != 0:
                    available[sf] = sf_data
            # Add all SFs which are in the placement
            for sf in placed_sf_list:
                if sf not in available.keys():
                    available[sf] = available.get(sf, {
                        'load': 0.0,
                        'last_active': self.env.now,
                        'startup_time': self.env.now
                    })
            self.params.network.nodes[node_id]['available_sf'] = available

        # Get the new schedule from the SimulatorAction
        # Set it in the params of the instantiated simulator object.
        self.params.schedule = action.scheduling

        runtime_steps = self.duration * self.params.run_times
        self.params.logger.debug("Running simulator until time step %s", runtime_steps)
        self.env.run(until=runtime_steps)
        self.parse_network()
        self.network_metrics()
        # Check to see if traffic prediction is enabled to provide future traffic not current traffic
        if self.params.prediction:
            self.update_prediction()
        # Create a new SimulatorState object to pass to the RL Agent
        simulator_state = SimulatorState(self.network_dict, self.params.sf_placement, self.params.sfc_list,
                                         self.params.sf_list, self.traffic, self.network_stats)
        return simulator_state
