import logging
import os
import networkx as nx
import numpy as np
from datetime import datetime
from collections import defaultdict
from siminterface.simulator import ExtendedSimulatorAction
from siminterface.simulator import Simulator
from auxiliary.link import Link
from auxiliary.placement import Placement
from algorithms.greedy.metrics import CustomMetrics

log = logging.getLogger(__name__)


class G3Algo:
    """
    GPASP + Beacon
    """
    def __init__(self, simulator: Simulator):
        # Besides interaction we need the simulator reference to query all needed information. Not all information can
        # conveniently put into the simulator state, nevertheless it is justified that the algorithm can access these.
        self.simulator = simulator
        # To evaluate if some operations are feasible we need to modify the network topology, that must not happen on
        # the shared network instance

        # require the manipulation of the network topology, we
        self.network_copy = None
        # Timeout determines after which period a unused vnf is removed from a node
        self.vnf_timeout = 10
        # Custom metrics
        self.metrics = CustomMetrics()

    def init(self, network_path, service_functions_path, config_path, seed, output_id, resource_functions_path=""):
        init_state = \
            self.simulator.init(network_path, service_functions_path, config_path, seed, output_id,
                                resource_functions_path=resource_functions_path,
                                interception_callbacks=
                                {'pass_flow': self.pass_flow,
                                 'init_flow': self.init_flow,
                                 'post_forwarding': self.post_forwarding,
                                 'depart_flow': self.depart_flow,
                                 'drop_flow': self.drop_flow,
                                 'periodic': [(self.periodic_measurement, 100, 'State measurement.'),
                                              (self.periodic_remove, 10, 'Remove SF interception.')]})

        log.info(f'Network Stats after init(): {init_state.network_stats}')
        self.network_copy = self.simulator.get_network_copy()
        self.beacon = {}

    def run(self):
        placement = defaultdict(list)
        processing_rules = defaultdict(lambda : defaultdict(list))
        forwarding_rules = defaultdict(dict)
        action = ExtendedSimulatorAction(placement=placement, scheduling={}, flow_forwarding_rules=forwarding_rules,
                                         flow_processing_rules=processing_rules)
        self.simulator.apply(action)
        log.info(f'Start simulation at: {datetime.now().strftime("%H-%M-%S")}')
        self.simulator.run()
        log.info(f'End simulation at: {datetime.now().strftime("%H-%M-%S")}')
        log.info(f'Network Stats after run(): {self.simulator.get_state().network_stats}')

    def init_flow(self, flow):
        """
        <Callback>
        """
        flow['state'] = 'greedy'
        flow['target_node_id'] = flow.egress_node_id
        flow['blocked_links'] = []
        flow['intermediate_targets'] = 0
        flow['evasive_routes'] = 0
        try:
            self.set_new_path(flow)
        except nx.NetworkXNoPath:
            flow['state'] = 'drop'
            flow['path'] = []

    def pass_flow(self, flow):
        """
        <Callback>
        This is the main dynamic logic of the algorithm, whenever a flow is passed to node this function is called.
        The associated node is determined and all actions and information are computed from its perspective.
        """

        # Get state information
        state = self.simulator.get_state()
        placement = state.placement
        forwarding_rules = state.flow_forwarding_rules
        processing_rules = state.flow_processing_rules
        # The associated node
        node_id = flow.current_node_id
        node = state.network['nodes'][node_id]
        # Managment
        new_target = False

        # Is flow processed?
        if flow.is_processed():
            # Needs the state to change?
            if flow['state'] != 'departure':
                # yes => switch to departure, forward to egress node
                flow['state'] = 'departure'
                flow['target_node_id'] = flow.egress_node_id
                flow['blocked_links'] = []
                try:
                    self.set_new_path(flow)
                except nx.NetworkXNoPath:
                    flow['state'] = 'drop'
                    flow['path'] = []
        else:
            # no
            if node_id == flow['target_node_id']:
                # is flow at targte node =>
                # if flow arrived at egress node => set new random target distinct from the current node
                while flow['target_node_id'] == node_id or flow['target_node_id'] in self.beacon:
                    flow['target_node_id'] = np.random.choice(state.network['node_list'])
                flow['blocked_links'] = []
                try:
                    self.set_new_path(flow)
                    new_target = True
                except nx.NetworkXNoPath:
                    flow['state'] = 'drop'
                    flow['path'] = []

        # Determine Flow state
        if flow['state'] == 'greedy':
            # One the way to the target, needs processing
            # Placement
            # Can flow be processed at current node
            demand_p, need_placement = Placement.calculate_demand(flow, flow.current_sf, node['available_sf'],
                                                           self.simulator.params.sf_list)
            assert need_placement == (flow.current_sf not in placement[node_id]), 'False placement'

            if node['capacity'] >= demand_p:
                # yes =>  set processing rule
                processing_rules[node_id][flow.flow_id] = [flow.current_sf]
                # SF already placed?
                if need_placement:
                    # no => add VNF/SF to placement
                    placement[node_id].append(flow.current_sf)
            else:
                # no => forward
                self.forward_flow(flow, state)
                if flow['state'] != 'drop' and new_target:
                    flow['intermediate_targets'] += 1

        elif flow['state'] == 'departure':
            # Return to destination as soon as possible, no more processing necessary
            if node_id != flow.egress_node_id:
                self.forward_flow(flow, state)

        if flow['state'] == 'drop':
            # Something went legitimate wrong => clear remaing rules => let it drop
            processing_rules[node_id].pop(flow.flow_id, None)
            forwarding_rules[node_id].pop(flow.flow_id, None)
            if node_id not in self.beacon:
                self.beacon[node_id] = True
                self.simulator.timeout_callback(self.remove_beacon_event(node_id), 2, 'Remove beacon')

        # Apply state to simulator
        self.simulator.apply(state.derive_action())

    def forward_flow(self, flow, state):
        """
        This function will handle the necessary actions to forward a flow from the associated node. A call to this
        function requires the flow to have a precomputed path. If a flow can be forwarded along th precomputed path
        the flow_forwarding_rules for the associated node will be set. If a flow cannot be forwarded, due missing link
        resources, all incident links will be checked and all unsuitable links will be added to the blocked link list
        of the flow. Subsequent a new path is attempted to calculate.
        """

        node_id = flow.current_node_id
        assert len(flow['path']) > 0
        next_neighbor_id = flow['path'].pop(0)
        edge = self.simulator.params.network[node_id][next_neighbor_id]

        # Can forward?
        if (edge['remaining_cap'] >= flow.dr):
            # yes => set forwarding rule
            state.flow_forwarding_rules[node_id][flow.flow_id] = next_neighbor_id
        else:
            # no => adapt path
            # remove all incident links which cannot be crossed
            for incident_edge in self.simulator.params.network.edges(node_id, data=True):
                if (incident_edge[2]['remaining_cap'] - flow.dr) < 0:
                    link = Link(incident_edge[0], incident_edge[1], **incident_edge[2])
                    if link not in flow['blocked_links']:
                        flow['blocked_links'].append(link)
            try:
                # Try to find new path
                self.set_new_path(flow)
                assert len(flow['path']) > 0
                next_neighbor_id = flow['path'].pop(0)
                # Set forwarding rule
                state.flow_forwarding_rules[node_id][flow.flow_id] = next_neighbor_id
                flow['evasive_routes'] += 1
            except nx.NetworkXNoPath:
                flow['state'] = 'drop'
                flow['path'] = []
                flow['death_cause'] = 'Forward: all incident links are exhausted'

    def set_new_path(self, flow):
        """
        Calculate and set shortest path to the target node defined by target_node_id, taking blocked links into account.
        """
        network = self.simulator.get_network_copy()
        for link in flow['blocked_links']:
            network.remove_edge(link[0], link[1])
        for n in self.beacon:
            if n != flow.current_node_id and flow.current_node_id != flow['target_node_id']:
                network.remove_node(n)
        try:
            shortest_path = nx.shortest_path(network, flow.current_node_id, flow['target_node_id'],
                                             weight='delay')
            shortest_path.pop(0)
            flow['path'] = shortest_path
        except nx.NetworkXNoPath:
            raise


    def periodic_measurement(self):
        """
        <Callback>
        """
        #self.simulator.write_state()
        state = self.simulator.get_state()

        log.warning(f'Network Stats after time: {state.simulation_time} / 'f'{state.network_stats} / '
                    f' {self.metrics.get_metrics()} / {state.network["metrics"]}')

    def periodic_remove(self):
        """
         <Callback>
        """
        state = self.simulator.get_state()
        for node_id, node_data in state.network['nodes'].items():
            for sf, sf_data in node_data['available_sf'].items():
                if (sf_data['load'] == 0) and ((state.simulation_time - sf_data['last_requested']) > self.vnf_timeout):
                    state.placement[node_id].remove(sf)
        self.simulator.apply(state.derive_action())

    def post_forwarding(self, node_id, flow):
        """
        <Callback>
        """
        # Direct access for speed gain
        self.simulator.params.flow_forwarding_rules[node_id].pop(flow.flow_id, None)

    def depart_flow(self, flow):
        self.metrics.processed_flow(flow)

    def drop_flow(self, flow):
        self.metrics.dropped_flow(flow)

    def remove_beacon_event(self, node):
        def f():
            del self.beacon[node]
            return
        return f


