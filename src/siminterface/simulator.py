import coordsim.reader.networkreader as networkreader
from coordsim.simulation.flowsimulator import FlowSimulator
import coordsim.metrics.metrics as metrics
from coordsim.network import scheduler
import time
from coordsim.simulation.params import SimulatorParams
from siminterface.interface.siminterface import SimulatorAction, SimulatorInterface, SimulatorState
import simpy
import logging


class Simulator(SimulatorInterface):
    def __init__(self):
        # Define simulator duration until which simulator in 'apply' runs until requesting a decision
        self.duration = int(100)
        self.run_times = int(1)

    def init(self, network_file, service_functions_file, seed):
        metrics.reset()
        start_time = time.time()
        self.network = networkreader.read_network(network_file, node_cap=10, link_cap=10)
        self.sf_placement, self.sfc_list, self.sf_list = networkreader.network_update(service_functions_file,
                                                                                      self.network)
        self.env = simpy.Environment()
        self.schedule = scheduler.flow_schedule()
        self.seed = seed
        self.params = SimulatorParams(self.network, self.sf_placement, self.sfc_list, self.sf_list, self.seed,
                                      self.schedule)
        self.simulator = FlowSimulator(self.env, self.params)
        self.simulator.start_simulator()
        self.env.step()
        end_time = time.time()
        metrics.running_time(start_time, end_time)
        self.parse_network()
        self.network_metrics()
        self.run_times += 1
        traffic = metrics.get_metrics()['current_traffic']
        simulator_state = SimulatorState(self.network_dict, self.sfc_list, self.sf_list, traffic, self.network_stats)
        return simulator_state

    def apply(self, actions: SimulatorAction):
        start_time = time.time()
        self.simulator.params.sf_placement = actions.placement
        self.simulator.params.schedule = actions.scheduling
        self.env.run(until=(self.duration*self.run_times))
        self.parse_network()
        self.network_metrics()
        self.run_times += 1
        traffic = metrics.get_metrics()['current_traffic']
        simulator_state = SimulatorState(self.network_dict, self.sfc_list, self.sf_list, traffic, self.network_stats)
        end_time = time.time()
        metrics.running_time(start_time, end_time)
        return simulator_state

    def parse_network(self) -> dict:
        self.network_dict = {'nodes': [], 'edges': []}
        for node in self.network.nodes(data=True):
            # Reset network_dict nodes array
            node_cap = node[1]['cap']
            used_node_cap = node[1]['cap'] - node[1]['remaining_cap']
            self.network_dict['nodes'].append({'id': node[0], 'resource': node_cap, 'used_resources': used_node_cap})
        for edge in self.network.edges(data=True):
            edge_src = edge[0]
            edge_dest = edge[1]
            edge_delay = edge[2]['delay']
            edge_dr = edge[2]['cap']
            edge_used_dr = 0
            self.network_dict['edges'] = {
                'src': edge_src,
                'dst': edge_dest,
                'delay': edge_delay,
                'data_rate': edge_dr,
                'used_data_rate': edge_used_dr
                }

    def network_metrics(self):
        stats = metrics.get_metrics()
        self.traffic = stats['current_traffic']
        self.network_stats = {
            'total_flows': stats['generated_flows'],
            'successful_flows': stats['processed_flows'],
            'dropped_flows': stats['dropped_flows'],
            'in_network_flows': stats['total_active_flows'],
            'avg_end_2_end_delay': stats['avg_end2end_delay']
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    simulate = Simulator()
    simulate.init("params/networks/Abilene.graphml",
                  "params/placements/Abilene.yaml", 9999)
