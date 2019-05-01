import random
import logging
import string
import numpy as np
# from coordsim.reader import networkreader
from coordsim.network.flow import Flow
from coordsim.network import scheduler
from coordsim.metrics import metrics
from coordsim.reader.networkreader import shortest_paths as sp
log = logging.getLogger(__name__)

shortest_paths = {}


# Start the simulator.
def start_simulation(env, network, sf_placement, sfc_list, sf_list, inter_arr_mean=1.0, flow_dr_mean=1.0,
                     flow_dr_stdev=1.0, flow_size_shape=1.0, vnf_delay_mean=1.0,
                     vnf_delay_stdev=1.0):
    log.info("Starting simulation")
    global shortest_paths
    shortest_paths = sp(network)
    nodes_list = [n[0] for n in network.nodes.items()]
    log.info("Using nodes list {}\n".format(nodes_list))
    ing_nodes = ingress_nodes(network)
    log.info("Total of {} ingress nodes available\n".format(len(ing_nodes)))
    for node in ing_nodes:
        node_id = node[0]
        env.process(generate_flow(env, node_id, sf_placement, sfc_list, sf_list, inter_arr_mean, network,
                                  flow_dr_mean, flow_dr_stdev, flow_size_shape, vnf_delay_mean, vnf_delay_stdev))


# Filter out non-ingree nodes.
def ingress_nodes(network):
    ing_nodes = []
    for node in network.nodes.items():
        if node[1]["type"] == "Ingress":
            ing_nodes.append(node)
    return ing_nodes


# Generate flows at the ingress nodes.
def generate_flow(env, node_id, sf_placement, sfc_list, sf_list, inter_arr_mean, network,
                  flow_dr_mean, flow_dr_stdev, flow_size_shape, vnf_delay_mean, vnf_delay_stdev):
    # log.info flow arrivals, departures and waiting for flow to end (flow_duration) at a pre-specified rate
    while True:
        flow_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(6))
        flow_id_str = "{}-{}".format(node_id, flow_id)
        # Exponentially distributed random inter arrival rate using a user set (or default) mean
        inter_arr_time = random.expovariate(inter_arr_mean)
        # Assign a random flow datarate and size according to a normal distribution with config. mean and stdev.
        # Abs here is necessary as normal dist. gives negative numbers.
        flow_dr = np.absolute(np.random.normal(flow_dr_mean, flow_dr_stdev))
        # Use a Pareto distribution (Heavy tail) random variable to generate flow sizes
        flow_size = np.absolute(np.random.pareto(flow_size_shape)) + 1
        # Normal Dist. may produce zeros. That is not desired. We skip the remainder of the loop.
        if flow_dr == 0 or flow_size == 0:
            continue
        flow_sfc = np.random.choice([sfc for sfc in sfc_list.keys()])
        # Generate flow based on given params
        flow = Flow(flow_id_str, flow_sfc, flow_dr, flow_size, current_node_id=node_id)
        # Update metrics for the generated flow
        metrics.generated_flow()
        # Generate flows and schedule them at ingress node
        env.process(flow_init(env, flow, sf_placement, sfc_list, sf_list, network, vnf_delay_mean,
                    vnf_delay_stdev))
        yield env.timeout(inter_arr_time)


# Initialize flows within the network. This function takes the generated flow object at the ingress node
# and handles it according to the requested SFC. We check if the SFC that is being requested is indeed
# within the schedule, otherwise we log a warning and drop the flow.
# The algorithm will check the flow's requested SFC, and will forward the flow through the network using the
# SFC's list of SFs based on the LB rules that are provided through the scheduler's 'flow_schedule()'
# function.
def flow_init(env, flow, sf_placement, sfc_list, sf_list, network, vnf_delay_mean, vnf_delay_stdev):
    log.info(
        "Flow {} generated. arrived at node {} Requesting {} - flow duration: {}, flow dr: {}. Time: {}"
        .format(flow.flow_id, flow.current_node_id, flow.sfc, flow.duration, flow.dr, env.now))
    sfc = sfc_list.get(flow.sfc, None)
    # Check to see if requested SFC exists
    if sfc is not None:
        # Iterate over the SFs and process the flow at each SF.
        yield env.process(schedule_flow(env, flow, network, sfc, vnf_delay_mean, vnf_delay_stdev, sf_placement))
    else:
        log.warning("No Scheduling rule for requested SFC. Dropping flow {}".format(flow.flow_id))
        # Update metrics for the dropped flow
        metrics.dropped_flow()
        env.exit()


