# -*- coding: utf-8 -*-
"""
Dummy simulator for testing purposes.
"""
from spinterface import SimulatorAction, SimulatorInterface, SimulatorState


class DummySimulator(SimulatorInterface):
    """
    return a mixture of static and random values
    """

    def __init__(self, network_file: str, service_functions_file: str, config_file: str, test_mode=False):
        super(DummySimulator, self).__init__(test_mode)

    def init(self, seed: int,
             trace=None) -> SimulatorState:
        """ returns fixed init state

        Parameters
        ----------
        config_file
        network_file
        service_functions_file
        seed

        Returns
        -------
        state: SimulatorState

        """
        return self.example_state_1

    def apply(self, actions: SimulatorAction) -> SimulatorState:
        """ returns fixed simulator state

        Parameters
        ----------
        actions

        Returns
        -------
        state: SimulatorState

        """
        return self.example_state_1

    def get_active_ingress_nodes(self):
        return ['pop0']

    @property
    def example_state_1(self):
        """ Returns a fixed instance of a simulator state

        Returns
        -------
        state: SimulatorState

        """

        state = SimulatorState(
            network={
                'nodes': [
                    {
                        'id': 'pop0',
                        'resource': 42.0,
                        'used_resources': 0.21
                    },
                    {
                        'id': 'pop1',
                        'resource': 42.0,
                        'used_resources': 0.21
                    },
                    {
                        'id': 'pop2',
                        'resource': 42.0,
                        'used_resources': 0.21
                    }
                ],
                'edges': [
                    {
                        'src': 'pop0',
                        'dst': 'pop1',
                        'delay': 13,
                        'data_rate': 100,
                        'used_data_rate': 62,
                    },
                    {
                        'src': 'pop1',
                        'dst': 'pop2',
                        'delay': 13,
                        'data_rate': 100,
                        'used_data_rate': 62,
                    },
                    {
                        'src': 'pop2',
                        'dst': 'pop0',
                        'delay': 13,
                        'data_rate': 100,
                        'used_data_rate': 62,
                    },
                ],
            },
            sfcs={
                'sfc_1': ['a', 'b', 'c'],
            },
            service_functions={
                'a': {
                    'processing_delay': 0.5
                },
                'b': {
                    'processing_delay': 0.3
                },
                'c': {
                    'processing_delay': 0.2
                },
            },
            traffic={
                'pop0': {
                    'sfc_1': {
                        'a': 1,
                        'b': 1,
                    },
                },
                'pop1': {
                    'sfc_1': {
                        'b': 1,
                        'c': 1,
                    },
                },
                'pop2': {
                    'sfc_1': {
                        'c': 1,
                    },
                },
            },
            network_stats={
                'total_flows': 136,
                'successful_flows': 30,
                'dropped_flows': 3,
                'in_network_flows': 32,
                'avg_end2end_delay': 21,
                'run_avg_end2end_delay': 42,
                'run_total_processed_traffic': dict(),
                'run_avg_path_delay': 22,
                'processed_traffic': dict()
            },
            placement={
                'pop0': ['a'],
                'pop1': ['b'],
                'pop2': ['c']
            }
        )
        return state
