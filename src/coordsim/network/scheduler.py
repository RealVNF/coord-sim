

# Placeholder function to return a fixed LB schedule. Todo: Replace this with
# functioning algorithm or get data from outside (RL or another agent)
def flow_schedule():
    flow_schedule = {'pop0':
                     {'a': {'pop0': 0.4, 'pop1': 0.6, 'pop2': 0},
                      'b': {'pop0': 0.6, 'pop1': 0.2, 'pop2': 0.2},
                      'c': {'pop0': 0.6, 'pop1': 0.2, 'pop2': 0.2}},
                     'pop1':
                     {'a': {'pop0': 0.3, 'pop1': 0.6, 'pop2': 0.1},
                      'b': {'pop0': 0.6, 'pop1': 0.2, 'pop2': 0.2},
                      'c': {'pop0': 0.6, 'pop1': 0.2, 'pop2': 0.2}},
                     'pop2':
                     {'a': {'pop0': 0.1, 'pop1': 0.6, 'pop2': 0.3},
                      'b': {'pop0': 0.6, 'pop1': 0.2, 'pop2': 0.2},
                      'c': {'pop0': 0.6, 'pop1': 0.2, 'pop2': 0.2}}}
    return flow_schedule
