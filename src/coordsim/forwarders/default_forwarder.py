import logging
from coordsim.forwarders import BaseFlowForwarder
log = logging.getLogger(__name__)


class DefaultFlowForwarder(BaseFlowForwarder):
    """
    This is the default forwarder class. It takes the shortest path.
    """
    def __init__(self, env, params):
        """
        docstring
        """
        self.env = env
        self.params = params

    def forward_flow(self, flow, next_node):
        """
        Calculates the path delays occurring when forwarding a node
        Path delays are calculated using the Shortest path
        The delay is simulated by timing out for the delay amount of duration
        """
        if next_node is None:
            log.info(f"No node to forward flow {flow.flow_id} to. Dropping it")
            # Update metrics for the dropped flow
            self.params.metrics.dropped_flow(flow)
            return False

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
        return True
