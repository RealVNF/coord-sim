import logging
import random
import numpy as np
from coordsim.network.flow import Flow
from coordsim.metrics import metrics
log = logging.getLogger(__name__)


"""
Flow Simulator class
This class holds the flow simulator and its internal flow handling functions.
The abstracted core logic of the simulator is presented in the following chart. Boxed names present SimPy processes,
directed links illustrate how processes interact with each other, by spawning a new instance of the corresponding SimPy process.

                                                                  +-------------------------------------------------------------+
                                                                  |                                                             |
                                                                  |                                                             |
                      +---------------+          +-----------+    V     +-----------+          +--------------------------+     |
start() ----+-------->+ generate_flow +--------->+ init_flow +----o---->+ pass_flow +----+---->+ forward_flow_to_neighbor +---->o
            |         +---------------+          +-----------+          +-----------+    |     +--------------------------+     ^
            |                                                                            |                                      |
            |         +----------------------+                                           |     +--------------+                 |
            +-------->+ periodic_measurement |                                           +---->+ process_flow +-----------------+
                      +----------------------+                                           |     +--------------+
                                                                                         |
                                                                                         |
                                                                                         |     +-------------+
                                                                                         +---->+ depart_flow |
                                                                                               +-------------+
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
        nodes_list = [n[0] for n in self.params.network.nodes.items()]
        log.info("Using nodes list {}\n".format(nodes_list))
        log.info("Total of {} ingress nodes available\n".format(len(self.params.ing_nodes)))
        for node in self.params.ing_nodes:
            node_id = node[0]
            self.env.process(self.generate_flow(node_id))
        # Start periodic measurement process
        self.env.process(self.periodic_measurement())

    def periodic_measurement(self):
        """
        SimPy process.
        This process allows external algorithms to capture simulator state in a specified intervals, independent of the
        overall simulation run duration and algorithm interaction.

        The process interaction is visualized as:

             +----------------------+
        ---->+ periodic_measurement |
             +----------------------+
        """
        while True:
            log.debug(f'measurement interception. Time {self.env.now}.')
            # Allow algorithm to collect state for measurement, invoke interception callback
            if 'periodic_measurement' in self.params.interception_callbacks:
                self.params.interception_callbacks['periodic_measurement']()
            yield self.env.timeout(self.params.inter_measurement)

    def generate_flow(self, node_id):
        """
        SimPy process.
        Generates flows at the ingress nodes.

        The process interaction is visualized as:

             +---------------+          +-----------+
        ---->+ generate_flow +--------->+ init_flow +---->
             +---------------+          +-----------+
        """
        while True:
            self.total_flow_count += 1

            # set normally distributed flow data rate
            flow_dr = np.random.normal(self.params.flow_dr_mean, self.params.flow_dr_stdev)

            # if "deterministic = True" use deterministic flow size and inter-arrival times (eg, for debugging)
            if self.params.deterministic:
                # Exponentially distributed random inter arrival rate using a user set (or default) mean
                #
                # use deterministic, fixed inter-arrival time for now
                inter_arr_time = self.params.inter_arr_mean
                flow_size = self.params.flow_size_shape
            # else use randomly distributed values (default)
            else:
                inter_arr_time = random.expovariate(self.params.inter_arr_mean)
                # heavy-tail flow size
                flow_size = np.random.pareto(self.params.flow_size_shape) + 1
            # Skip flows with negative flow_dr or flow_size values
            if flow_dr <= 0.00 or flow_size <= 0.00:
                continue

            # Assign a random SFC to the flow
            flow_sfc_id = np.random.choice([sfc for sfc in self.params.sfc_list.keys()])
            flow_sfc_components = self.params.sfc_list[flow_sfc_id]
            # Get the flow's creation time (current environment time)
            creation_time = self.env.now
            # Generate flow based on given params
            flow = Flow(str(self.total_flow_count), flow_sfc_id, flow_sfc_components, flow_dr, flow_size, creation_time,
                        current_node_id=node_id, )
            # Update metrics for the generated flow
            metrics.generated_flow()
            # Generate flows and schedule them at ingress node
            self.env.process(self.init_flow(flow))
            yield self.env.timeout(inter_arr_time)

    def init_flow(self, flow):
        """
        SimPy process.
        Initializes flows within the network. This function takes the generated flow object at the ingress node
        and handles it according to the requested SFC. We check if the SFC that is being requested is indeed
        within the schedule, otherwise we log a warning and drop the flow.
        The algorithm will check the flow's requested SFC, and will forward the flow through the network using the
        SFC's list of SFs based on the LB rules that are provided through the scheduler's 'flow_schedule()'
        function.

        The process interaction is visualized as:

             +-----------+          +-----------+
        ---->+ init_flow +--------->+ pass_flow |---->
             +-----------+          +-----------+
        """
        log.info(
            "Flow {} generated. arrived at node {} Requesting {} - flow duration: {}ms, "
            "flow dr: {}. Time: {}".format(flow.flow_id, flow.current_node_id, flow.sfc_id, flow.duration, flow.dr,
                                           self.env.now))
        sfc = self.params.sfc_list[flow.sfc_id]
        # Check to see if requested SFC exists
        if sfc is not None:
            # Iterate over the SFs and process the flow at each SF.
            yield self.env.process(self.pass_flow(flow, sfc))
        else:
            log.info(f"Requested SFC was not found. Dropping flow {flow.flow_id}")
            self.drop_flow(flow)
            self.env.exit()

    def pass_flow(self, flow, sfc):
        """
        SimPy process.
        Passes the flow to the node, to decide how to handle it.
        The flow might still be arriving at a previous node or SF.

        This process is used in a recursion alongside forward_flow_to_neighbor and process_flow
        processes to allow flows to arrive and begin further handling without waiting for the flow to completely arrive.
        The recursion is as follows:

            +-------------------------------------------------------------+
            |                                                             |
            |                                                             |
            V     +-----------+          +--------------------------+     |
        ----o---->+ pass_flow +----+---->+ forward_flow_to_neighbor +---->o
                  +-----------+    |     +--------------------------+     ^
                                   |                                      |
                                   |     +--------------+                 |
                                   +---->+ process_flow +-----------------+
                                   |     +--------------+
                                   |
                                   |
                                   |     +-------------+
                                   +---->+ depart_flow |
                                         +-------------+

        Breaking condition: Flow reaches last position within the SFC, then pass_flow creates depart_flow process.
        The position of the flow within the SFC is determined using current_position attribute of the flow object.
        if (flow.current_position == len(sfc))
        """
        # Determine flow status
        flow_is_processed = (flow.current_position == len(sfc))
        if not flow_is_processed:
            # Flow not fully processed, update next service function before callback interception
            flow.current_sf = sfc[flow.current_position]
        # Invoke interception callback
        if 'pass_flow' in self.params.interception_callbacks:
            self.params.interception_callbacks['pass_flow'](flow)

        # Decide how to handle the flow
        if flow_is_processed:
            if flow.current_node_id == flow.destination_id:
                # Flow head is processed and resides at egress node: depart flow
                self.env.process(self.depart_flow(flow))
            elif flow.destination_id is None:
                # Flow head is processed and resides at egress node: depart flow
                log.info(f'Flow {flow.flow_id} has no egress node, will depart from current node {flow.current_node_id}. Time {self.env.now}.')
                self.env.process(self.depart_flow(flow))
            else:
                # Forward flow
                next_node = self.get_next_node(flow)
                yield self.env.process(self.forward_flow_to_neighbor(flow, next_node))

        else:
            # Flow is not fully processed, get next service function
            sf = sfc[flow.current_position]

            flow_processing_rules = self.params.flow_processing_rules
            if (flow.current_node_id in flow_processing_rules) and (flow.flow_id in flow_processing_rules[flow.current_node_id]):
                # Try to process Flow
                processing_rule = flow_processing_rules[flow.current_node_id][flow.flow_id]
                if sf in processing_rule:
                    # Flow has permission to be processed for requested service. Check if service function actually exists
                    if sf in self.params.sf_placement[flow.current_node_id]:
                        log.info(f'Flow {flow.flow_id} STARTED ARRIVING at SF {flow.current_sf} at node {flow.current_node_id} for processing. Time: {self.env.now}')
                        yield self.env.process(self.process_flow(flow, sfc))
                    else:
                        log.warning(f'SF was not found at requested node. Dropping flow {flow.flow_id}.')
                        self.drop_flow(flow)
                        self.env.exit()
                else:
                    # Flow has no permission for requested service: fallback to forward flow
                    log.debug(f'Flow {flow.flow_id}: Processing rules exists at {flow.current_node_id}, but not for SF {flow.current_sf}. Fallback to forward.')
                    next_node = self.get_next_node(flow, sf)
                    yield self.env.process(self.forward_flow_to_neighbor(flow, next_node))

            else:
                # There are no rules which instruct the flow to be processed at this node: forward flow
                next_node = self.get_next_node(flow, sf)
                yield self.env.process(self.forward_flow_to_neighbor(flow, next_node))

    def get_next_node(self, flow, sf=None):
        """
        Determine next node for a flow from its current node
        First individual flow forwarding rules will be checked, if none exists it will fallback to general
        scheduling policy. If no forwarding target can determined, the flow will be dropped.
        """
        schedule = self.params.schedule
        flow_forwarding_rules = self.params.flow_forwarding_rules

        if (flow.current_node_id in flow_forwarding_rules) and (flow.flow_id in flow_forwarding_rules[flow.current_node_id]):
            # Check if individual forwarding rule exists
            next_node = flow_forwarding_rules[flow.current_node_id][flow.flow_id]
            return next_node

        elif (sf is not None) and (flow.current_node_id in schedule) and (flow.sfc_id in schedule[flow.current_node_id]):
            # Check if scheduling rule exists
            schedule_node = schedule[flow.current_node_id]
            schedule_sf = schedule_node[flow.sfc_id][sf]
            sf_nodes = [sch_sf for sch_sf in schedule_sf.keys()]
            sf_probability = [prob for name, prob in schedule_sf.items()]
            try:
                next_node = np.random.choice(sf_nodes, p=sf_probability)
                log.warning(f'Flow {flow.flow_id}: Had to fallback to scheduling policy at {flow.current_node_id}.')
                return next_node

            except Exception as ex:
                # Next node could not determined with given scheduling policy: drop flow
                log.warning(f'Flow {flow.flow_id}: Scheduling rule at node {flow.current_node_id} not correct'
                            f'Dropping flow!')
                log.warning(ex)
                self.drop_flow(flow)
                self.env.exit()
        else:
            # Next node could not determined: drop flow
            log.warning(f'Flow {flow.flow_id}: Forwarding rule not found at {flow.current_node_id}. Dropping flow!')
            self.drop_flow(flow)
            self.env.exit()

    def forward_flow_to_neighbor(self, flow, neighbor_id):
        '''
        SimPy process.
        Forwards the flow over a link from the current node to a direct neighbor. Forwarding a flow to itself is not
        permitted.
        Link capacities are claimed as soon as the flow starts traversing the link and will not be freed before the
        flow has completely traversed the link. If not enough capacity is available the flow will be dropped

        The process interaction is visualized as:

              +--------------------------+          +-----------+
        ----->+ forward_flow_to_neighbor +--------->+ pass_flow +---->
              +--------------------------+          +-----------+
        '''
        if neighbor_id not in self.params.network.neighbors(flow.current_node_id):
            # Forwarding target is actually not a neighbor of the flows current node: drop flow
            log.warning(f'Flow {flow.flow_id}: Cannot forward from node {flow.current_node_id} to node {neighbor_id} over non-existent link. Dropping flow!')
            self.drop_flow(flow)
            self.env.exit()
        else:
            forwarding_link = self.params.network[flow.current_node_id][neighbor_id]
            assert forwarding_link['remaining_cap'] >= 0, "Remaining link capacity cannot be less than 0 (zero)!"
            # Check if link has enough capacity
            if flow.dr <= forwarding_link['remaining_cap']:
                # Flow will be forwarded
                link_delay = forwarding_link['delay']
                # Claim link capacities
                forwarding_link['remaining_cap'] -= flow.dr
                log.info(f'Flow {flow.flow_id} will leave node {flow.current_node_id} towards node {neighbor_id}. Time {self.env.now}')
                yield self.env.timeout(link_delay)

                # Update flows current node
                flow.current_node_id = neighbor_id
                # Update metrics
                flow.path_delay += link_delay
                metrics.add_path_delay(link_delay)
                flow.end2end_delay += link_delay
                log.info(f'Flow {flow.flow_id} STARTED ARRIVING at node {neighbor_id} by forwarding. Time: {self.env.now}')
                self.env.process(self.pass_flow(flow, self.params.sfc_list[flow.sfc_id]))

                yield self.env.timeout(flow.duration)
                log.info(f'Flow {flow.flow_id} FINISHED ARRIVING at node {neighbor_id} by forwarding. Time: {self.env.now}')
                # Free link capacities
                forwarding_link['remaining_cap'] += flow.dr
                assert forwarding_link['remaining_cap'] <= forwarding_link['cap'],\
                    "Link remaining capacity cannot be more than link capacity!"
            else:
                log.warning(f'Not enough link capacity for flow {flow.flow_id} to forward over link ({flow.current_node_id}, {neighbor_id}). Dropping flow.')
                self.drop_flow(flow)
                self.env.exit()

    def process_flow(self, flow, sfc):
        """
        SimPy process.
        Processes the flow at the requested SF of the current node.

        The process interaction is visualized as:

              +--------------+          +-----------+
        ----->+ process_flow +--------->+ pass_flow +---->
              +--------------+          +-----------+
        """

        # Generate a processing delay for the SF
        current_sf = flow.current_sf
        current_node_id = flow.current_node_id
        vnf_delay_mean = self.params.sf_list[flow.current_sf]["processing_delay_mean"]
        vnf_delay_stdev = self.params.sf_list[flow.current_sf]["processing_delay_stdev"]
        processing_delay = np.absolute(np.random.normal(vnf_delay_mean, vnf_delay_stdev))

        # Calculate the demanded capacity when the flow is processed at this node
        demanded_total_capacity = 0.0
        for sf_i, sf_data in self.params.network.nodes[current_node_id]['available_sf'].items():
            if current_sf == sf_i:
                # Include flows data rate in requested sf capacity calculation
                demanded_total_capacity += self.params.sf_list[sf_i]['resource_function'](sf_data['load'] + flow.dr)
            else:
                demanded_total_capacity += self.params.sf_list[sf_i]['resource_function'](sf_data['load'])

        # Get node capacities
        node_cap = self.params.network.nodes[current_node_id]["cap"]
        node_remaining_cap = self.params.network.nodes[current_node_id]["remaining_cap"]
        assert node_remaining_cap >= 0, "Remaining node capacity cannot be less than 0 (zero)!"

        if demanded_total_capacity <= node_cap:
            log.info(f'Flow {flow.flow_id} started processing at sf {current_sf} at node {current_node_id}. Time: {self.env.now}, Processing delay: {processing_delay}')
            # Metrics: Add active flow to the SF once the flow has begun processing.
            metrics.add_active_flow(flow, current_node_id, current_sf)

            # Add load to sf
            self.params.network.nodes[current_node_id]['available_sf'][current_sf]['load'] += flow.dr
            # Set remaining node capacity
            self.params.network.nodes[current_node_id]['remaining_cap'] = node_cap - demanded_total_capacity
            # Just for the sake of keeping lines small, the node_remaining_cap is updated again.
            node_remaining_cap = self.params.network.nodes[current_node_id]["remaining_cap"]

            yield self.env.timeout(processing_delay)
            log.info(
                f'Flow {flow.flow_id} started departing sf {current_sf} at node {current_node_id}. Time {self.env.now}')
            # Increment the position of the flow within SFC
            flow.current_position += 1
            # Update metrics for the processing delay
            # Add the delay to the flow's end2end delay
            metrics.add_processing_delay(processing_delay)
            flow.end2end_delay += processing_delay
            # Create new pass_flow process
            self.env.process(self.pass_flow(flow, sfc))

            yield self.env.timeout(flow.duration)
            log.info(
                f'Flow {flow.flow_id} has departed SF {current_sf} at node {current_node_id} for processing. Time: {self.env.now}')

            # Remove the active flow from the SF after it departed the SF
            metrics.remove_active_flow(flow, current_node_id, current_sf)

            # Remove load from sf
            self.params.network.nodes[current_node_id]['available_sf'][current_sf]['load'] -= flow.dr
            assert self.params.network.nodes[current_node_id]['available_sf'][current_sf][
                       'load'] >= 0, 'SF load cannot be less than 0!'
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
            self.drop_flow(flow)
            self.env.exit()

    def depart_flow(self, flow):
        """
        SimPy process.
        Departs the flow from the network

        The process interaction is visualized as:

              +-------------+
        ----->+ depart_flow +
              +-------------+
        """

        log.info(f'Flow {flow.flow_id} was processed and starts departing the network from {flow.current_node_id}. Time {self.env.now}')
        yield self.env.timeout(flow.duration)
        log.info(f'Flow {flow.flow_id} has completely departed the network from {flow.current_node_id}. Time {self.env.now}')

        # Update metrics for the processed flow
        metrics.processed_flow()
        metrics.add_end2end_delay(flow.end2end_delay)
        metrics.add_path_delay_of_processed_flows(flow.path_delay)

        self.env.exit()

    def drop_flow(self, flow):
        """
        This function concentrates actions that need to be carried out when dropping a flow. At the moment
        there is no real advantage in this outsourcing, but future version might introduce more actions.
        """
        # Update metrics for the dropped flow
        metrics.dropped_flow()
