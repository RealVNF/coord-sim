# -*- coding: utf-8 -*-
"""
Simulator interface tests
"""
from unittest import TestCase

from spinterface import SimulatorInterface, SimulatorAction, SimulatorState

NETWORK_FILE = "params/networks/triangle.graphml"
SERVICE_FUNCTIONS_FILE = "params/services/3sfcs.yaml"
CONFIG_FILE = "params/config/sim_config.yaml"

SIMULATOR_MODULE_NAME = "siminterface.simulator"
SIMULATOR_CLS_NAME = "Simulator"
SIMULATOR_MODULE = __import__(SIMULATOR_MODULE_NAME)
SIMULATOR_CLS = getattr(SIMULATOR_MODULE, SIMULATOR_CLS_NAME)
TEST_MODE = False


class TestSimulatorInterface(TestCase):

    simulator = None  # type: SimulatorInterface

    def setUp(self):
        """
        create simulator for test cases
        """
        # TODO: replace SimulatorInterface with implementation
        self.simulator = SIMULATOR_CLS(TEST_MODE)
        self.simulator.init(NETWORK_FILE, SERVICE_FUNCTIONS_FILE, CONFIG_FILE, 1234)

    def test_apply(self):
        # test if placement and schedule can be applied
        placement = {
            'pop0': ['a', 'b', 'c'],
            'pop1': ['a', 'b', 'c'],
            'pop2': ['a', 'b', 'c'],
        }
        flow_schedule = {
            'pop0': {
                'sfc_1': {
                    'a': {
                        'pop0': 0.4,
                        'pop1': 0.6,
                        'pop2': 0
                        },
                    'b': {
                        'pop0': 0.6,
                        'pop1': 0.2,
                        'pop2': 0.2
                        },
                    'c': {
                        'pop0': 0.6,
                        'pop1': 0.2,
                        'pop2': 0.2
                        }
                    },
                'sfc_2': {
                    'a': {
                        'pop0': 0.4,
                        'pop1': 0.6,
                        'pop2': 0
                        },
                    'b': {
                        'pop0': 0.6,
                        'pop1': 0.2,
                        'pop2': 0.2
                        },
                    'c': {
                        'pop0': 0.6,
                        'pop1': 0.2,
                        'pop2': 0.2
                        }
                    },
                'sfc_3': {
                    'a': {
                        'pop0': 0.4,
                        'pop1': 0.6,
                        'pop2': 0
                        },
                    'b': {
                        'pop0': 0.6,
                        'pop1': 0.2,
                        'pop2': 0.2
                        },
                    'c': {
                        'pop0': 0.6,
                        'pop1': 0.2,
                        'pop2': 0.2
                        }
                    },
                },
            'pop1': {
                'sfc_1': {
                    'a': {
                        'pop0': 0.4,
                        'pop1': 0.6,
                        'pop2': 0
                        },
                    'b': {
                        'pop0': 0.6,
                        'pop1': 0.2,
                        'pop2': 0.2
                        },
                    'c': {
                        'pop0': 0.6,
                        'pop1': 0.2,
                        'pop2': 0.2
                        }
                    },
                'sfc_2': {
                    'a': {
                        'pop0': 0.4,
                        'pop1': 0.6,
                        'pop2': 0
                        },
                    'b': {
                        'pop0': 0.6,
                        'pop1': 0.2,
                        'pop2': 0.2
                        },
                    'c': {
                        'pop0': 0.6,
                        'pop1': 0.2,
                        'pop2': 0.2
                        }
                    },
                'sfc_3': {
                    'a': {
                        'pop0': 0.4,
                        'pop1': 0.6,
                        'pop2': 0
                        },
                    'b': {
                        'pop0': 0.6,
                        'pop1': 0.2,
                        'pop2': 0.2
                        },
                    'c': {
                        'pop0': 0.6,
                        'pop1': 0.2,
                        'pop2': 0.2
                        }
                    },
                },
            'pop2': {
                'sfc_1': {
                    'a': {
                        'pop0': 0.4,
                        'pop1': 0.6,
                        'pop2': 0
                        },
                    'b': {
                        'pop0': 0.6,
                        'pop1': 0.2,
                        'pop2': 0.2
                        },
                    'c': {
                        'pop0': 0.6,
                        'pop1': 0.2,
                        'pop2': 0.2
                        }
                    },
                'sfc_2': {
                    'a': {
                        'pop0': 0.4,
                        'pop1': 0.6,
                        'pop2': 0
                        },
                    'b': {
                        'pop0': 0.6,
                        'pop1': 0.2,
                        'pop2': 0.2
                        },
                    'c': {
                        'pop0': 0.6,
                        'pop1': 0.2,
                        'pop2': 0.2
                        }
                    },
                'sfc_3': {
                    'a': {
                        'pop0': 0.4,
                        'pop1': 0.6,
                        'pop2': 0
                        },
                    'b': {
                        'pop0': 0.6,
                        'pop1': 0.2,
                        'pop2': 0.2
                        },
                    'c': {
                        'pop0': 0.6,
                        'pop1': 0.2,
                        'pop2': 0.2
                        }
                    },
                },
            }

        action = SimulatorAction(placement=placement, scheduling=flow_schedule)
        simulator_state = self.simulator.apply(action)
        self.assertIsInstance(simulator_state, SimulatorState)

        # test if network is read correctly
        nw_nodes = simulator_state.network['nodes']
        self.assertIs(len(nw_nodes), 3)
        # 3 bidirectional edges
        edges = simulator_state.network['edges']
        self.assertIs(len(edges), 3)
        # with 5 edge attributes:
        # 'edges': [{
        #     'src': str,
        #     'dst': str,
        #     'delay': int (ms),
        #     'data_rate': int (Mbit/s),
        #     'used_data_rate': int (Mbit/s),
        # }],
        nw_edges = simulator_state.network['edges'][0]
        self.assertIs(len(nw_edges), 5)

        # Check if placement is read correctly
        sim_placement = simulator_state.placement
        self.assertIs(len(sim_placement), 3)

        # test if sfcs are read correctly
        sfcs = simulator_state.sfcs
        self.assertIs(len(sfcs), 3)

        # SFs
        service_functions = simulator_state.service_functions
        self.assertIs(len(service_functions), 3)

        # traffic
        # TODO: test traffic

        # network_stats
        """
        network_stats : dict
            {
                'total_flows' : int,
                'successful_flows' : int,
                'dropped_flows' : int,
                'in_network_flows' : int,
                 'avg_end_2_end_delay' : int
            }
        """
        network_stats = simulator_state.network_stats
        self.assertIs(len(network_stats), 5)
        self.assertIn('total_flows', network_stats)
        self.assertIn('successful_flows', network_stats)
        self.assertIn('dropped_flows', network_stats)
        self.assertIn('in_network_flows', network_stats)
        self.assertIn('avg_end_2_end_delay', network_stats)
