from siminterface.simulator import Simulator
import logging
import os
from datetime import datetime

from siminterface.simulator import ExtendedSimulatorAction
from siminterface.simulator import Simulator

log = logging.getLogger(__name__)


class StaticTriangleAlgo:
    """
    This algorithm is used as test instance for the simulator. The placement and routing is predefined, but the
    corresponding control entries are registered dynamically at run time.
    The algorithm interacts with the simulator in various ways. Callback functions are registered, so that
    the internal flowsimulator can directly execute the algorithm at certain events. In some cases the algorithm is
    then provided with additional event information. In general the algorithm queries the current network state from
    the simulator interface. The simulator state is composed of original and referenced data. Therefore the algorithm
    directly operates on parts of the internal simulator state. These parts are restricted on placement and node
    behavior rules.
    """

    def __init__(self, simulator: Simulator):
        self.simulator = simulator

    def init(self, network_path, service_functions_path, config_path, seed):
        """
        The algorithm initializes the simulator by its own.
        """

        init_state = self.simulator.init(network_path,
                                         service_functions_path,
                                         config_path, seed,
                                         interception_callbacks={'pass_flow': self.pass_flow,
                                                                 'periodic_measurement': self.periodic_measurement})

        log.info("Network Stats after init(): %s", init_state.network_stats)

    def run(self):
        """
        Need to call apply once to start simulation. Parameters are all empty because the algorithm will interact
        with the simulator through callbacks.
        """

        placement = {
            'pop0': [],
            'pop1': [],
            'pop2': []
        }
        processing_rules = {'pop0': {},
                            'pop1': {},
                            'pop2': {}}
        forwarding_rules = {'pop0': {},
                            'pop1': {},
                            'pop2': {}}
        action = ExtendedSimulatorAction(placement=placement, scheduling={}, flow_forwarding_rules=forwarding_rules,
                                         flow_processing_rules=processing_rules)
        self.simulator.apply(action)

    def pass_flow(self, flow):
        """
        Callback function.
        Main interaction point between algorithm and simulator. This function is called every time a flow is passed to
        a node. A flow f is passed to a node n when:
        - f is spawned at n
        - f arrives by forwarding by n
        - f was processed by SF placed at n
        """

        state = self.simulator.get_simulator_state()
        placement = state.placement
        processing_rules = state.flow_processing_rules
        forwarding_rules = state.flow_forwarding_rules
        node_id = flow.current_node_id

        if node_id == 'pop0':
            # The first flow will trigger the placement of SF 'a'
            if len(placement[node_id]) == 0:
                placement[node_id].append('a')

            if flow.flow_id not in processing_rules[node_id]:
                # Arriving flows are instructed to be processed by 'a' at this node
                processing_rules[node_id][flow.flow_id] = ['a']
            else:
                # After processing flows will be forwarded to 'pop1'
                forwarding_rules[node_id][flow.flow_id] = 'pop1'

        elif node_id == 'pop1':
            # No processing only forwarding
            forwarding_rules[node_id][flow.flow_id] = 'pop2'

        elif node_id == 'pop2':
            # The first flow will trigger the placement of SFs 'b' and 'c'
            if len(placement[node_id]) == 0:
                placement[node_id].append('b')
                placement[node_id].append('c')

            if flow.flow_id not in processing_rules[node_id]:
                # Arriving flows are instructed to be processed by 'b' and 'c' at this node
                processing_rules[node_id][flow.flow_id] = ['b', 'c']

    def periodic_measurement(self):
        """
        Callback function.
        Called after a the specified inter_measurement interval. Used to record simulator state
        in regular intervals.
        """
        self.simulator.write_simulator_state()


def main():
    # Simulator params
    args = {
        'network': '../../../params/networks/triangle.graphml',
        'service_functions': '../../../params/services/abc.yaml',
        'config': '../../../params/config/sim_config.yaml',
        'seed': 9999
    }

    # Setup logging
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    os.makedirs('logs', exist_ok=True)
    logging.basicConfig(filename=f'logs/{os.path.basename(args["network"])}_{timestamp}_{args["seed"]}.log',
                        level=logging.INFO)
    logging.getLogger('coordsim').setLevel(logging.INFO)
    simulator = Simulator(test_mode=True)

    # Setup algorithm
    algo = StaticTriangleAlgo(simulator)
    algo.init(os.path.abspath(args['network']),
              os.path.abspath(args['service_functions']),
              os.path.abspath(args['config']),
              args['seed'])
    # Execute orchestrated simulation
    algo.run()


if __name__ == "__main__":
    main()