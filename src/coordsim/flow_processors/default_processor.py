import logging
from coordsim.flow_processors import BaseFlowProcessor
import numpy as np
log = logging.getLogger(__name__)


class DefaultFlowProcessor(BaseFlowProcessor):
    """
    This is the default processor class.
    """
    def __init__(self, env, params):
        self.env = env
        self.params = params

    def process_flow(self, flow):
        """
        Process the flow at the requested SF of the current node.
        """
        # Generate a processing delay for the SF
        current_node_id = flow.current_node_id
        sfc = self.params.sfc_list[flow.sfc]
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
                        flow.forward_to_eg = True
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
                return False
        else:
            log.info(f"SF {sf} was not found at {current_node_id}. Dropping flow {flow.flow_id}")
            self.params.metrics.dropped_flow(flow)
            return False
