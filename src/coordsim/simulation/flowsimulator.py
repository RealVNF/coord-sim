import random
import logging
import string
import numpy as np
# from coordsim.reader import networkreader
from coordsim.network.flow import Flow
from coordsim.network import scheduler
log = logging.getLogger(__name__)


def generate_flow(env, node, sf_placement, sfc_list, sf_list, rand_mean):
    # log.info flow arrivals, departures and waiting for flow to end (flow_duration) at a pre-specified rate
    while True:
        flow_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(6))
        # Random flow duration for each flow
        flow_duration = random.randint(0, 3)
        # Exponentially distributed random inter arrival rate using a user set (or default) mean
        inter_arr_time = random.expovariate(rand_mean)
        flow_id_str = "{}-{}".format(node.node_id, flow_id)
        flow_sfc = np.random.choice([sfc for sfc in sfc_list.keys()])
        flow = Flow(flow_id_str, flow_sfc, flow_duration, current_node_id=node.node_id)
        # Generate flows and schedule them at ingress node
        env.process(schedule_flow(env, node, flow, sf_placement, sfc_list, sf_list))
        yield env.timeout(inter_arr_time)


# Filter out non-ingree nodes
def ingress_nodes(nodes):
    ing_nodes = []
    for node in nodes:
        if node.node_type == "Ingress":
            ing_nodes.append(node)
    return ing_nodes


# Flow arrival and departure functions. Just logs that flow arrived and departed.
def process_flow(env, node, flow):
    log.info(
        "Flow {} processed by sf '{}' at node {}. Time {}"
        .format(flow.flow_id, flow.current_sf, node, env.now))


def flow_departure(env, node, flow):
    log.info("Flow {} was fully processed and departed network from {}. Time {}".format(flow.flow_id, node, env.now))


def flow_forward(env, node, next_node, flow):
    if(node.node_id == next_node):
        log.info("Flow {} stays in node {}. Time: {}.".format(flow.flow_id, flow.current_node_id, env.now))
    else:
        log.info("Flow {} departed node {} to node {}. Time {}"
                 .format(flow.flow_id, flow.current_node_id, next_node, env.now))
        flow.current_node_id = next_node


# Schedule flows. This function takes the generated flow object at the ingress node and handles it according
# to the requested SFC. We check if the SFC that is being requested is indeed within the schedule, otherwise
# we log a warning and drop the flow.
# The algorithm will check the flow's requested SFC, and will forward the flow through the network using the
# SFC's list of SFs based on the LB rules that are provided through the scheduler's 'flow_schedule()'
# function.
def schedule_flow(env, node, flow, sf_placement, sfc_list, sf_list):
    log.info(
        "Flow {} generated. arrived at node {} Requesting {} - flow duration: {}. Time: {}"
        .format(flow.flow_id, node.node_id, flow.sfc, flow.duration, env.now))
    schedule = scheduler.flow_schedule()
    sfc = sfc_list.get(flow.sfc, None)
    if sfc is not None:
        for index, sf in enumerate(sfc_list[flow.sfc]):
            schedule_sf = schedule[flow.current_node_id][sf]
            flow.current_sf = sf
            sf_nodes = [sch_sf for sch_sf in schedule_sf.keys()]
            sf_probability = [prob for name, prob in schedule_sf.items()]
            next_node = np.random.choice(sf_nodes, 1, sf_probability)[0]
            processing_delay = sf_list[sf].get("processing_delay", 0)
            if sf in sf_placement[next_node]:
                flow_forward(env, node, next_node, flow)
                process_flow(env, flow.current_node_id, flow)
                yield env.timeout(flow.duration + processing_delay)
                if(index == len(sfc_list[flow.sfc])-1):
                    flow_departure(env, flow.current_node_id, flow)
            else:
                log.warning("SF was not found at requested node. Dropping flow {}".format(flow.flow_id))
    else:
        log.warning("No Scheduling rule for requested SFC. Dropping flow {}".format(flow.flow_id))


def start_simulation(env, nodes, sf_placement, sfc_list, sf_list, rand_mean=1.0, sim_rate=0):
    log.info("Starting simulation")
    nodes_list = [(n.node_id, n.name) for n in nodes]
    log.info("Using nodes list {}\n".format(nodes_list))
    ing_nodes = ingress_nodes(nodes)
    log.info("Total of {} ingress nodes available\n".format(len(ing_nodes)))
    for node in ing_nodes:
        env.process(generate_flow(env, node, sf_placement, sfc_list, sf_list, rand_mean))
