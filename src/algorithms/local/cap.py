import logging
import os
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
    pass


class CAPAlgo:
    def __init__(self, simulator: Simulator):
        # Besides interaction we need the simulator reference to query all needed information. Not all information can
        # conveniently put into the simulator state, nevertheless it is justified that the algorithm can access these.
        self.simulator = simulator
        self.network_copy = None

    def init(self, network_path, service_functions_path, config_path, seed, output_id, resource_functions_path=""):
        init_state = self.simulator.init(network_path, service_functions_path, config_path, seed, output_id,
                                         resource_functions_path=resource_functions_path,
                                         interception_callbacks={'pass_flow': self.pass_flow,
                                                                 'init_flow': self.init_flow,
                                                                 'post_forwarding': self.post_forwarding,
                                                                 'depart_flow': self.depart_flow,
                                                                 'drop_flow': self.drop_flow})

        log.info(f'Network Stats after init(): {init_state.network_stats}')

        self.network_copy = self.simulator.get_network_copy()

        self.network_diameter = nx.diameter(self.network_copy)

        self.asps = dict(nx.all_pairs_dijkstra_path(self.network_copy))
        self.apsp_length = dict(nx.all_pairs_dijkstra_path_length(self.network_copy))

        self.node_mortality = defaultdict(int)

        self.qlist = defaultdict(list)
        ma = max(init_state.network['edges'], key=lambda x: x['data_rate'])
        mi = min(init_state.network['edges'], key=lambda x: x['data_rate'])
        self.d_r = max(init_state.network['edges'], key=lambda x: x['data_rate'])['data_rate']

        periodic = [(self.periodic_measurement, 100, 'Measurement')]
        self.simulator.params.interception_callbacks['periodic'] = periodic

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
        flow['state'] = 'greedy'
        flow['target_node_id'] = flow.egress_node_id

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

        if (flow.flow_id, flow.dr) not in self.qlist[exec_node_id]:
            self.qlist[exec_node_id].append((flow.flow_id, flow.dr))

        if flow.is_processed() and flow['state'] != 'departure':
            # yes => switch to departure, forward to egress node
            flow['state'] = 'departure'
            flow['target_node_id'] = flow.egress_node_id

        if flow['state'] == 'greedy':
            demand, need_placement = Placement.calculate_demand(flow, flow.current_sf, exec_node['available_sf'],
                                                                state.service_functions)
            if exec_node['capacity'] > demand:
                action = np.random.choice([True, False], p=[0.8, 0.2])
                if action:
                    # process flow
                    if need_placement:
                        placement[exec_node_id].append(flow.current_sf)
                    processing_rules[exec_node_id][flow.flow_id] = [flow.current_sf]
                else:
                    self.forward_flow(flow, state)
            else:
                self.forward_flow(flow, state)
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

    def score(self, flow):
        state = self.simulator.get_state()
        exec_node_id = flow.current_node_id
        candidates = []
        rejected = []

        for n in self.network_copy.neighbors(exec_node_id):
            edge = self.simulator.params.network[exec_node_id][n]

            if flow.dr < edge['remaining_cap']:
                d_q = (self.Q(exec_node_id) - self.Q(n)) / self.Q(exec_node_id)
                d_g = self.apsp_length[exec_node_id][flow['target_node_id']] - self.apsp_length[n][flow['target_node_id']]
                d_r = edge['cap'] / self.d_r
                score = d_q + d_g + d_r
                candidates.append((n, score))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates

    def forward_flow(self, flow, state):
        """
        This function will handle the necessary actions to forward a flow from the associated node. A call to this
        function requires the flow to have a precomputed path. If a flow can be forwarded along th precomputed path
        the flow_forwarding_rules for the associated node will be set. If a flow cannot be forwarded, due missing link
        resources, all incident links will be checked and all unsuitable links will be added to the blocked link list
        of the flow. Subsequent a new path is attempted to calculate.
        """

        node_id = flow.current_node_id
        candidates = self.score(flow)

        if len(candidates) > 0:
            next_neighbor_id = candidates[0][0]
            state.flow_forwarding_rules[node_id][flow.flow_id] = next_neighbor_id
        else:
            flow['state'] = 'drop'
            flow['path'] = []

    def Q(self, node_id):
        return sum(float(dr) for id, dr in self.qlist[node_id])

    def post_forwarding(self, node_id, flow):
        self.qlist[node_id].remove((flow.flow_id, flow.dr))

    def depart_flow(self, flow):
        self.qlist[flow.current_node_id].remove((flow.flow_id, flow.dr))

    def drop_flow(self, flow):
        self.qlist[flow.current_node_id].remove((flow.flow_id, flow.dr))

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
        'network': '../../../params/networks/dfn_58.graphml',
        'service_functions': '../../../params/services/3sfcs.yaml',
        'resource_functions': '../../../params/services/resource_functions',
        'config': '../../../params/config/probabilistic_discrete_config.yaml',
        'seed': 9999,
        'output_id': 'cap-out'
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
    algo = CAPAlgo(simulator)
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
