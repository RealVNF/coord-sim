import logging
from coordsim.forwarders import BaseFlowForwarder
# log = logging.getLogger(__name__)


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
            self.params.logger.info(f"No node to forward flow {flow.flow_id} to. Dropping it")
            return False

        path_delay = 0
        if flow.current_node_id != next_node:
            path_delay = self.params.network.graph['shortest_paths'][(flow.current_node_id, next_node)][1]

        # Check if path delay is longer than flow's remaining TTL
        if flow.ttl - path_delay <= 0:
            # Path delay longer than TTL, drop flow
            flow.ttl = 0
            return False

        # TODO: Put this in a better place. Maybe in the perflow controller. For later
        if flow.current_node_id == flow.egress_node_id and flow.forward_to_eg:
            # TODO: Make sure this is correct
            flow.departed = True
            flow.success = True
        # Metrics calculation for path delay. Flow's end2end delay is also incremented.
        if flow.current_node_id == next_node:
            # Write action even if flow stays
            if self.params.writer is not None:
                self.params.writer.write_flow_action(self.params, self.env.now, flow, flow.current_node_id, next_node)
            assert path_delay == 0, "While Forwarding the flow, the Current and Next node same, yet path_delay != 0"
            self.params.logger.info(
                "Flow {} will stay in node {}. Time: {}.".format(flow.flow_id, flow.current_node_id, self.env.now))
        else:
            self.params.logger.info(
                "Flow {} will leave node {} towards node {}. Time {}"
                .format(flow.flow_id, flow.current_node_id, next_node, self.env.now))
            path_to_next_node = self.params.network.graph['shortest_paths'][(flow.current_node_id, next_node)][0]
            # Get the path starting from next node
            for next_hop in path_to_next_node[1:]:
                # Write flow action for every hop
                if self.params.writer is not None:
                    self.params.writer.write_flow_action(self.params, self.env.now, flow, flow.current_node_id,
                                                         next_hop)
                # Get edges resources
                deduct_resources = self.deduct_link_resources(flow, flow.current_node_id, next_hop)
                if not deduct_resources:
                    # Not enough resources, flow dropped
                    return False
                hop_delay = self.params.network.graph['shortest_paths'][(flow.current_node_id, next_hop)][1]
                if next_hop == flow.egress_node_id and flow.forward_to_eg:
                    # TODO: Make sure this is correct
                    # Flow destiny must be known before any simpy timeouts occur. Necessary for SPR
                    flow.departed = True
                    flow.success = True
                yield self.env.timeout(hop_delay)
                self.env.process(self.return_link_resources(flow, flow.current_node_id, next_hop))
                flow.current_node_id = next_hop

            # Only add the full delay if flow passed the link fully
            self.params.metrics.add_path_delay(path_delay)
            flow.end2end_delay += path_delay
            flow.ttl -= path_delay

        # Return true only after all hops have been traverssed successfully
        return True

    def deduct_link_resources(self, flow, source_node_id, dest_node_id):
        """
        Deduct the flow's dr from the link resources
        """
        # Get edges resources
        edge_rem_cap = self.params.network.edges[(flow.current_node_id, dest_node_id)]['remaining_cap']
        # calculate new remaining cap
        new_rem_cap = edge_rem_cap - flow.dr
        if new_rem_cap >= 0:
            # There is enoough capacity on the edge: send the flow
            self.params.logger.info(
                f"Flow {flow.flow_id} started travelling on edge ({flow.current_node_id}, {dest_node_id})")
            self.params.network.edges[(flow.current_node_id, dest_node_id)]['remaining_cap'] -= flow.dr
            return True
        else:
            # Not enough capacity on the edge: drop the flow
            self.params.logger.info(f"No cap on edge ({flow.current_node_id}, {dest_node_id}) to handle {flow.flow_id}.\
            Dropping it")
            return False

    def return_link_resources(self, flow, source_node_id, dest_node_id):
        """
        Simpy process: wait flow.duration then cleanup link
        Used only when flow is forwarding to egress node and no flow processing done
        """
        # Wait flow duration
        yield self.env.timeout(flow.duration)

        # return the used capacity to the edge
        # Add the used cap back to the edge
        self.params.network.edges[(source_node_id, dest_node_id)]['remaining_cap'] += flow.dr
        remaining_edge_cap = self.params.network.edges[(source_node_id, dest_node_id)]['remaining_cap']
        edge_cap = self.params.network.edges[(source_node_id, dest_node_id)]['cap']
        assert remaining_edge_cap <= edge_cap, "Edge rem. cap can't be > actual cap"
