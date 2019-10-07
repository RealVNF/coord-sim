import math
from collections import defaultdict
import networkx as nx
from auxiliary.link import Link
from auxiliary.placement import Placement
from siminterface.simulator import ExtendedSimulatorAction
from siminterface.simulator import Simulator


class NoCandidateException(Exception):
    """
    Signal that no suitable routing/placement candidate could be determined
    """
    pass


class SPR1Algo:
    """
    SPR base algorithm
    Score: closeness + compound path length + remaining node cap + unavailable links + remaining path cap
    Node cap requirement: soft
    Blocked links: only for each forwarding operation
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

    def init(self, network_path, service_functions_path, config_path, seed, output_path,
             resource_functions_path=""):
        init_state = self.simulator.init(network_path, service_functions_path, config_path, seed, output_path,
                                         resource_functions_path=resource_functions_path,
                                         interception_callbacks=
                                         {'pass_flow': self.pass_flow,
                                          'init_flow': self.init_flow,
                                          'depart_flow': self.depart_flow,
                                          'drop_flow': self.drop_flow,
                                          'periodic': [(self.periodic_measurement, 100, 'Measurement'),
                                                       (self.periodic_remove, 10, 'Remove SF interception.')]})

        self.network_copy = self.simulator.get_network_copy()
        sum_of_degrees = sum(map(lambda x: x[1], self.network_copy.degree()))
        self.avg_ceil_degree = int(math.ceil(sum_of_degrees / len(self.network_copy)))

        # All pairs shortest path calculations
        self.apsp = dict(nx.all_pairs_dijkstra_path(self.network_copy, weight='delay'))
        self.apsp_length = dict(nx.all_pairs_dijkstra_path_length(self.network_copy, weight='delay'))

        # Record how often a flow was passed to a node, used to calculate score
        self.node_mortality = defaultdict(int)
        # Record current general load, used to calculate score
        self.occupancy_list = defaultdict(list)

    def run(self):
        placement = defaultdict(list)
        processing_rules = defaultdict(lambda: defaultdict(list))
        forwarding_rules = defaultdict(dict)
        action = ExtendedSimulatorAction(placement=placement, scheduling={}, flow_forwarding_rules=forwarding_rules,
                                         flow_processing_rules=processing_rules)
        self.simulator.apply(action)
        self.simulator.run()
        self.simulator.write_state()

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
                if exec_node['capacity'] >= demand:
                    # process flow
                    if need_placement:
                        placement[exec_node_id].append(flow.current_sf)
                    processing_rules[exec_node_id][flow.flow_id] = [flow.current_sf]
                else:
                    try:
                        self.plan_placement(flow, exclude=[flow.current_node_id])
                        assert flow['target_node_id'] != exec_node_id, \
                            'Flow cannot be processed here, why does it stay?'
                        flow['blocked_links'] = []
                        self.set_new_path(flow)
                        self.forward_flow(flow, state)
                    except (NoCandidateException, nx.NetworkXNoPath) as e:
                        flow['state'] = 'drop'
                        flow['path'] = []
            else:
                try:
                    # self.plan_placement(flow)
                    # self.set_new_path(flow)
                    self.forward_flow(flow, state)
                except nx.NetworkXNoPath:
                    flow['state'] = 'drop'
                    flow['path'] = []

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

    def plan_placement(self, flow, exclude=[]):
        try:
            score_table = self.score(flow, exclude)
            #score_table = score_table[:self.avg_ceil_degree]
            #score_table = score_table[:1]
            # Determine target node
            #sum_score = sum(map(lambda x: x[1], score_table))
            #p = list(map(lambda x: x[1] / sum_score, score_table))
            #target = np.random.choice(list(map(lambda x: x[0], score_table)), p=p)
            target = score_table[0][0]
            flow['target_node_id'] = target
            flow['state'] = 'transit'
        except NoCandidateException:
            raise

    def score(self, flow, exclude=[]):
        state = self.simulator.get_state()
        exec_node_id = flow.current_node_id
        candidates_nodes = []
        candidates_path = []
        rejected_nodes = []
        rejected_path = []

        for n in state.network['node_list']:
            if n not in exclude:
                node_stats = self.node_stats(n, flow)
                path_stats = self.path_stats(flow.current_node_id, n, flow)
                candidates_nodes.append(node_stats)
                candidates_path.append(path_stats)

        # Determine max min
        # Nodes
        # Closeness
        minimum_closeness = min(candidates_nodes, key=lambda x: x[2])[2]
        maximum_closeness = max(candidates_nodes, key=lambda x: x[2])[2]
        # Compound path length
        minimum_compound_path_length = min(candidates_nodes, key=lambda x: x[3])[3]
        maximum_compound_path_length = max(candidates_nodes, key=lambda x: x[3])[3]
        # Remaining node cap
        minimum_remaining_node_cap = min(candidates_nodes, key=lambda x: x[4])[4]
        maximum_remaining_node_cap = max(candidates_nodes, key=lambda x: x[4])[4]
        # Node mortality
        minimum_node_mortality = min(candidates_nodes, key=lambda x: x[5])[5]
        maximum_node_mortality = max(candidates_nodes, key=lambda x: x[5])[5]
        # Node occupancy
        minimum_node_occupancy = min(candidates_nodes, key=lambda x: x[6])[6]
        maximum_node_occupancy = max(candidates_nodes, key=lambda x: x[6])[6]
        # Path
        # Remaining link cap
        minimum_remaining_link_cap = min(candidates_path, key=lambda x: x[2])[2]
        maximum_remaining_link_cap = max(candidates_path, key=lambda x: x[2])[2]
        # Number of unavailable links
        minimum_unavailable_links = min(candidates_path, key=lambda x: x[3])[3]
        maximum_unavailable_links = max(candidates_path, key=lambda x: x[3])[3]
        # Path occupancy
        minimum_path_occupancy = min(candidates_path, key=lambda x: x[4])[4]
        maximum_path_occupancy = max(candidates_path, key=lambda x: x[4])[4]

        # Determine value ranges
        # Add delta to prevent zero division
        delta = 0.0001
        # Node range
        range_closeness = maximum_closeness - minimum_closeness + delta
        range_compound_path_length = maximum_compound_path_length - minimum_compound_path_length + delta
        range_remaining_node_cap = maximum_remaining_node_cap - minimum_remaining_node_cap + delta
        range_node_mortality = maximum_node_mortality - minimum_node_mortality + delta
        range_node_occupancy = maximum_node_occupancy - minimum_node_occupancy + delta
        # Path range
        range_remaining_link_cap = maximum_remaining_link_cap - minimum_remaining_link_cap + delta
        range_unavailable_links = maximum_unavailable_links - minimum_unavailable_links + delta
        range_path_occupancy = maximum_path_occupancy - minimum_path_occupancy + delta

        # Range scaling
        # Nodes
        for i in range(len(candidates_nodes)):
            candidates_nodes[i][2] = maximum_closeness - candidates_nodes[i][2]
            candidates_nodes[i][3] = maximum_compound_path_length - candidates_nodes[i][3]
            candidates_nodes[i][4] = candidates_nodes[i][4] - minimum_remaining_node_cap
            candidates_nodes[i][5] = maximum_node_mortality - candidates_nodes[i][5]
            candidates_nodes[i][6] = maximum_node_occupancy - candidates_nodes[i][6]
        # Links
        for i in range(len(candidates_path)):
            candidates_path[i][2] = candidates_path[i][2] - minimum_remaining_link_cap
            candidates_path[i][3] = maximum_unavailable_links - candidates_path[i][3]
            candidates_path[i][4] = maximum_path_occupancy - candidates_path[i][4]

        # [0,1] scaling
        # print('')
        # Nodes
        for i in range(len(candidates_nodes)):
            candidates_nodes[i][2] = candidates_nodes[i][2] / range_closeness
            candidates_nodes[i][3] = candidates_nodes[i][3] / range_compound_path_length
            candidates_nodes[i][4] = candidates_nodes[i][4] / range_remaining_node_cap
            candidates_nodes[i][5] = candidates_nodes[i][5] / range_node_mortality
            candidates_nodes[i][6] = candidates_nodes[i][6] / range_node_occupancy
            assert 0 <= candidates_nodes[i][2] <= 1
            assert 0 <= candidates_nodes[i][3] <= 1
            assert 0 <= candidates_nodes[i][4] <= 1
            assert 0 <= candidates_nodes[i][5] <= 1
            assert 0 <= candidates_nodes[i][6] <= 1
        # Links
        for i in range(len(candidates_path)):
            candidates_path[i][2] = candidates_path[i][2] / range_remaining_link_cap
            candidates_path[i][3] = candidates_path[i][3] / range_unavailable_links
            candidates_path[i][4] = candidates_path[i][4] / range_path_occupancy
            assert 0 <= candidates_path[i][2] <= 1
            assert 0 <= candidates_path[i][3] <= 1
            assert 0 <= candidates_path[i][4] <= 1

        # Scoring
        score_table = []
        for i in range(len(candidates_nodes)):
            node_score = candidates_nodes[i][2] + candidates_nodes[i][3] + candidates_nodes[i][4]
            path_score = candidates_path[i][2] + candidates_path[i][3]
            score_table.append((candidates_nodes[i][0], node_score + path_score))

        score_table.sort(key=lambda x: x[1], reverse=True)

        return score_table

    def occupancy(self, node_id):
        return sum(float(dr) for id, dr in self.occupancy_list[node_id])

    def node_stats(self, node_id, flow):
        """
        Returns node stats for score calculation as list
        Index:
        1. Can the flow be processed at this moment
        2. Closeness to flows current node
        3. Sum of path length from current node to target node and target node to egress node
        4. Remaining node capacity
        5. How many flows have already dropped there
        6. Node occupancy
        """
        available_sf = self.simulator.params.network.node[node_id]['available_sf']
        demand, place = Placement.calculate_demand(flow, flow.current_sf, available_sf, self.simulator.params.sf_list)

        can_be_processed = 1 if self.simulator.params.network.nodes[node_id]['cap'] > demand else 0
        closeness = self.apsp_length[flow.current_node_id][node_id]
        compound_path_length = (
                    self.apsp_length[flow.current_node_id][node_id] + self.apsp_length[node_id][flow.egress_node_id])
        remaining_cap = self.simulator.params.network.nodes[node_id]['remaining_cap']
        node_mortality = self.node_mortality[node_id]
        return [node_id, can_be_processed, closeness, compound_path_length, remaining_cap, node_mortality,
                self.occupancy(node_id)]

    def path_stats(self, node_a_id, node_b_id, flow):
        """
        Returns path stats for score calculation as list
        Index:
        1. path length
        2. Avg remaining link capacity
        3. Sum of unavailable links
        4. Path_occupancy
        """
        sum_unavailable_links = 0
        sum_remaining_cap = 0
        shortest_path = self.apsp[node_a_id][node_b_id]
        path_length = self.apsp_length[node_a_id][node_b_id]
        path_occupancy = sum(map(self.occupancy, shortest_path))
        for i in range(len(shortest_path) - 1):
            i_1 = shortest_path[i]
            i_2 = shortest_path[i + 1]
            cap = self.simulator.params.network[i_1][i_2]['cap']
            remaining_cap = self.simulator.params.network[i_1][i_2]['remaining_cap']
            sum_remaining_cap += remaining_cap
            sum_unavailable_links += 1 if (remaining_cap < flow.dr) else 0

        return [(node_a_id, node_b_id), path_length, sum_remaining_cap, sum_unavailable_links, path_occupancy]

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
            shortest_path = nx.shortest_path(self.network_copy, flow.current_node_id, flow['target_node_id'], weight='delay')
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
                # Try to find new path once
                self.set_new_path(flow)
                assert len(flow['path']) > 0
                next_neighbor_id = flow['path'].pop(0)
                # Set forwarding rule
                state.flow_forwarding_rules[node_id][flow.flow_id] = next_neighbor_id
            except nx.NetworkXNoPath:
                flow['state'] = 'drop'
                flow['path'] = []
            flow['blocked_links'] = []

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
        self.simulator.write_state()
