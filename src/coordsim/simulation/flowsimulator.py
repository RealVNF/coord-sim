import random
import logging
import string
import numpy as np
from coordsim.network.flow import Flow
from coordsim.metrics import metrics
from coordsim.reader.networkreader import shortest_paths as sp
log = logging.getLogger(__name__)

shortest_paths = {}


class FlowSimulator:
    def __init__(self, env, params):
        self.env = env
        self.params = params

    # Start the simulator.
    def start_simulator(self):
        log.info("Starting simulation")
        global shortest_paths
        shortest_paths = sp(self.params.network)
        nodes_list = [n[0] for n in self.params.network.nodes.items()]
        log.info("Using nodes list {}\n".format(nodes_list))
        ing_nodes = self.ingress_nodes()
        log.info("Total of {} ingress nodes available\n".format(len(ing_nodes)))
        for node in ing_nodes:
            node_id = node[0]
            self.env.process(self.generate_flow(node_id))

    # Filter out non-ingree nodes.
    def ingress_nodes(self):
        ing_nodes = []
        for node in self.params.network.nodes.items():
            if node[1]["type"] == "Ingress":
                ing_nodes.append(node)
        return ing_nodes

    # Generate flows at the ingress nodes.
    def generate_flow(self, node_id):
        # log.info flow arrivals, departures and waiting for flow to end (flow_duration) at a pre-specified rate
        while True:
            flow_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(6))
            flow_id_str = "{}-{}".format(node_id, flow_id)
            # Exponentially distributed random inter arrival rate using a user set (or default) mean
            inter_arr_time = random.expovariate(self.params.inter_arr_mean)
            # Assign a random flow datarate and size according to a normal distribution with config. mean and stdev.
            # Abs here is necessary as normal dist. gives negative numbers.

            # Todo: Change the abs here as it is not a real mean anymore. Will affect result accuracy when
            # publishing.
            flow_dr = np.absolute(np.random.normal(self.params.flow_dr_mean, self.params.flow_dr_stdev))
            # Use a Pareto distribution (Heavy tail) random variable to generate flow sizes
            flow_size = np.absolute(np.random.pareto(self.params.flow_size_shape)) + 1
            # Normal Dist. may produce zeros. That is not desired. We skip the remainder of the loop.
            if flow_dr == 0 or flow_size == 0:
                continue
            flow_sfc = np.random.choice([sfc for sfc in self.params.sfc_list.keys()])
            # Generate flow based on given params
            flow = Flow(flow_id_str, flow_sfc, flow_dr, flow_size, current_node_id=node_id)
            # Update metrics for the generated flow
            metrics.generated_flow()
            # Generate flows and schedule them at ingress node
            self.env.process(self.flow_init(flow))
            yield self.env.timeout(inter_arr_time)

    # Initialize flows within the network. This function takes the generated flow object at the ingress node
    # and handles it according to the requested SFC. We check if the SFC that is being requested is indeed
    # within the schedule, otherwise we log a warning and drop the flow.
    # The algorithm will check the flow's requested SFC, and will forward the flow through the network using the
    # SFC's list of SFs based on the LB rules that are provided through the scheduler's 'flow_schedule()'
    # function.
    def flow_init(self, flow):
        log.info(
            "Flow {} generated. arrived at node {} Requesting {} - flow duration: {}ms, "
            "flow dr: {}. Time: {}".format(flow.flow_id, flow.current_node_id, flow.sfc, flow.duration, flow.dr,
                                           self.env.now))
        sfc = self.params.sfc_list[flow.sfc]
        # Check to see if requested SFC exists
        if sfc is not None:
            # Iterate over the SFs and process the flow at each SF.
            yield self.env.process(self.schedule_flow(flow, sfc))
        else:
            log.warning("No Scheduling rule for requested SFC. Dropping flow {}".format(flow.flow_id))
            # Update metrics for the dropped flow
            metrics.dropped_flow()
            self.env.exit()

    # Schedule the flow
    # This function is used in a mutual recursion alongside process_flow function to allow flows to arrive and begin
    # processing without waiting for the flow to completely arrive.
    # The mutual recursion is as follows:
    # schedule_flow() -> process_flow() -> schedule_flow() and so on...
    # Breaking condition: Flow reaches last position within the SFC, then process_flow() calls flow_departure()
    # instead of schedule_flow(). The position of the flow within the SFC is determined using current_position
    # attribute of the flow object.
    def schedule_flow(self, flow, sfc):
        sf = sfc[flow.current_position]
        flow.current_sf = sf
        next_node = self.get_next_node(flow, sf)
        yield self.env.process(self.flow_forward(flow, next_node))
        if sf in self.params.sf_placement[next_node]:
            # Metrics: Add active flow to the SF the flow is arriving to.
            metrics.add_active_flow(flow)
            log.info("Flow {} STARTED ARRIVING at SF {} at node {} for processing. Time: {}"
                     .format(flow.flow_id, flow.current_sf, flow.current_node_id, self.env.now))
            yield self.env.process(self.process_flow(flow, sfc))
        else:
            log.warning("SF was not found at requested node. Dropping flow {}".format(flow.flow_id))
            self.env.exit()

    # Get next node using weighted probabilites from the scheduler
    def get_next_node(self, flow, sf):
        schedule = self.params.schedule
        schedule_sf = schedule[flow.current_node_id][flow.sfc][sf]
        sf_nodes = [sch_sf for sch_sf in schedule_sf.keys()]
        sf_probability = [prob for name, prob in schedule_sf.items()]
        next_node = np.random.choice(sf_nodes, 1, sf_probability)[0]
        return next_node

    # Calculates the path delays occuring when forwarding a node
    # Path delays are calculated using the Shortest path
    # The delay is simulated by timing out for the delay amount of duration
    def flow_forward(self, flow, next_node):
        path_delay = 0
        if flow.current_node_id != next_node:
            path_delay = shortest_paths[(flow.current_node_id, next_node)][1]

        # Metrics calculation for path delay. Flow's end2end delay is also incremented.
        metrics.add_path_delay(path_delay)
        flow.end2end_delay += path_delay
        if flow.current_node_id == next_node:
            assert path_delay == 0, "While Forwarding the flow, the Current and Next node same, yet path_delay != 0"
            log.info("Flow {} will stay in node {}. Time: {}.".format(flow.flow_id, flow.current_node_id, self.env.now))
        else:
            log.info("Flow {} will leave node {} towards node {}. Time {}"
                     .format(flow.flow_id, flow.current_node_id, next_node, self.env.now))
            yield self.env.timeout(path_delay)
            flow.current_node_id = next_node

    # Process the flow at the requested SF of the current node.
    def process_flow(self, flow, sfc):
        # Generate a processing delay for the SF
        vnf_delay_mean = self.params.sf_list[flow.current_sf]["processing_delay_mean"]
        vnf_delay_stdev = self.params.sf_list[flow.current_sf]["processing_delay_stdev"]
        processing_delay = np.absolute(np.random.normal(vnf_delay_mean, vnf_delay_stdev))
        # Update metrics for the processing delay
        # Add the delay to the flow's end2end delay
        metrics.add_processing_delay(processing_delay)
        flow.end2end_delay += processing_delay
        # Get node capacities
        log.info(
            "Flow {} started proccessing at sf '{}' at node {}. Time: {}, "
            "Processing delay: {}".format(flow.flow_id, flow.current_sf, flow.current_node_id, self.env.now,
                                          processing_delay))
        node_cap = self.params.network.nodes[flow.current_node_id]["cap"]
        node_remaining_cap = self.params.network.nodes[flow.current_node_id]["remaining_cap"]
        assert node_remaining_cap >= 0, "Remaining node capacity cannot be less than 0 (zero)!"
        if flow.dr <= node_remaining_cap:
            node_remaining_cap -= flow.dr
            yield self.env.timeout(processing_delay)
            log.info(
                "Flow {} started departing sf '{}' at node {}."
                " Time {}".format(flow.flow_id, flow.current_sf, flow.current_node_id, self.env.now))
            # Check if flow is currently in last SF, if so, then depart flow.
            # metrics.remove_active_flow(flow)
            if (flow.current_position == len(sfc) - 1):
                yield self.env.timeout(flow.duration)
                self.flow_departure(self, flow.current_node_id, flow)
            else:
                # Increment the position of the flow within SFC
                flow.current_position += 1
                self.env.process(self.schedule_flow(flow, sfc))
                yield self.env.timeout(flow.duration)
                # before departing the SF.
                log.info("Flow {} FINISHED ARRIVING at SF {} at node {} for processing. Time: {}"
                         .format(flow.flow_id, flow.current_sf, flow.current_node_id, self.env.now))
                # Remove the active flow from the SF after it departed the SF
                metrics.remove_active_flow(flow)
            node_remaining_cap += flow.dr
            # We assert that remaining capacity must at all times be less than the node capacity so that
            # nodes dont put back more capacity than the node's capacity.
            assert node_remaining_cap <= node_cap, "Node remaining capacity cannot be more than node capacity!"
        else:
            log.warning("Not enough capacity for flow {} at node {}. Dropping flow."
                        .format(flow.flow_id, flow.current_node_id))
            # Update metrics for the dropped flow
            metrics.dropped_flow()
            metrics.remove_active_flow(flow)
            self.env.exit()

    # When the flow is in the last SF of the requested SFC. Depart it from the network.
    def flow_departure(self, node_id, flow):
        # Update metrics for the processed flow
        metrics.processed_flow()
        metrics.remove_active_flow(flow)
        metrics.add_end2end_delay(flow.end2end_delay)
        log.info("Flow {} was processed and departed the network from {}. Time {}".format(flow.flow_id, node_id,
                                                                                          self.env.now))
