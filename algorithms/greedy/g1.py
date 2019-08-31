import logging
import os
import copy
import networkx as nx
import numpy as np
from datetime import datetime
from collections import defaultdict
from siminterface.simulator import ExtendedSimulatorAction
from siminterface.simulator import Simulator

log = logging.getLogger(__name__)


class G1Algo:
    def __init__(self, simulator: Simulator):
        # Besides interaction we need the simulator reference to query all needed information. Not all information can
        # conveniently put into the simulator state, nevertheless it is justified that the algorithm can access these.
        self.simulator = simulator
        # To evaluate if some operations are feasible we need to modify the network topology, that must not happen on
        # the shared network instance

        # require the manipulation of the network topology, we
        self.network_copy = None
        self.initial_number_of_edges = 0

    def init(self, network_path, service_functions_path, config_path, seed, resource_functions_path=""):
        init_state = self.simulator.init(network_path,
                                         service_functions_path,
                                         config_path, seed,
                                         resource_functions_path=resource_functions_path,
                                         interception_callbacks={'pass_flow': self.pass_flow,
                                                                 'init_flow': self.init_flow,
                                                                 'periodic': [(self.periodic, 10, 'State measurement.')]})

        log.info("Network Stats after init(): %s", init_state.network_stats)
        self.network_copy = self.simulator.get_network_copy()
        self.initial_number_of_edges = self.network_copy.number_of_edges()

    def run(self):
        placement = defaultdict(list)
        processing_rules = defaultdict(lambda : defaultdict(list))
        forwarding_rules = defaultdict(dict)
        action = ExtendedSimulatorAction(placement=placement, scheduling={}, flow_forwarding_rules=forwarding_rules,
                                         flow_processing_rules=processing_rules)
        self.simulator.apply(action)
        self.simulator.run()
        # for f in self.simulator.metrics['flows']:
        #     print(f'Flow {f.flow_id}, ingress {f.ingress_node_id}, egress {f.egress_node_id},'
        #           f' path delay {f.path_delay}, i2e path delay {nx.shortest_path_length(self.simulator.params.network, f.ingress_node_id, f.egress_node_id, weight="delay")}')
        log.info("Network Stats after init(): %s", self.simulator.get_state().network_stats)

    def init_flow(self, flow):
        """
        <Callback>
        """
        flow['state'] = 'greedy'
        flow['target_node_id'] = flow.egress_node_id
        flow['blocked_links'] = []
        try:
            self.set_new_path(flow)
        except nx.NetworkXNoPath:
            flow['state'] = 'drop'
            flow['path'] = []


    def pass_flow(self, flow):
        """
        <Callback>
        """

        # Get state information
        id = flow.flow_id
        state = self.simulator.get_state()
        placement = state.placement
        scheduling = {}
        forwarding_rules = state.flow_forwarding_rules
        processing_rules = state.flow_processing_rules
        node_id = flow.current_node_id
        node = state.network['nodes'][node_id]

        # Is flow processed?
        if flow.is_processed():
            # yes => switch to departure, forward to egress node
            flow['state'] = 'departure'
            flow['target_node_id'] = flow.egress_node_id
            flow['blocked_links'] = []
            try:
                self.set_new_path(flow)
            except nx.NetworkXNoPath:
                flow['state'] = 'drop'
                flow['path'] = []
        elif node_id == flow['target_node_id']:
            # no => if flow arrived at egress node => set new random target distinct from the current node
            while flow['target_node_id'] == node_id:
                flow['target_node_id'] = np.random.choice(state.network['node_list'])
            flow['blocked_links'] = []
            try:
                self.set_new_path(flow)
            except nx.NetworkXNoPath:
                flow['state'] = 'drop'
                flow['path'] = []

        # Determine Flow state
        if flow['state'] == 'greedy':
            # One the way to the target, needs processing
            # Placement
            # SF already placed?
            if flow.current_sf in placement[node_id]:
                # yes
                demand = self.calculate_demand(flow, state)
                # Can add?
                if node['capacity'] >= demand:
                    # yes =>  set processing rule
                    processing_rules[node_id][flow.flow_id] = [flow.current_sf]
                else:
                    # no => forward
                    self.routing(flow, state)
            else:
                # no => test placement to calculate demand, no real placement yet
                state.network['nodes'][flow.current_node_id]['available_sf'][flow.current_sf] = {'load': 0.0}
                demand = self.calculate_demand(flow, state)
                # Can add?
                if node['capacity'] >= demand:
                    # yes => place SF and set processing rule
                    placement[node_id].append(flow.current_sf)
                    processing_rules[node_id][flow.flow_id] = [flow.current_sf]
                else:
                    # no => remove test placement
                    del state.network['nodes'][flow.current_node_id]['available_sf'][flow.current_sf]
                    # Forward
                    self.routing(flow, state)

        elif flow['state'] == 'departure':
            # Return to destination as soon as possible, no more processing necessary
            if node_id != flow.egress_node_id:
                self.routing(flow, state)

        elif flow['state'] == 'drop':
            # Something went legitimate wrong => clear remaing rules => let it drop
            processing_rules[node_id].pop(flow.flow_id, None)
            forwarding_rules[node_id].pop(flow.flow_id, None)

        # Apply state to simulator
        self.simulator.apply(ExtendedSimulatorAction(placement, scheduling, forwarding_rules, processing_rules))

    def routing(self, flow, state):
        """
        Calculate and set shortest path to the target node defined by target_node_id. If no path is available the flow
        will switch to drop state.
        """

        node_id = flow.current_node_id
        assert len(flow['path']) > 0
        next_neighbor_id = flow['path'].pop(0)
        edge = self.simulator.params.network[node_id][next_neighbor_id]

        # Can forward?
        if (edge['remaining_cap'] - flow.dr) >= 0:
            # yes => set forwarding rule
            state.flow_forwarding_rules[node_id][flow.flow_id] = next_neighbor_id
        else:
            # no => adapt path
            # remove all incident links which cannot be crossed
            for incident_edge in self.simulator.params.network.edges(node_id, data=True):
                if (incident_edge[2]['remaining_cap'] - flow.dr) < 0:
                    flow['blocked_links'].append(copy.deepcopy(incident_edge))
            try:
                # Try to find new path
                self.set_new_path(flow)
                assert len(flow['path']) > 0
                next_neighbor_id = flow['path'].pop(0)
                # Set forwarding rule
                state.flow_forwarding_rules[node_id][flow.flow_id] = next_neighbor_id
            except nx.NetworkXNoPath:
                flow['state'] = 'drop'
                flow['path'] = []

    def set_new_path(self, flow):
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
                self.network_copy.add_edge(link[0], link[1], delay=link[2]['delay'])
            assert self.network_copy.number_of_edges() == self.simulator.params.network.number_of_edges(), 'Edge count mismatch!'
            assert self.network_copy.number_of_edges() == self.initial_number_of_edges, 'Edge count mismatch!'


    def calculate_demand(self, flow, state) -> float:
        # Calculate the demanded capacity when the flow is processed at this node
        demanded_total_capacity = 0.0
        for sf_i, sf_data in state.network['nodes'][flow.current_node_id]['available_sf'].items():
            if flow.current_sf == sf_i:
                # Include flows data rate in requested sf capacity calculation
                demanded_total_capacity += state.service_functions[sf_i]['resource_function'](sf_data['load'] + flow.dr)
            else:
                demanded_total_capacity += state.service_functions[sf_i]['resource_function'](sf_data['load'])
        return demanded_total_capacity

    def periodic(self):
        """
        <Callback>
        """
        self.simulator.write_state()

    def remove_unused_sf(self):
        pass


def main():
    # Simulator params
    args = {
        'network': '../../params/networks/dfn.graphml',
        'service_functions': '../../params/services/abc.yaml',
        'resource_functions': '../../params/services/resource_functions',
        'config': '../../params/config/probabilistic_discrete_config.yaml',
        'seed': 9999
    }

    # Setup logging
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    os.makedirs('logs', exist_ok=True)
    os.makedirs(f'logs/{os.path.basename(args["network"])}', exist_ok=True)
    logging.basicConfig(filename=f'logs/{os.path.basename(args["network"])}/{os.path.basename(args["network"])}_{timestamp}_{args["seed"]}.log',
                        level=logging.INFO)
    logging.getLogger('coordsim').setLevel(logging.INFO)
    simulator = Simulator(test_mode=True)

    # Setup algorithm
    algo = G1Algo(simulator)
    algo.init(os.path.abspath(args['network']),
              os.path.abspath(args['service_functions']),
              os.path.abspath(args['config']),
              args['seed'],
              resource_functions_path=os.path.abspath(args['resource_functions']))
    # Execute orchestrated simulation
    algo.run()


if __name__ == "__main__":
    main()