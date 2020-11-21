import logging
from coordsim.flow_processors import BaseFlowProcessor
import numpy as np
log = logging.getLogger(__name__)


class DefaultFlowProcessor(BaseFlowProcessor):
    """
    This is the default processor class.
    """
    def __init__(self, env, params):
        super().__init__(env, params)

    def process_flow(self, flow) -> bool:
        """
        Process the flow at the requested SF of the current node.
        Returns: True if flow started processing
        """
        # Generate a processing delay for the SF
        current_node_id = flow.current_node_id
        sfc = self.params.sfc_list[flow.sfc]
        sf = sfc[flow.current_position]
        flow.current_sf = sf

        self.params.logger.info(
            "Flow {} STARTED PROCESSING at node {} for processing. Time: {}"
            .format(flow.flow_id, flow.current_node_id, self.env.now))

        if sf in self.params.sf_placement[current_node_id]:
            processing_delay = self.get_processing_delay(flow, sf)
            resources_available = yield self.env.process(self.request_resources(flow, current_node_id, sf))
            if resources_available:
                # Resources are available: wait processing_delay
                yield self.env.timeout(processing_delay)
                self.params.logger.info(
                    "Flow {} started departing sf {} at node {}. Time {}"
                    .format(flow.flow_id, sf, current_node_id, self.env.now))
                # Create a simpy process to cleanup used resources after flow duration passed
                self.env.process(self.finish_processing(flow, current_node_id, sf))
                return True
            else:
                return False

        else:
            self.params.logger.info(f"SF {sf} was not found at {current_node_id}. Dropping flow {flow.flow_id}")
            return False
