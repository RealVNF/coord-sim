import random


def generate_flow(env, node, rate, duration):
    # Print flow arrivals, departures and waiting for flow to end (duration) at a pre-specified rate
    flow_id = 0
    while True:
        print("Flow {}{} arrived at time {}".format(node["name"], flow_id, env.now))
        yield env.timeout(duration)
        print("Flow {}{} departed at time {}".format(node["name"], flow_id, env.now))
        flow_id += 1
        yield env.timeout(rate)
    
    

#Filter out non-ingree nodes 
def ingress_nodes(nodes):
    ing_nodes = []
    for node in nodes:
        if node["type"] == "ingress":
            ing_nodes.append(node)
    return ing_nodes


def start_simulation(env, nodes, sim_rate=0):
    ing_nodes = ingress_nodes(nodes)
    for node in ing_nodes:
        duration = random.randint(0, 3)
        rate = random.random()
        env.process(generate_flow(env, node, rate, duration))
