import random
import logging
import string
import numpy as np
from coordsim.network.flow import Flow
from coordsim.metrics import metrics
log = logging.getLogger(__name__)


"""
Flow Simulator class
This class holds the flow simulator and its internal flow handling functions.
Flow of data through the simulator (abstract):

start() -> generate_flow() -> init_flow() -> pass_flow() -> process_flow()
and forward_flow() -> depart_flow() or pass_flow()

"""


class FlowSimulator:
    def __init__(self, env, params):
        self.env = env
        self.params = params

    def start(self):
        """
        Start the simulator.
        """
        log.info("Starting simulation")
        # Setting the all-pairs shortest path in the NetworkX network as a graph attribute
        nodes_list = [n[0] for n in self.params.network.nodes.items()]
        log.info("Using nodes list {}\n".format(nodes_list))
        log.info("Total of {} ingress nodes available\n".format(len(self.params.ing_nodes)))
        for node in self.params.ing_nodes:
            node_id = node[0]
            self.env.process(self.generate_flow(node_id))

    def generate_flow(self, node_id):
        """
        Generate flows at the ingress nodes.
        """
        # log.info flow arrivals, departures and waiting for flow to end (flow_duration) at a pre-specified rate
        while True:
            flow_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(6))
            flow_id_str = "{}-{}".format(node_id, flow_id)
            # Exponentially distributed random inter arrival rate using a user set (or default) mean
            inter_arr_time = random.expovariate(self.params.inter_arr_mean)
            # Assign a random flow datarate and size according to a normal distribution with config. mean and stdev.
            # Abs here is necessary as normal dist. gives negative numbers.

            # TODO: Change the abs here as it is not a real mean anymore. Will affect result accuracy when
            # publishing.
            flow_dr = np.random.normal(self.params.flow_dr_mean, self.params.flow_dr_stdev)
            # Use a Pareto distribution (Heavy tail) random variable to generate flow sizes
            flow_size = np.random.pareto(self.params.flow_size_shape) + 1

            # Ignore negative flow_dr or flow_size values
            if(flow_dr <= 0.00 or flow_size <= 0.00):
                continue

            # Normal Dist. may produce zeros. That is not desired. We skip the remainder of the loop.
            # if flow_dr == 0 or flow_size == 0:
            #     continue
            # Assign a random SFC to the flow
            flow_sfc = np.random.choice([sfc for sfc in self.params.sfc_list.keys()])
            # Get the flow's creation time (current environment time)
            creation_time = self.env.now
            # Generate flow based on given params
            flow = Flow(flow_id_str, flow_sfc, flow_dr, flow_size, creation_time, current_node_id=node_id)
            # Update metrics for the generated flow
            metrics.generated_flow()
            # Generate flows and schedule them at ingress node
            self.env.process(self.init_flow(flow))
            yield self.env.timeout(inter_arr_time)

    def init_flow(self, flow):
        """
        Initialize flows within the network. This function takes the generated flow object at the ingress node
        and handles it according to the requested SFC. We check if the SFC that is being requested is indeed
        within the schedule, otherwise we log a warning and drop the flow.
        The algorithm will check the flow's requested SFC, and will forward the flow through the network using the
        SFC's list of SFs based on the LB rules that are provided through the scheduler's 'flow_schedule()'
        function.
        """
        log.info(
            "Flow {} generated. arrived at node {} Requesting {} - flow duration: {}ms, "
            "flow dr: {}. Time: {}".format(flow.flow_id, flow.current_node_id, flow.sfc, flow.duration, flow.dr,
                                           self.env.now))
        sfc = self.params.sfc_list[flow.sfc]
        # Check to see if requested SFC exists
        if sfc is not None:
            # Iterate over the SFs and process the flow at each SF.
            yield self.env.process(self.pass_flow(flow, sfc))
        else:
            log.warning("No Scheduling rule for requested SFC. Dropping flow {}".format(flow.flow_id))
            # Update metrics for the dropped flow
            metrics.dropped_flow()
            self.env.exit()

    def pass_flow(self, flow, sfc):
        """
        Passes the flow to the next node to begin processing.
        The flow might still be arriving at a previous node or SF.
        This function is used in a mutual recursion alongside process_flow() function to allow flows to arrive and begin
        processing without waiting for the flow to completely arrive.
        The mutual recursion is as follows:
        pass_flow() -> process_flow() -> pass_flow() and so on...
        Breaking condition: Flow reaches last position within the SFC, then process_flow() calls depart_flow()
        instead of pass_flow(). The position of the flow within the SFC is determined using current_position
        attribute of the flow object.
        """
        sf = sfc[flow.current_position]
        flow.current_sf = sf
        next_node = self.get_next_node(flow, sf)
        yield self.env.process(self.forward_flow(flow, next_node))
        if sf in self.params.sf_placement[next_node]:
            log.info("Flow {} STARTED ARRIVING at SF {} at node {} for processing. Time: {}"
                     .format(flow.flow_id, flow.current_sf, flow.current_node_id, self.env.now))
            yield self.env.process(self.process_flow(flow, sfc))
        else:
            log.warning("SF was not found at requested node. Dropping flow {}".format(flow.flow_id))
            self.env.exit()

    def get_next_node(self, flow, sf):
        """
        Get next node using weighted probabilites from the scheduler
        """
        schedule = self.params.schedule
        schedule_sf = schedule[flow.current_node_id][flow.sfc][sf]
        sf_nodes = [sch_sf for sch_sf in schedule_sf.keys()]
        sf_probability = [prob for name, prob in schedule_sf.items()]
        next_node = np.random.choice(sf_nodes, 1, sf_probability)[0]
        return next_node

    def forward_flow(self, flow, next_node):
        """
        Calculates the path delays occurring when forwarding a node
        Path delays are calculated using the Shortest path
        The delay is simulated by timing out for the delay amount of duration
        """
        path_delay = 0
        if flow.current_node_id != next_node:
            path_delay = self.params.network.graph['shortest_paths'][(flow.current_node_id, next_node)][1]

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

    def process_flow(self, flow, sfc):
        """
        Process the flow at the requested SF of the current node.
        """
        # Generate a processing delay for the SF
        current_sf = flow.current_sf
        current_node_id = flow.current_node_id
        vnf_delay_mean = self.params.sf_list[flow.current_sf]["processing_delay_mean"]
        vnf_delay_stdev = self.params.sf_list[flow.current_sf]["processing_delay_stdev"]
        processing_delay = np.absolute(np.random.normal(vnf_delay_mean, vnf_delay_stdev))
        # Update metrics for the processing delay
        # Add the delay to the flow's end2end delay
        metrics.add_processing_delay(processing_delay)
        flow.end2end_delay += processing_delay
        # Get node capacities
        node_cap = self.params.network.nodes[flow.current_node_id]["cap"]
        node_remaining_cap = self.params.network.nodes[flow.current_node_id]["remaining_cap"]
        assert node_remaining_cap >= 0, "Remaining node capacity cannot be less than 0 (zero)!"
        # Metrics: Add active flow to the SF once the flow has begun processing.
        metrics.add_active_flow(flow, current_node_id, current_sf)
        if flow.dr <= node_remaining_cap:
            log.info(
                "Flow {} started proccessing at sf '{}' at node {}. Time: {}, "
                "Processing delay: {}".format(flow.flow_id, current_sf, current_node_id, self.env.now,
                                              processing_delay))
            
            # print(metrics.get_metrics()['current_traffic'])
            node_remaining_cap -= flow.dr
            yield self.env.timeout(processing_delay)
            log.info(
                "Flow {} started departing sf '{}' at node {}."
                " Time {}".format(flow.flow_id, flow.current_sf, flow.current_node_id, self.env.now))
            # Check if flow is currently in last SF, if so, then depart flow.

            if (flow.current_position == len(sfc) - 1):
                yield self.env.timeout(flow.duration)
                self.depart_flow(flow)
            else:
                # Increment the position of the flow within SFC
                flow.current_position += 1
                self.env.process(self.pass_flow(flow, sfc))
                yield self.env.timeout(flow.duration)
                # before departing the SF.
                # print(metrics.get_metrics()['current_active_flows'])
                log.info("Flow {} FINISHED ARRIVING at SF {} at node {} for processing. Time: {}"
                         .format(flow.flow_id, current_sf, current_node_id, self.env.now))
                # Remove the active flow from the SF after it departed the SF
                metrics.remove_active_flow(flow, current_node_id, current_sf)
            node_remaining_cap += flow.dr
            # We assert that remaining capacity must at all times be less than the node capacity so that
            # nodes dont put back more capacity than the node's capacity.
            assert node_remaining_cap <= node_cap, "Node remaining capacity cannot be more than node capacity!"
        else:
            log.warning("Not enough capacity for flow {} at node {}. Dropping flow."
                        .format(flow.flow_id, flow.current_node_id))
            # Update metrics for the dropped flow
            metrics.dropped_flow()
            metrics.remove_active_flow(flow, current_node_id, current_sf)
            self.env.exit()

    def depart_flow(self, flow):
        """
        Process the flow at the requested SF of the current node.
        """
        # Update metrics for the processed flow
        metrics.processed_flow()
        metrics.add_end2end_delay(flow.end2end_delay)
        metrics.remove_active_flow(flow, flow.current_node_id, flow.current_sf)
        log.info("Flow {} was processed and departed the network from {}. Time {}"
                 .format(flow.flow_id, flow.current_node_id, self.env.now))
