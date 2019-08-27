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
    directly operates on parts of the internal simulator state. Nevertheless the algorithm has to call simulator.apply
    to let all changes come into effect.
    """

    def __init__(self, simulator: Simulator):
        self.simulator = simulator

    def init(self, network_path, service_functions_path, config_path, seed, resource_functions_path=""):
        """
        The algorithm initializes the simulator by its own.
        """

        init_state = self.simulator.init(network_path,
                                         service_functions_path,
                                         config_path, seed,
                                         resource_functions_path=resource_functions_path,
                                         interception_callbacks={'pass_flow': self.pass_flow,
                                                                 'periodic': [(self.periodic_measurement, 10,
                                                                               "measurement interception")]})

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
        self.simulator.run()
        log.info("Network Stats after init(): %s", self.simulator.get_state().network_stats)

    def pass_flow(self, flow):
        """
        Callback function.
        Main interaction point between algorithm and simulator. This function is called every time a flow is passed to
        a node. A flow f is passed to a node n when:
        - f is spawned at n
        - f arrives by forwarding by n
        - f was processed by SF placed at n
        """

        state = self.simulator.get_state()
        placement = state.placement
        scheduling = {}
        forwarding_rules = state.flow_forwarding_rules
        processing_rules = state.flow_processing_rules
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

        # Although the algorithm directly manipultes flowsimulator internal state as placement, forwarding_rules and
        # processing_rules it needs to call apply to correctly set the state
        self.simulator.apply(ExtendedSimulatorAction(placement, scheduling, forwarding_rules, processing_rules))

    def periodic_measurement(self):
        """
        Callback function.
        Called after the specified interval. Used to record simulator state
        in regular intervals.
        """
        self.simulator.write_state()


def main():
    # Simulator params
    args = {
        'network': '../../../params/networks/triangle.graphml',
        'service_functions': '../../../params/services/abc.yaml',
        'resource_functions': '../../../params/services/resource_functions',
        'config': '../../../params/config/debug_config.yaml',
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
              args['seed'],
              resource_functions_path=os.path.abspath(args['resource_functions']))
    # Execute orchestrated simulation
    algo.run()


if __name__ == "__main__":
    main()
