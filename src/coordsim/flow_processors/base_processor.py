from simpy import Environment
import numpy as np
import logging
from coordsim.network.flow import Flow
from coordsim.simulation.simulatorparams import SimulatorParams
log = logging.getLogger(__name__)


class BaseFlowProcessor:
    """ Base Flow Processor class
    All flow processor classes must inherit this class
    """
    def __init__(self, env: Environment, params: SimulatorParams):
        self.env = env
        self.params = params

    def process_flow(self, flow: Flow) -> bool:
        """ Process the flow at its requested SF if resources are available
        Returns:
            - bool: the status of the flow whether it was processed or not
        """
        raise NotImplementedError

    def get_demanded_cap(self, dr: int, node_id: str, sf: str) -> float:
        # Calculate the demanded capacity when the flow is processed at a node
        demanded_total_capacity = 0.0
        for sf_i, sf_data in self.params.network.nodes[node_id]['available_sf'].items():
            if not sf_i == "EG":
                if sf == sf_i:
                    # Include flows data rate in requested sf capacity calculation
                    demanded_total_capacity += self.params.sf_list[sf]['resource_function'](sf_data['load'] + dr)
                else:
                    demanded_total_capacity += self.params.sf_list[sf_i]['resource_function'](sf_data['load'])

        return demanded_total_capacity

    def get_processing_delay(self, flow: Flow, sf: str) -> float:
        """ Generate a random processing delay based on mean and stdev from sf file """
        vnf_delay_mean = self.params.sf_list[sf]["processing_delay_mean"]
        vnf_delay_stdev = self.params.sf_list[sf]["processing_delay_stdev"]
        processing_delay = np.absolute(np.random.normal(vnf_delay_mean, vnf_delay_stdev))
        self.params.metrics.add_processing_delay(processing_delay)
        flow.end2end_delay += processing_delay
        flow.ttl -= processing_delay

        return processing_delay

    def request_resources(self, flow: Flow, node_id: str, sf: str) -> bool:
        """ Request resources from the node
        Returns True if resources were successfully given to the flow
        """
        # Calculate the demanded capacity when the flow is processed at this node
        demanded_total_capacity = self.get_demanded_cap(flow.dr, node_id, sf)
        # Get node capacities
        node_cap = self.params.network.nodes[node_id]["cap"]
        node_remaining_cap = self.params.network.nodes[node_id]["remaining_cap"]
        assert node_remaining_cap >= 0, "Remaining node capacity cannot be less than 0 (zero)!"
        if demanded_total_capacity <= node_cap:
            self.params.logger.info(
                "Flow {} started processing at sf {} at node {}. Time: {}"
                .format(flow.flow_id, sf, node_id, self.env.now))

            # Update processing level of flow
            flow.processing_index += 1

            # Metrics: Add active flow to the SF once the flow has begun processing.
            self.params.metrics.add_active_flow(flow, node_id, sf)

            # Add load to sf
            self.params.network.nodes[node_id]['available_sf'][sf]['load'] += flow.dr
            # Set remaining node capacity
            self.params.network.nodes[node_id]['remaining_cap'] = node_cap - demanded_total_capacity
            # Set max node usage
            self.params.metrics.calc_max_node_usage(node_id, demanded_total_capacity)
            # Just for the sake of keeping lines small, the node_remaining_cap is updated again.
            node_remaining_cap = self.params.network.nodes[node_id]["remaining_cap"]

            # Check if startup is done
            startup_time = self.params.network.nodes[node_id]['available_sf'][sf]['startup_time']
            startup_delay = self.params.sf_list[sf]["startup_delay"]
            startup_done = True if (startup_time + startup_delay) <= self.env.now else False

            if not startup_done:
                # Startup is not done: wait the remaining startup time
                startup_time_remaining = (startup_time + startup_delay) - self.env.now
                flow.end2end_delay += startup_time_remaining
                flow.ttl -= startup_time_remaining
                yield self.env.timeout(startup_time_remaining)

            return True
        else:
            self.params.logger.info(
                f"Not enough capacity for flow {flow.flow_id} at node {flow.current_node_id}. Dropping flow.")
            return False

    def finish_processing(self, flow: Flow, node_id: str, sf: str) -> bool:
        """ Simpy process to cleanup used resources after a flow has finished processing """
        flow.current_position += 1
        if flow.current_position == len(self.params.sfc_list[flow.sfc]):
            flow.forward_to_eg = True
        # Wait flow duration for flow to fully process
        yield self.env.timeout(flow.duration)
        # Remove the active flow from the node
        self.params.metrics.remove_active_flow(flow, node_id, sf)
        # Remove flow's load from sf
        self.params.network.nodes[node_id]['available_sf'][sf]['load'] -= flow.dr
        assert self.params.network.nodes[node_id]['available_sf'][sf]['load'] >= 0, \
            'SF load cannot be less than 0!'

        # Remove SF gracefully from node if no load exists and SF removed from placement
        if (self.params.network.nodes[node_id]['available_sf'][sf]['load'] == 0) and (
                sf not in self.params.sf_placement[node_id]):
            del self.params.network.nodes[node_id]['available_sf'][sf]

        # Recalculate used node cap before updating node rem. cap because of how simpy schedules processes
        node_cap = self.params.network.nodes[node_id]["cap"]
        used_total_capacity = 0.0
        for sf_i, sf_data in self.params.network.nodes[node_id]['available_sf'].items():
            if not sf_i == "EG":
                used_total_capacity += self.params.sf_list[sf_i]['resource_function'](sf_data['load'])
        # Set remaining node capacity
        self.params.network.nodes[node_id]['remaining_cap'] = node_cap - used_total_capacity

        node_remaining_cap = self.params.network.nodes[node_id]["remaining_cap"]

        # We assert that remaining capacity must at all times be less than the node capacity so that
        # nodes dont put back more capacity than the node's capacity.
        assert node_remaining_cap <= node_cap, "Node remaining capacity cannot be more than node capacity!"
