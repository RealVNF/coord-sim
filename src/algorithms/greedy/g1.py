import logging
import os
import random
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


class G1Algo:
    """
    GPASP base algorithm
    """
    def __init__(self, simulator: Simulator):
        # Besides interaction we need the simulator reference to query all needed information. Not all information can
        # conveniently put into the simulator state, nevertheless it is justified that the algorithm can access these.
        self.simulator = simulator
        # To evaluate if some operations are feasible we need to modify the network topology, that must not happen on
        # the shared network instance
        self.network_copy = None
        # Timeout determines, after which period a unused vnf is removed from a node
        self.vnf_timeout = 10
        # Custom metrics
        self.metrics = CustomMetrics()

    def init(self, network_path, service_functions_path, config_path, seed, output_path, resource_functions_path=""):
        init_state = \
            self.simulator.init(network_path, service_functions_path, config_path, seed, output_path,
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
        self.simulator.write_state()
        log.info(f'Network Stats after run(): {self.simulator.get_state().network_stats}')
        self.simulator.write_decisions()

    def init_flow(self, flow):
        """
        <Callback>
        Called whenever a flow is initialized.
        """
        flow['state'] = 'greedy'
        flow['target_node_id'] = flow.egress_node_id
        flow['blocked_links'] = []
        flow['metrics'] = {}
        flow['metrics']['intermediate_targets'] = 0
        flow['metrics']['evasive_routes'] = 0
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
        self.simulator.metrics.add_decision(node_id)
        # Algorithm management
        new_target = False
        # Metric management
        self.metrics['node_visit'][node_id] += 1

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
            # no, not fully processed
            if node_id == flow['target_node_id']:
                # has flow arrived at targte node => set new random target distinct from the current node
                while flow['target_node_id'] == node_id:
                    flow['target_node_id'] = random.choice(state.network['node_list'])
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
            # Can flow be processed at current node?
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
                    flow['metrics']['intermediate_targets'] += 1

        elif flow['state'] == 'departure':
            # Return to destination as soon as possible, no more processing necessary
            if node_id != flow.egress_node_id:
                self.forward_flow(flow, state)

        if flow['state'] == 'drop':
            # Something went legitimate wrong => clear remaining rules => let it drop
            self.metrics['node_mortality'][node_id] += 1
            processing_rules[node_id].pop(flow.flow_id, None)
            forwarding_rules[node_id].pop(flow.flow_id, None)

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
        if edge['remaining_cap'] >= flow.dr:
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
                flow['metrics']['evasive_routes'] += 1
            except nx.NetworkXNoPath:
                flow['state'] = 'drop'
                flow['path'] = []
                flow['death_cause'] = 'Forward: all incident links are exhausted'

    def set_new_path(self, flow):
        """
        Calculate and set shortest path to the target node defined by target_node_id, taking blocked links into account.
        """
        assert self.network_copy.number_of_edges() == self.simulator.params.network.number_of_edges(), \
            f'Pre edge count mismatch with internal state! Flow {flow.flow_id}'
        for link in flow['blocked_links']:
            self.network_copy.remove_edge(link[0], link[1])
        try:
            shortest_path = nx.shortest_path(self.network_copy, flow.current_node_id, flow['target_node_id'],
                                             weight='delay')
            shortest_path.pop(0)
            flow['path'] = shortest_path
        except nx.NetworkXNoPath:
            raise
        finally:
            for link in flow['blocked_links']:
                self.network_copy.add_edge(link[0], link[1], **link.attributes)
            assert self.network_copy.number_of_edges() == self.simulator.params.network.number_of_edges(), 'Post edge count mismatch with internal state!'

    def periodic_measurement(self):
        """
        <Callback>
        Called periodically to capture the simulator state.
        """
        state = self.simulator.write_state()
        log.warning(f'Network Stats after time: {state.simulation_time} / 'f'{state.network_stats} / '
                    f' {self.metrics.get_metrics()} / {state.network["metrics"]}')

    def periodic_remove(self):
        """
         <Callback>
         Called periodically to check if vnfs have to be removed.
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
        Called to remove no longer used forwarding rules, keep it overseeable.
        """
        # Direct access for speed gain
        self.simulator.params.flow_forwarding_rules[node_id].pop(flow.flow_id, None)

    def depart_flow(self, flow):
        """
        <Callback>
        Called to record custom metrics.
        """
        self.metrics.processed_flow(flow)

    def drop_flow(self, flow):
        """
        <Callback>
        Called to record custom metrics.
        """
        self.metrics.dropped_flow(flow)


def main():
    # Simulator params
    network = 'bics_34.graphml'
    args = {
        'network': f'../../../params/networks/{network}',
        'service_functions': '../../../params/services/3sfcs.yaml',
        'resource_functions': '../../../params/services/resource_functions',
        'config': '../../../params/config/probabilistic_discrete_config.yaml',
        'seed': 9999,
        'output_path': f'g1-out/{network}'
    }

    # Setup logging
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    os.makedirs(f'{args["output_path"]}/logs', exist_ok=True)
    logging.basicConfig(filename=
                        f'{args["output_path"]}/logs/{os.path.basename(args["network"])}_{timestamp}_{args["seed"]}.log',
                        level=logging.INFO)
    logging.getLogger('coordsim').setLevel(logging.ERROR)
    logging.getLogger('coordsim.reader').setLevel(logging.INFO)
    simulator = Simulator(test_mode=True)

    # Setup algorithm
    algo = G1Algo(simulator)
    algo.init(os.path.abspath(args['network']),
              os.path.abspath(args['service_functions']),
              os.path.abspath(args['config']),
              args['seed'],
              args['output_path'],
              resource_functions_path=os.path.abspath(args['resource_functions']))
    # Execute orchestrated simulation
    algo.run()


if __name__ == "__main__":
    main()