def main():
    # Simulator params
    args = {
        'network': '../../../../params/networks/dfn_58.graphml',
        'service_functions': '../../../../params/services/3sfcs.yaml',
        'resource_functions': '../../../../params/services/resource_functions',
        'config': '../../../../params/config/probabilistic_discrete_config.yaml',
        'seed': 9999,
        'output_id': 'g3-out'
    }

    # Setup logging
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    os.makedirs(f'{args["output_id"]}/logs/{os.path.basename(args["network"])}', exist_ok=True)
    logging.basicConfig(filename=
                        f'{args["output_id"]}/logs/{os.path.basename(args["network"])}/'
                        f'{os.path.basename(args["network"])}_{timestamp}_{args["seed"]}.log',
                        level=logging.INFO)
    logging.getLogger('coordsim').setLevel(logging.ERROR)
    logging.getLogger('coordsim.reader').setLevel(logging.INFO)
    simulator = Simulator(test_mode=True)

    # Setup algorithm
    algo = G3Algo(simulator)
    algo.init(os.path.abspath(args['network']),
              os.path.abspath(args['service_functions']),
              os.path.abspath(args['config']),
              args['seed'],
              args['output_id'],
              resource_functions_path=os.path.abspath(args['resource_functions']))
    # Execute orchestrated simulation
    algo.run()


if __name__ == "__main__":
    main()