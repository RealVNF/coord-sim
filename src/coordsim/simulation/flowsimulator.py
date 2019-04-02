import random
import logging

log = logging.getLogger(__name__)


def generate_flow(env, node, rand_mean):
    # log.info flow arrivals, departures and waiting for flow to end (flow_duration) at a pre-specified rate
    flow_id = 0
    while True:
        # Random flow duration for each flow
        flow_duration = random.randint(0, 3)
        # Exponentially distributed random inter arrival rate using a user set (or default) mean
        inter_arr_time = random.expovariate(rand_mean)
        # Let flows arrive concurrently, no need to wait for one flow to depart for another to arrive.
        env.process(flow_arrival(env, node, flow_duration, flow_id))
        flow_id += 1
        yield env.timeout(inter_arr_time)


# Filter out non-ingree nodes
def ingress_nodes(nodes):
    ing_nodes = []
    for node in nodes:
        if node["type"] == "Ingress":
            ing_nodes.append(node)
    return ing_nodes


# Flow arrival and departure function
def flow_arrival(env, node, flow_duration, flow_id):
    log.info("Flow {}-{} arrived at time {} - flow duration: {}".format(node["name"], flow_id, env.now, flow_duration))
    yield env.timeout(flow_duration)
    log.info("Flow {}-{} departed at time {} - flow duration: {}".format(node["name"], flow_id, env.now, flow_duration))


def start_simulation(env, nodes, rand_mean=1.0, sim_rate=0):
    log.info("Starting simulation")
    log.info("Using nodes list {}\n".format(nodes))
    ing_nodes = ingress_nodes(nodes)
    log.info("Total of {} ingress nodes available: {}\n".format(len(ing_nodes), ing_nodes))
    for node in ing_nodes:
        env.process(generate_flow(env, node, rand_mean))
