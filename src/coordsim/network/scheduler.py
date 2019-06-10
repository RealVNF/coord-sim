"""

Flow Scheduler
Defines a weighted flow schedule to allow making weighted decisions on where to
forward flows through the network
Placeholder function to return a fixed LB schedule.

The schedule assigns forwarding decision weights for each SF at each SFC in each node.

Follows the following format:

schedule = {
    node : {
        sfc : {
            sf : {
                node : weight (float),
            },
        },
    },
}

"""


class Scheduler:
    def __init__(self):
        # TODO: Remove the initial schedule.
        # Define an initial static flow schedule for the test scenario
        self.flow_schedule = {
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
