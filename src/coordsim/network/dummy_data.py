# dummy placements and schedules for testing the simulator without an algorithm

# placements
placement = {
    'pop0': ['a', 'b', 'c'],
    'pop1': ['a', 'b', 'c'],
    'pop2': ['a', 'b']
}

triangle_placement = {
    'pop0': ['a'],
    'pop1': ['b'],
    'pop2': ['c']
}

# schedules
schedule = {
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

# simple schedule sending flows along the triangle in deterministic way
triangle_schedule = {
    'pop0': {
        'sfc_1': {
            'a': {
                'pop0': 0.6,
                'pop1': 0.3,
                'pop2': 0.1
            },
            'b': {
                'pop0': 0,
                'pop1': 1,
                'pop2': 0
            },
            'c': {
                'pop0': 0,
                'pop1': 0,
                'pop2': 1
            }
        }
    },
    'pop1': {
        'sfc_1': {
            'a': {
                'pop0': 1,
                'pop1': 0,
                'pop2': 0
            },
            'b': {
                'pop0': 0,
                'pop1': 1,
                'pop2': 0
            },
            'c': {
                'pop0': 0,
                'pop1': 0,
                'pop2': 1
            }
        }
    },
    'pop2': {
        'sfc_1': {
            'a': {
                'pop0': 1,
                'pop1': 0,
                'pop2': 0
            },
            'b': {
                'pop0': 0,
                'pop1': 1,
                'pop2': 0
            },
            'c': {
                'pop0': 0,
                'pop1': 0,
                'pop2': 1
            }
        }
    }
}
