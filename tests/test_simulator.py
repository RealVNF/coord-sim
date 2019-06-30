from unittest import TestCase
from coordsim.simulation.flowsimulator import FlowSimulator
from coordsim.simulation.simulatorparams import SimulatorParams
from coordsim.network import dummy_data
from coordsim.reader import reader
from coordsim.metrics import metrics
import simpy
import logging


NETWORK_FILE = "params/networks/triangle.graphml"
SERVICE_FUNCTIONS_FILE = "params/services/abc.yaml"
CONFIG_FILE = "params/config/sim_config.yaml"
SIMULATION_DURATION = 1000
SEED = 1234


class TestFlowSimulator(TestCase):
    flow_simulator = None
    simulator_params = None

    def setUp(self):
        """
        Setup test environment
        """
        logging.basicConfig(level=logging.ERROR)
        metrics.reset()

        self.env = simpy.Environment()
        # Configure simulator parameters
        network, ing_nodes = reader.read_network(NETWORK_FILE, node_cap=10, link_cap=10)
        sfc_list = reader.get_sfc(SERVICE_FUNCTIONS_FILE)
        sf_list = reader.get_sf(SERVICE_FUNCTIONS_FILE)
        config = reader.get_config(CONFIG_FILE)

        sf_placement = dummy_data.triangle_placement
        schedule = dummy_data.triangle_schedule

        # Initialize Simulator and SimulatoParams objects
        self.simulator_params = SimulatorParams(network, ing_nodes, sfc_list, sf_list, config, SEED,
                                                sf_placement=sf_placement, schedule=schedule)
        self.flow_simulator = FlowSimulator(self.env, self.simulator_params)
        self.flow_simulator.start()
        self.env.run(until=SIMULATION_DURATION)

    def test_simulator(self):
        """
        Test the simulator
        """
        # Collect metrics
        self.metric_collection = metrics.get_metrics()
        # Check if Simulator is initiated correctly
        self.assertIsInstance(self.flow_simulator, FlowSimulator)
        # Check if Params are set correctly
        self.assertIsInstance(self.simulator_params, SimulatorParams)
        # Check if generated flows are equal to processed flow + dropped + active flows
        gen_flow_check = self.metric_collection['generated_flows'] == (self.metric_collection['processed_flows'] +
                                                                       self.metric_collection['dropped_flows'] +
                                                                       self.metric_collection['total_active_flows'])
        self.assertIs(gen_flow_check, True)
        # More tests are to come
