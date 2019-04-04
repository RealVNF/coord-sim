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
        sfc = [sfc for sfc in sfc_list.keys()]
        flow_sfc = np.random.choice([sfc for sfc in sfc_list.keys()])
        flow = Flow(flow_id, flow_sfc, flow_duration)
        # Let flows arrive concurrently, no need to wait for one flow to depart for another to arrive.
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


# Flow arrival and departure function
def flow_arrival(env, node, flow):
    if isinstance(node, str):
        log.info("Flow {} arrived at {} at time {} - current sf {} - flow duration: {}".format(flow.flow_id, node, env.now, flow.current_sf, flow.duration))
        flow.current_node = node
    else: 
        log.info("Flow {} arrived at {} at time {} - current sf {} - flow duration: {}".format(flow.flow_id, node.node_id, env.now, flow.current_sf, flow.duration))
        flow.current_node = node.name
    
    #yield env.timeout(flow.flow_duration)
    #log.info("Flow {} departed {} at time {} - flow duration: {}".format(flow.flow_id, node.name, env.now, flow.duration))


def flow_departure(env, node, flow):

    log.info("Flow {} departed {} at time {} - flow duration: {}".format(flow.flow_id, node, env.now, flow.duration))


def schedule_flow(env, node, flow, sf_placement, sfc_list):
    log.info("Flow {} arrived at {} at time {} - Requesting {} - flow duration: {}".format(flow.flow_id, node.node_id, env.now, flow.sfc, flow.duration))
    schedule = scheduler.flow_schedule()
    sfc = sfc_list.get(flow.sfc, None)
    if sfc is not None:
        for sf in sfc_list[flow.sfc]:
            schedule_sf = schedule[sf]
            flow.current_sf = sf
            if sf is None:
                log.warning("No Scheduling rule for requested SF. Dropping flow {}".format(flow.flow_id))
                break
            else:
                sf_nodes = [sch_sf for sch_sf in schedule_sf.keys()]
                sf_probability = [prob for name, prob in schedule_sf.items()]
                next_node = np.random.choice(sf_nodes, 1, sf_probability)[0]
                flow_arrival(env, next_node, flow)
                flow_departure(env, next_node, flow)
        yield env.timeout(1)
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
