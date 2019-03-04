import random


def generate_flow(env, node, rand_mean):
    # Print flow arrivals, departures and waiting for flow to end (duration) at a pre-specified rate
    flow_id = 0
    while True:
        duration = random.randint(0, 3)
        inter_arr_time = random.expovariate(rand_mean)
        env.process(flow_arrival(env, node, duration, flow_id))
        flow_id += 1
        yield env.timeout(inter_arr_time)
    

#Filter out non-ingree nodes 
def ingress_nodes(nodes):
    ing_nodes = []
    for node in nodes:
        if node["type"] == "ingress":
            ing_nodes.append(node)
    return ing_nodes


def flow_arrival(env, node, duration, flow_id):
    print("Flow {}{} arrived at time {}".format(node["name"], flow_id, env.now))
    yield env.timeout(duration)
    print("Flow {}{} departed at time {}".format(node["name"], flow_id, env.now))

 
def start_simulation(env, nodes, rand_mean=1.0, sim_rate=0):
    print("Starting simulation")
    print("Using nodes list {}\n".format(nodes))
    ing_nodes = ingress_nodes(nodes)

    print("Total of {} ingress nodes available: {}\n".format(len(ing_nodes), ing_nodes))
    for node in ing_nodes:
        env.process(generate_flow(env, node, rand_mean))


