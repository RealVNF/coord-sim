# -*- coding: utf-8 -*-
"""
Module to abstract interaction between simulator and S&P algorithm
"""


class SimulatorAction:
    """
    Defines the actions to apply to the simulator environment.
    """

    def __init__(self,
                 placement: dict,
                 scheduling: dict):
        """initializes all properties since this is a data class

        Parameters
        ----------
        placement : dict
            {
                'node id' : [list of SF ids]
            }

        << Schedule: Must include traffic distribution for all possible nodes. Even those that have a value of zero >>
        The Sum of probabilities for each node of each SF needs to sum to 1.0
        Use :func:`~common.common_functionalities.normalize_scheduling_probabilities` to normalize if needed.
        scheduling : dict
            {
                'node id' : dict
                {
                    'SFC id' : dict
                    {
                        'SF id' : dict
                        {
                            'node id' : float (Inclusive of zero values)
                        }
                    }
                }
            }

        Examples
        --------
        placement = {
            'pop0': ['a', 'c', 'd'],
            'pop1': ['b', 'c', 'd'],
            'pop2': ['a', 'b'],
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
                ...
            },
        }

        simulator_action = SimulationAction(placement, flow_schedule)
        """
        self.placement = placement
        self.scheduling = scheduling

    def __repr__(self):
        return "SimulatorAction({})".format(repr({
            'placement': self.placement,
            'scheduling': self.scheduling
        }))

    def __str__(self):
        return f"SimulatorAction(Placement: {self.placement}, Schedule: {self.scheduling})"


class SimulatorState:
    """
    Defines the state of the simulator environment.
    Contains all necessary information for an coordination algorithm.
    """
    def __init__(self, network, placement, sfcs, service_functions, traffic, network_stats):
        """initializes all properties since this is a data class

        Parameters
        ----------
        network : dict
            {
                'nodes': [{
                    'id': str,
                    'resource': [float],
                    'used_resources': [float]
                }],
                'edges': [{
                    'src': str,
                    'dst': str,
                    'delay': int (ms),
                    'data_rate': int (Mbit/s),
                    'used_data_rate': int (Mbit/s),
                }],
            }
        placement : dict
            {
                'node id' : [list of SF ids]
            }
        sfcs : dict
            {
                'sfc_id': list
                    ['ids (str)']
            },

        service_functions : dict
            {
                'sf_id (str)' : dict
                {
                    'processing_delay_mean': int (ms),
                    'processing_delay_stdev': int (ms)
                },
            }


        << traffic: aggregated data rates of flows arriving at node requesting >>
        traffic : dict
            {
                'node_id (str)' : dict
                {
                    'sfc_id (str)': dict
                    {
                        'sf_id (str)': data_rate (int) [Mbit/s]
                    },
                },
            },

        network_stats : dict
            {
                'total_flows' : int,
                'successful_flows' : int,
                'dropped_flows' : int,
                'in_network_flows' : int
                'avg_end_2_end_delay' : int (ms)
            }
        """
        self.network = network
        self.placement = placement
        self.sfcs = sfcs
        self.service_functions = service_functions
        self.traffic = traffic
        self.network_stats = network_stats

    def __str__(self):
        return f"SimulatorState(Network nodes: {self.network['nodes']}, Traffic: {dict(self.traffic)}, ...)"


class SimulatorInterface:
    """
    Defines required method on the simulator object.
    """
    def __init__(self, test_mode):
        self.test_mode = test_mode

    def init(self, seed: int) -> SimulatorState:
        """Creates a new simulation environment.

        Parameters
        ----------
        seed : int
            Seed for reproducible randomness

        Returns
        -------
        state: SimulationStateInterface
        """
        raise NotImplementedError

    def apply(self, actions: SimulatorAction) -> SimulatorState:
        """Applies set of actions.

        Parameters
        ----------
        actions: SimulationAction

        Returns
        -------
        state: SimulationStateInterface
        """
        raise NotImplementedError
