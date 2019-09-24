import logging
import os
import json
import operator
from collections import defaultdict
from datetime import datetime
import networkx as nx
import numpy as np
from auxiliary.link import Link
from auxiliary.placement import Placement
from siminterface.simulator import ExtendedSimulatorAction
from siminterface.simulator import Simulator

log = logging.getLogger(__name__)


class NoCandidateException(Exception):
    """
    Signal that no suitable routing/placement candidate could be determined
    """
    pass


class TPKAlgo:
    def __init__(self, simulator: Simulator):
        # Besides interaction we need the simulator reference to query all needed information. Not all information can
        # conveniently put into the simulator state, nevertheless it is justified that the algorithm can access these.
        self.simulator = simulator
        # To evaluate if some operations are feasible we need to modify the network topology, that must not happen on
        # the shared network instance
        self.network_copy = None
        # Timeout determines, after which period a unused vnf is removed from a node
        self.vnf_timeout = 10

    def init(self, network_path, connectivity_path, service_functions_path, config_path, seed, output_id,
             resource_functions_path=""):
        init_state = self.simulator.init(network_path, service_functions_path, config_path, seed, output_id,
                                         resource_functions_path=resource_functions_path,
                                         interception_callbacks=
                                         {'pass_flow': self.pass_flow,
                                          'init_flow': self.init_flow,
                                          'depart_flow': self.depart_flow,
                                          'drop_flow': self.drop_flow,
                                          'periodic': [(self.periodic_measurement, 100, 'Measurement'),
                                                       (self.periodic_remove, 10, 'Remove SF interception.')]})

        log.info(f'Network Stats after init(): {init_state.network_stats}')

        self.network_copy = self.simulator.get_network_copy()
        # nx.draw(self.network_copy)
        # plt.show()
        self.network_diameter = nx.diameter(self.network_copy)

        self.asps = dict(nx.all_pairs_dijkstra_path(self.network_copy, weight='delay'))
        self.apsp_length = dict(nx.all_pairs_dijkstra_path_length(self.network_copy, weight='delay'))

        # Record how often a flow was passed to a node, used to calculate score
        self.node_mortality = defaultdict(int)
        # Record current general load, used to calculate score
        self.occupancy_list = defaultdict(list)

        # Load connectivity measurement
        node_connectivity_json_file = open(f'{connectivity_path}/{os.path.basename(network_path)}_node_con.json')
        edge_connectivity_json_file = open(f'{connectivity_path}/{os.path.basename(network_path)}_edge_con.json')
        self.node_connectivity = json.loads(node_connectivity_json_file.read())
        self.edge_connectivity = json.loads(edge_connectivity_json_file.read())
        #self.degree_centrality = nx.degree_centrality(self.network_copy)
        #self.closeness_centrality = nx.closeness_centrality(self.network_copy, distance='delay')
        #self.betweenness_centrality = nx.betweenness_centrality(self.network_copy, weight='delay')

        # Set periodic callbacks directly before the flowsimulator can
        #periodic = [(self.periodic_measurement, 100, 'Measurement'),
        #            (self.periodic_remove, 10, 'Remove SF interception.')]
        #self.simulator.params.interception_callbacks['periodic'] = periodic

    def run(self):
        placement = defaultdict(list)
        processing_rules = defaultdict(lambda: defaultdict(list))
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
        flow['state'] = 'transit'
        flow['blocked_links'] = []
        try:
            self.plan_placement(flow)
            self.try_set_new_path(flow)
        except NoCandidateException:
            flow['state'] = 'drop'
            flow['path'] = []
            print('No candidate')

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
        exec_node_id = flow.current_node_id
        exec_node = state.network['nodes'][exec_node_id]

        if (flow.flow_id, flow.dr) not in self.occupancy_list[exec_node_id]:
            self.occupancy_list[exec_node_id].append((flow.flow_id, flow.dr))

        if flow.is_processed() and flow['state'] != 'departure':
            # yes => switch to departure, forward to egress node
            flow['state'] = 'departure'
            flow['target_node_id'] = flow.egress_node_id
            flow['blocked_links'] = []
            self.try_set_new_path(flow)

        if flow['state'] == 'transit':
            demand, need_placement = Placement.calculate_demand(flow, flow.current_sf, exec_node['available_sf'],
                                                                state.service_functions)
            if flow['target_node_id'] == exec_node_id:
                if exec_node['capacity'] > demand:
                    # process flow
                    if need_placement:
                        placement[exec_node_id].append(flow.current_sf)
                    processing_rules[exec_node_id][flow.flow_id] = [flow.current_sf]
                    flow['state'] = 'processing'
                else:
                    try:
                        self.plan_placement(flow)
                        assert flow['target_node_id'] != exec_node_id, \
                            'Flow cannot be processed here, why does it stay?'
                        flow['blocked_links'] = []
                        self.set_new_path(flow)
                        self.forward_flow(flow, state)
                    except:
                        flow['state'] = 'drop'
                        flow['path'] = []
            else:
                try:
                    self.plan_placement(flow)
                    self.set_new_path(flow)
                    self.forward_flow(flow, state)
                except:
                    flow['state'] = 'drop'
                    flow['path'] = []

        elif flow['state'] == 'processing':
            # process or forward, change state accordingly
            try:
                self.plan_placement(flow)
                if flow['target_node_id'] == exec_node_id:
                    demand, need_placement = Placement.calculate_demand(flow, flow.current_sf,
                                                                        exec_node['available_sf'],
                                                                        state.service_functions)
                    if exec_node['capacity'] > demand:
                        if need_placement:
                            placement[exec_node_id].append(flow.current_sf)
                        processing_rules[exec_node_id][flow.flow_id] = [flow.current_sf]
                        flow['state'] = 'processing'
                    else:
                        assert False, f'Flow {flow.flow_id} should stay here although there is not enough capcitiy!'
                else:
                    try:
                        flow['blocked_links'] = []
                        self.set_new_path(flow)
                        self.forward_flow(flow, state)
                    except nx.NetworkXNoPath:
                        flow['state'] = 'drop'
                        flow['path'] = []
            except NoCandidateException:
                flow['state'] = 'drop'
                flow['path'] = []
                print('No candidate')

        elif flow['state'] == 'departure':
            # Return to destination as soon as possible, no more processing necessary
            if exec_node_id != flow.egress_node_id:
                self.forward_flow(flow, state)

        if flow['state'] == 'drop':
            # Something went legitimate wrong => clear remaing rules => let it drop
            processing_rules[exec_node_id].pop(flow.flow_id, None)
            forwarding_rules[exec_node_id].pop(flow.flow_id, None)
            self.node_mortality[exec_node_id] += 1

        self.simulator.apply(state.derive_action())

    def plan_placement(self, flow):
        try:
            score_table = self.score(flow)
            # Determine target node
            target = score_table[0][0]
            flow['target_node_id'] = target
            flow['state'] = 'transit'
        except NoCandidateException:
            raise

    def score(self, flow):
        state = self.simulator.get_state()
        exec_node_id = flow.current_node_id
        candidates = []
        rejected = []

        minimum_edge_con = min(self.edge_connectivity[exec_node_id].items(), key=operator.itemgetter(1))[1]
        maximum_edge_con = max(self.edge_connectivity[exec_node_id].items(), key=operator.itemgetter(1))[1]
        #minimum_node_con = min(self.node_connectivity[exec_node_id].items(), key=operator.itemgetter(1))[1]
        #maximum_node_con = max(self.node_connectivity[exec_node_id].items(), key=operator.itemgetter(1))[1]

        for n in state.network['node_list']:
            # Can place?
            available_sf = self.simulator.params.network.node[n]['available_sf']
            demand, place = Placement.calculate_demand(flow, flow.current_sf, available_sf, state.service_functions)

            path_a_length = self.apsp_length[exec_node_id][n]
            path_b_length = self.apsp_length[n][flow.egress_node_id]
            n_cap = state.network['nodes'][n]['capacity']
            n_load = state.network['nodes'][n]['used_capacity']
            if exec_node_id != n:
                edge_con = self.edge_connectivity[exec_node_id][n]
            else:
                edge_con = maximum_edge_con

            if state.network['nodes'][n]['capacity'] > demand:
                candidates.append(
                    [n, path_a_length, path_a_length + path_b_length, n_cap - n_load, self.node_mortality[n], edge_con,
                     self.occupancy(n)])
            else:
                rejected.append(
                    [n, path_a_length, path_a_length + path_b_length, n_cap - n_load, self.node_mortality[n], edge_con,
                     self.occupancy(n)])

        if len(candidates) == 0:
            raise NoCandidateException()

        delta = 0.0001
        minimum_a = min(candidates, key=lambda x: x[1])[1]
        maximum_a = max(candidates, key=lambda x: x[1])[1]
        minimum_ab = min(candidates, key=lambda x: x[2])[2]
        maximum_ab = max(candidates, key=lambda x: x[2])[2]
        minimum_free = min(candidates, key=lambda x: x[3])[3]
        maximum_free = max(candidates, key=lambda x: x[3])[3]
        minimum_mortality = min(candidates, key=lambda x: x[4])[4]
        maximum_mortality = max(candidates, key=lambda x: x[4])[4]
        minimum_occupancy = max(candidates, key=lambda x: x[6])[6]
        maximum_occupancy = max(candidates, key=lambda x: x[6])[6]
        d_a = maximum_a + delta
        d_ab = maximum_ab + delta
        d_free = maximum_free + delta
        d_mortality = maximum_mortality + delta
        d_occupancy = maximum_occupancy + delta
        d_edge_con = maximum_edge_con + delta
        #d_node_con = maximum_node_con - minimum_node_con + 0.0001

        for i in range(len(candidates)):
            candidates[i][1] = (maximum_a - candidates[i][1]) / d_a
            candidates[i][2] = (maximum_ab - candidates[i][2]) / d_ab
            candidates[i][3] = (candidates[i][3]) / d_free
            candidates[i][4] = (maximum_mortality - candidates[i][4] + delta) / d_mortality
            candidates[i][5] = candidates[i][5] / d_edge_con
            candidates[i][6] = (maximum_occupancy - candidates[i][6] + delta) / d_occupancy

        score_table = []
        for i in range(len(candidates)):
            score_table.append((candidates[i][0],
                                1.5 * candidates[i][1] +
                                1 * candidates[i][2] +
                                1 * candidates[i][3] +
                                1.5 * candidates[i][4] +
                                1 * candidates[i][5] +
                                1.5 * candidates[i][6]))

        candidates.sort(key=lambda x: x[1])
        score_table.sort(key=lambda x: x[1], reverse=True)

        return score_table

    def occupancy(self, node_id):
        return sum(float(dr) for id, dr in self.occupancy_list[node_id])

    def try_set_new_path(self, flow):
        try:
            self.set_new_path(flow)
        except nx.NetworkXNoPath:
            flow['state'] = 'drop'
            flow['path'] = []

    def set_new_path(self, flow):
        """
        Calculate and set shortest path to the target node defined by target_node_id, taking blocked links into account.
        """
        for link in flow['blocked_links']:
            self.network_copy.remove_edge(link[0], link[1])
        try:
            shortest_path = nx.shortest_path(self.network_copy, flow.current_node_id, flow['target_node_id'],
                                             weight='delay')
            # Remove first node, as it is corresponds to the current node
            shortest_path.pop(0)
            flow['path'] = shortest_path
        except nx.NetworkXNoPath:
            raise
        finally:
            for link in flow['blocked_links']:
                self.network_copy.add_edge(link[0], link[1], **link.attributes)

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
                # Try to find new path once
                self.set_new_path(flow)
                assert len(flow['path']) > 0
                next_neighbor_id = flow['path'].pop(0)
                # Set forwarding rule
                state.flow_forwarding_rules[node_id][flow.flow_id] = next_neighbor_id
            except nx.NetworkXNoPath:
                flow['state'] = 'drop'
                flow['path'] = []

    def post_forwarding(self, node_id, flow):
        """
        Callback
        """
        self.occupancy_list[node_id].remove((flow.flow_id, flow.dr))

    def depart_flow(self, flow):
        """
        Callback
        """
        self.occupancy_list[flow.current_node_id].remove((flow.flow_id, flow.dr))

    def drop_flow(self, flow):
        """
        Callback
        """
        self.occupancy_list[flow.current_node_id].remove((flow.flow_id, flow.dr))

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

    def periodic_measurement(self):
        """
        <Callback>
        """
        #self.simulator.write_state()
        state = self.simulator.get_state()
        log.warning(f'Network Stats after time: {state.simulation_time} /{state.network_stats} / '
                    f'{state.network["metrics"]}')


def main():
    # Simulator params
    args = {
        'network': '../../../../params/networks/dfn_58.graphml',
        'network_connectivity': '../../../../params/networks/connectivity',
        'service_functions': '../../../../params/services/3sfcs.yaml',
        'resource_functions': '../../../../params/services/resource_functions',
        'config': '../../../../params/config/probabilistic_discrete_config.yaml',
        'seed': 9999,
        'output_id': 'tpk-out'
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
    algo = TPKAlgo(simulator)
    algo.init(os.path.abspath(args['network']),
              os.path.abspath(args['network_connectivity']),
              os.path.abspath(args['service_functions']),
              os.path.abspath(args['config']),
              args['seed'],
              args['output_id'],
              resource_functions_path=os.path.abspath(args['resource_functions']))
    # Execute orchestrated simulation
    algo.run()


if __name__ == "__main__":
    main()