# Schedule the flow
# This function is used in a mutual recursion alongside process_flow function to allow flows to arrive and begin
# processing without waiting for the flow to completely arrive.
# The mutual recursion is as follows:
# schedule_flow() -> process_flow() -> schedule_flow() and so on...
# Breaking condition: Flow reaches last position within the SFC, then process_flow() calls flow_departure()
# instead of schedule_flow(). The position of the flow within the SFC is determined using current_position
# attribute of the flow object.
def schedule_flow(env, flow, network, sfc, vnf_delay_mean, vnf_delay_stdev, sf_placement):
    sf = sfc[flow.current_position]
    flow.current_sf = sf
    next_node = get_next_node(flow, sf)
    yield env.process(flow_forward(env,network, flow, next_node))
    if sf in sf_placement[next_node]:
        log.info("Flow {} STARTED ARRIVING at SF {} at node {} for processing. Time: {}"
                 .format(flow.flow_id, flow.current_sf, flow.current_node_id, env.now))
        yield env.process(process_flow(env, flow, network,
                                       vnf_delay_mean, vnf_delay_stdev, sf_placement, sfc))
    else:
        log.warning("SF was not found at requested node. Dropping flow {}".format(flow.flow_id))
        env.exit()


# Get next node using weighted probabilites from the scheduler
def get_next_node(flow, sf):
    schedule = scheduler.flow_schedule()
    schedule_sf = schedule[flow.current_node_id][sf]
    sf_nodes = [sch_sf for sch_sf in schedule_sf.keys()]
    sf_probability = [prob for name, prob in schedule_sf.items()]
    next_node = np.random.choice(sf_nodes, 1, sf_probability)[0]
    return next_node


# Calculates the path delays occuring when forwarding a node
# Path delays are calculated using the Shortest path
# The delay is simulated by timing out for the delay amount of duration
def flow_forward(env, network, flow, next_node):
    path_delay = 0
    shortest_path = shortest_paths[flow.current_node_id][next_node]
    if len(shortest_path) > 1:
        for i in range(len(shortest_path)-1):
            source = shortest_path[0]
            destination = shortest_path[1]
            path_delay += network[source][destination]['delay']

    # Metrics calculation for path delay. Flow's end2end delay is also incremented.
    metrics.add_path_delay(path_delay)
    flow.end2end_delay += path_delay
    if path_delay:
        yield env.timeout(path_delay)
    if flow.current_node_id == next_node:
        log.info("Flow {} will stay in node {}. Time: {}.".format(flow.flow_id, flow.current_node_id, env.now))
    else:
        log.info("Flow {} will leave node {} towards node {}. Time {}"
                 .format(flow.flow_id, flow.current_node_id, next_node, env.now))
        flow.current_node_id = next_node


# Process the flow at the requested SF of the current node.
def process_flow(env, flow, network, vnf_delay_mean, vnf_delay_stdev, sf_placement, sfc):
    # Generate a processing delay for the SF
    processing_delay = np.absolute(np.random.normal(vnf_delay_mean, vnf_delay_stdev))
    # Update metrics for the processing delay
    # Add the delay to the flow's end2end delay
    metrics.add_processing_delay(processing_delay)
    flow.end2end_delay += processing_delay
    # Get node capacities
    log.info(
            "Flow {} started proccessing at sf '{}' at node {}. Time: {}, Processing delay: {}"
            .format(flow.flow_id, flow.current_sf, flow.current_node_id, env.now, processing_delay))
    node_cap = network.nodes[flow.current_node_id]["cap"]
    node_remaining_cap = network.nodes[flow.current_node_id]["remaining_cap"]
    assert node_remaining_cap >= 0, "Remaining node capacity cannot be less than 0 (zero)!"
    if flow.dr <= node_remaining_cap:
        node_remaining_cap -= flow.dr
        yield env.timeout(processing_delay)
        log.info(
            "Flow {} started departing sf '{}' at node {}. Time {}"
            .format(flow.flow_id, flow.current_sf, flow.current_node_id, env.now))
        # Check if flow is currently in last SF, if so, then depart flow.
        if(flow.current_position == len(sfc)-1):
            yield env.timeout(flow.duration)
            flow_departure(env, flow.current_node_id, flow)
        else:
            # Increment the position of the flow within SFC
            flow.current_position += 1
            env.process(schedule_flow(env, flow, network, sfc, vnf_delay_mean, vnf_delay_stdev, sf_placement))
            yield env.timeout(flow.duration)
            log.info("Flow {} FINISHED ARRIVING at SF {} at node {} for processing. Time: {}"
                     .format(flow.flow_id, flow.current_sf, flow.current_node_id, env.now))
        node_remaining_cap += flow.dr
        # We assert that remaining capacity must at all times be less than the node capacity so that
        # nodes dont put back more capacity than the node's capacity.
        assert node_remaining_cap <= node_cap, "Node remaining capacity cannot be more than node capacity!"
    else:
        log.warning("Not enough capacity for flow {} at node {}. Dropping flow."
                    .format(flow.flow_id, flow.current_node_id))
        # Update metrics for the dropped flow
        metrics.dropped_flow()
        env.exit()


# When the flow is in the last SF of the requested SFC. Depart it from the network.
def flow_departure(env, node_id, flow):
    # Update metrics for the processed flow
    metrics.processed_flow()
    metrics.add_end2end_delay(flow.end2end_delay)
    log.info("Flow {} was processed and departed the network from {}. Time {}".format(flow.flow_id, node_id, env.now))
