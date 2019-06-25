# -*- coding: utf-8 -*-
"""
Module to abstract interaction between simulator and S&P
"""


class SimulatorAction:
    """
    Defines the actions to apply to the simulator environment.
    """

    def __init__(self,
                 placement,
                 scheduling):
        """initializes all properties since this is a data class

        Parameters
        ----------
        placement : dict
            {
                'node id' : [list of SF ids]
            }

        << Schedule: Must include traffic distribution for all possible nodes. Even those that have a value of zero >>
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

        action = SimulationAction(placement, schedule)
        """
        self.placement = placement
        self.scheduling = scheduling


class SimulatorState:
    """
    Defines the state of the simulator environment.
    Contains all necessary information for an coordination algorithm.

    TODO: use integer for ids
    """
    def __init__(self,
                 network,
                 placement,
                 sfcs,
                 service_functions,
                 traffic,
                 network_stats):
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


class SimulatorInterface:
    """
    Defines required method on the simulator object.
    """

    def init(self, network_file: str, service_functions_file: str, seed: int) -> SimulatorState:
        """Creates a new simulation environment.

        Parameters
        ----------
        network_file : str
            (Absolute) path to the network description.
        service_functions_file : str
            (Absolute) path to the service function description file.
        seed : int
            The seed value enables reproducible gym environments respectively
            reproducible simulator environments. This value should initialize
            the random number generator used by the simulator when executing
            randomized functions.

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
