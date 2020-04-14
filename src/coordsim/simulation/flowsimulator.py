import logging
import random
import numpy as np
from coordsim.network.flow import Flow
# from coordsim.metrics import metrics

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
        self.total_flow_count = 0

    def start(self):
        """
        Start the simulator.
        """
        log.info("Starting simulation")
        # Setting the all-pairs shortest path in the NetworkX network as a graph attribute
        log.info("Using nodes list {}\n".format(list(self.params.network.nodes.keys())))
        log.info("Total of {} ingress nodes available\n".format(len(self.params.ing_nodes)))
        if self.params.eg_nodes:
            log.info("Total of {} egress nodes available\n".format(len(self.params.eg_nodes)))
        for node in self.params.ing_nodes:
            node_id = node[0]
            self.env.process(self.generate_flow(node_id))

    def generate_flow(self, node_id):
        """
        Generate flows at the ingress nodes.
        """
        while self.params.inter_arr_mean[node_id] is not None:
            self.total_flow_count += 1

            # set normally distributed flow data rate
            flow_dr = np.random.normal(self.params.flow_dr_mean, self.params.flow_dr_stdev)

            # set deterministic or random flow arrival times and flow sizes according to config
            if self.params.deterministic_arrival:
                inter_arr_time = self.params.inter_arr_mean[node_id]
            else:
                # Poisson arrival -> exponential distributed inter-arrival time
                inter_arr_time = random.expovariate(lambd=1.0/self.params.inter_arr_mean[node_id])

            if self.params.deterministic_size:
                flow_size = self.params.flow_size_shape
            else:
                # heavy-tail flow size
                flow_size = np.random.pareto(self.params.flow_size_shape) + 1

            # Skip flows with negative flow_dr or flow_size values
            if flow_dr <= 0.00 or flow_size <= 0.00:
                continue

            # Assign a random SFC to the flow
            flow_sfc = np.random.choice([sfc for sfc in self.params.sfc_list.keys()])
            # Get the flow's creation time (current environment time)
            creation_time = self.env.now
            # Set the egress node for the flow if some are specified in the network file
            flow_egress_node = None
            if self.params.eg_nodes:
                flow_egress_node = random.choice(self.params.eg_nodes)
            # Generate flow based on given params
            flow = Flow(str(self.total_flow_count), flow_sfc, flow_dr, flow_size, creation_time,
                        current_node_id=node_id, egress_node_id=flow_egress_node)
            # Update metrics for the generated flow
            self.params.metrics.generated_flow(flow, node_id)
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
            log.info(f"Requested SFC was not found. Dropping flow {flow.flow_id}")
            # Update metrics for the dropped flow
            self.params.metrics.dropped_flow(flow)
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

        # set current sf of flow
        sf = sfc[flow.current_position]
        flow.current_sf = sf
        self.params.metrics.add_requesting_flow(flow)

        next_node = self.get_next_node(flow, sf)
        yield self.env.process(self.forward_flow(flow, next_node))

        log.info("Flow {} STARTED ARRIVING at node {} for processing. Time: {}"
                 .format(flow.flow_id, flow.current_node_id, self.env.now))
        yield self.env.process(self.process_flow(flow, sfc))

    def get_next_node(self, flow, sf):
        """
        Get next node using weighted probabilites from the scheduler
        """
        schedule = self.params.schedule
        # Check if scheduling rule exists
        if (flow.current_node_id in schedule) and flow.sfc in schedule[flow.current_node_id]:
            schedule_node = schedule[flow.current_node_id]
            schedule_sf = schedule_node[flow.sfc][sf]
            sf_nodes = [sch_sf for sch_sf in schedule_sf.keys()]
            sf_probability = [prob for name, prob in schedule_sf.items()]
            try:
                next_node = np.random.choice(sf_nodes, p=sf_probability)
                return next_node

            except Exception as ex:

                # Scheduling rule does not exist: drop flow
                log.warning(f'Flow {flow.flow_id}: Scheduling rule at node {flow.current_node_id} not correct'
                            f'Dropping flow!')
                log.warning(ex)
                self.params.metrics.dropped_flow(flow)
                self.env.exit()
        else:
            # Scheduling rule does not exist: drop flow
            log.warning(f'Flow {flow.flow_id}: Scheduling rule not found at {flow.current_node_id}. Dropping flow!')
            self.params.metrics.dropped_flow(flow)
            self.env.exit()

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
        self.params.metrics.add_path_delay(path_delay)
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
        current_node_id = flow.current_node_id
        sf = sfc[flow.current_position]
        flow.current_sf = sf

        log.info("Flow {} STARTED PROCESSING at node {} for processing. Time: {}"
                 .format(flow.flow_id, flow.current_node_id, self.env.now))

        if sf in self.params.sf_placement[current_node_id]:
            current_sf = flow.current_sf
            vnf_delay_mean = self.params.sf_list[flow.current_sf]["processing_delay_mean"]
            vnf_delay_stdev = self.params.sf_list[flow.current_sf]["processing_delay_stdev"]
            processing_delay = np.absolute(np.random.normal(vnf_delay_mean, vnf_delay_stdev))
            # Update metrics for the processing delay
            # Add the delay to the flow's end2end delay
            self.params.metrics.add_processing_delay(processing_delay)
            flow.end2end_delay += processing_delay

            # Calculate the demanded capacity when the flow is processed at this node
            demanded_total_capacity = 0.0
            for sf_i, sf_data in self.params.network.nodes[current_node_id]['available_sf'].items():
                if sf == sf_i:
                    # Include flows data rate in requested sf capacity calculation
                    demanded_total_capacity += self.params.sf_list[sf]['resource_function'](sf_data['load'] + flow.dr)
                else:
                    demanded_total_capacity += self.params.sf_list[sf_i]['resource_function'](sf_data['load'])

            # Get node capacities
            node_cap = self.params.network.nodes[current_node_id]["cap"]
            node_remaining_cap = self.params.network.nodes[current_node_id]["remaining_cap"]
            assert node_remaining_cap >= 0, "Remaining node capacity cannot be less than 0 (zero)!"
            if demanded_total_capacity <= node_cap:
                log.info("Flow {} started processing at sf {} at node {}. Time: {}, Processing delay: {}"
                         .format(flow.flow_id, current_sf, current_node_id, self.env.now, processing_delay))

                # Metrics: Add active flow to the SF once the flow has begun processing.
                self.params.metrics.add_active_flow(flow, current_node_id, current_sf)

                # Add load to sf
                self.params.network.nodes[current_node_id]['available_sf'][sf]['load'] += flow.dr
                # Set remaining node capacity
                self.params.network.nodes[current_node_id]['remaining_cap'] = node_cap - demanded_total_capacity
                # Set max node usage
                self.params.metrics.calc_max_node_usage(current_node_id, demanded_total_capacity)
                # Just for the sake of keeping lines small, the node_remaining_cap is updated again.
                node_remaining_cap = self.params.network.nodes[current_node_id]["remaining_cap"]

                yield self.env.timeout(processing_delay)
                log.info("Flow {} started departing sf {} at node {}. Time {}"
                         .format(flow.flow_id, current_sf, current_node_id, self.env.now))

                # Check if flow is currently in last SF, if so, then:
                # - Check if the flow has some Egress node set or not. If not then just depart. If Yes then:
                #   - check if the current node is the egress node. If Yes then depart. If No then forward the flow to
                #     the egress node using the shortest_path

                if flow.current_position == len(sfc) - 1:
                    if flow.current_node_id == flow.egress_node_id:
                        # Flow is processed and resides at egress node: depart flow
                        yield self.env.timeout(flow.duration)
                        self.depart_flow(flow)
                    elif flow.egress_node_id is None:
                        # Flow is processed and no egress node specified: depart flow
                        log.info(f'Flow {flow.flow_id} has no egress node, will depart from'
                                 f' current node {flow.current_node_id}. Time {self.env.now}.')
                        yield self.env.timeout(flow.duration)
                        self.depart_flow(flow)
                    else:
                        # Remove the active flow from the SF after it departed the SF on current node towards egress
                        self.params.metrics.remove_active_flow(flow, current_node_id, current_sf)
                        # Forward flow to the egress node and then depart from there
                        yield self.env.process(self.forward_flow(flow, flow.egress_node_id))
                        yield self.env.timeout(flow.duration)
                        # In this situation the last sf was never active for the egress node,
                        # so we should not remove it from the metrics
                        self.depart_flow(flow, remove_active_flow=False)
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
                    self.params.metrics.remove_active_flow(flow, current_node_id, current_sf)

                # Remove load from sf
                self.params.network.nodes[current_node_id]['available_sf'][sf]['load'] -= flow.dr
                assert self.params.network.nodes[current_node_id]['available_sf'][sf]['load'] >= 0, \
                    'SF load cannot be less than 0!'
                # Check if SF is not processing any more flows AND if SF is removed from placement. If so the SF will
                # be removed from the load recording. This allows SFs to be handed gracefully.
                if (self.params.network.nodes[current_node_id]['available_sf'][sf]['load'] == 0) and (
                        sf not in self.params.sf_placement[current_node_id]):
                    del self.params.network.nodes[current_node_id]['available_sf'][sf]

                # Recalculation is necessary because other flows could have already arrived or departed at the node
                used_total_capacity = 0.0
                for sf_i, sf_data in self.params.network.nodes[current_node_id]['available_sf'].items():
                    used_total_capacity += self.params.sf_list[sf_i]['resource_function'](sf_data['load'])
                # Set remaining node capacity
                self.params.network.nodes[current_node_id]['remaining_cap'] = node_cap - used_total_capacity
                # Just for the sake of keeping lines small, the node_remaining_cap is updated again.
                node_remaining_cap = self.params.network.nodes[current_node_id]["remaining_cap"]

                # We assert that remaining capacity must at all times be less than the node capacity so that
                # nodes dont put back more capacity than the node's capacity.
                assert node_remaining_cap <= node_cap, "Node remaining capacity cannot be more than node capacity!"
            else:
                log.info(f"Not enough capacity for flow {flow.flow_id} at node {flow.current_node_id}. Dropping flow.")
                # Update metrics for the dropped flow
                self.params.metrics.dropped_flow(flow)
                self.env.exit()
        else:
            log.info(f"SF {sf} was not found at {current_node_id}. Dropping flow {flow.flow_id}")
            self.params.metrics.dropped_flow(flow)
            self.env.exit()

    def depart_flow(self, flow, remove_active_flow=True):
        """
        Process the flow at the requested SF of the current node.
        """
        # Update metrics for the processed flow
        self.params.metrics.completed_flow()
        self.params.metrics.add_end2end_delay(flow.end2end_delay)
        if remove_active_flow:
            self.params.metrics.remove_active_flow(flow, flow.current_node_id, flow.current_sf)
        log.info("Flow {} was processed and departed the network from {}. Time {}"
                 .format(flow.flow_id, flow.current_node_id, self.env.now))
