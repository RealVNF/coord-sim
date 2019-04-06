import random
import logging
import numpy as np
# from coordsim.reader import networkreader
from coordsim.network.flow import Flow
from coordsim.network import scheduler
log = logging.getLogger(__name__)


def generate_flow(env, node, sf_placement, sfc_list, rand_mean):
    # log.info flow arrivals, departures and waiting for flow to end (flow_duration) at a pre-specified rate
    flow_id = 0
    while True:
        # Random flow duration for each flow
        flow_duration = random.randint(0, 3)
        # Exponentially distributed random inter arrival rate using a user set (or default) mean
        inter_arr_time = random.expovariate(rand_mean)
        flow_id_str = "{}-{}".format(node.node_id, flow_id)
        flow_sfc = np.random.choice([sfc for sfc in sfc_list.keys()])
        flow = Flow(flow_id_str, flow_sfc, flow_duration)
        # Generate flows and schedule them at ingress node
        env.process(schedule_flow(env, node, flow, sf_placement, sfc_list))
        flow_id += 1
        yield env.timeout(inter_arr_time)


# Filter out non-ingree nodes
def ingress_nodes(nodes):
    ing_nodes = []
    for node in nodes:
        if node.node_type == "Ingress":
            ing_nodes.append(node)
    return ing_nodes


# Flow arrival and departure functions. Just logs that flow arrived and departed.
def flow_arrival(env, node, flow):
    log.info(
        "Flow {} processed at sf '{}' node {} at time {}"
        .format(flow.flow_id, flow.current_sf, node, env.now))
    flow.current_node = node


def flow_departure(env, node, flow):
    log.info("Flow {} departed {} at time {}".format(flow.flow_id, node, env.now))


# Schedule flows. This function takes the generated flow object at the ingress node and handles it according
# to the requested SFC. We check if the SFC that is being requested is indeed within the schedule, otherwise
# we log a warning and drop the flow.
# The algorithm will check the flow's requested SFC, and will forward the flow through the network using the
# SFC's list of SFs based on the LB rules that are provided through the scheduler's 'flow_schedule()'
# function.
def schedule_flow(env, node, flow, sf_placement, sfc_list):
    log.info(
        "Flow {} generated. arrived at ingress node {} at time {} - Requesting {} - flow duration: {}"
        .format(flow.flow_id, node.node_id, env.now, flow.sfc, flow.duration))
    schedule = scheduler.flow_schedule()
    sfc = sfc_list.get(flow.sfc, None)
    if sfc is not None:
        for sf in sfc_list[flow.sfc]:
            schedule_sf = schedule[node.node_id][sf]
            flow.current_sf = sf
            sf_nodes = [sch_sf for sch_sf in schedule_sf.keys()]
            sf_probability = [prob for name, prob in schedule_sf.items()]
            next_node = np.random.choice(sf_nodes, 1, sf_probability)[0]
            node.node_id = next_node
            flow_arrival(env, next_node, flow)
            yield env.timeout(flow.duration)
            flow_departure(env, next_node, flow)
    else:
        log.warning("No Scheduling rule for requested SFC. Dropping flow {}".format(flow.flow_id))


def start_simulation(env, nodes, sf_placement, sfc_list, rand_mean=1.0, sim_rate=0):
    log.info("Starting simulation")
    nodes_list = [(n.node_id, n.name) for n in nodes]
    log.info("Using nodes list {}\n".format(nodes_list))
    ing_nodes = ingress_nodes(nodes)
    log.info("Total of {} ingress nodes available\n".format(len(ing_nodes)))
    for node in ing_nodes:
        env.process(generate_flow(env, node, sf_placement, sfc_list, rand_mean))
