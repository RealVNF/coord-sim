import logging
import numpy as np
from coordsim.network.flow import Flow
from coordsim.simulation.simulatorparams import SimulatorParams
from coordsim.decision_maker import BaseDecisionMaker
log = logging.getLogger(__name__)


class DefaultDecisionMaker(BaseDecisionMaker):
    """
    This is the default decision maker class. It makes flow decisions based on the scheduling table
    """

    def __init__(self, env, params):
        self.env = env
        self.params: SimulatorParams = params

    def decide_next_node(self, flow: Flow):
        """ Load balance the flows according to the scheduling tables """
        # If flow is to be forwarded to egress, always return egress node as "next node"
        if flow.forward_to_eg:
            return flow.egress_node_id
        sf = self.params.sfc_list[flow.sfc][flow.current_position]
        flow.current_sf = sf
        self.params.metrics.add_requesting_flow(flow)
        schedule = self.params.schedule
        # Check if scheduling rule exists
        if (flow.current_node_id in schedule) and flow.sfc in schedule[flow.current_node_id]:
            local_schedule = schedule[flow.current_node_id][flow.sfc][sf]
            dest_nodes = [sch_sf for sch_sf in local_schedule.keys()]
            dest_prob = [prob for name, prob in local_schedule.items()]
            try:
                # select next node based on weighted RR according to the scheduling weights/probabilities
                # get current flow counts per possible destination node
                flow_counts = self.params.metrics.metrics['run_flow_counts'][flow.current_node_id][flow.sfc][sf]
                flow_sum = sum(flow_counts.values())
                # calculate the current ratios of flows sent to the different destination nodes
                if flow_sum > 0:
                    dest_ratios = [flow_counts[v] / flow_sum for v in dest_nodes]
                else:
                    dest_ratios = [0 for v in dest_nodes]

                # calculate the difference from the scheduling weight
                # for nodes with 0 probability/weight, set the diff to be negative so they are not selected
                # otherwise all diffs may be 0 if ratio = probability and a node with probability 0 could be selected
                assert len(dest_nodes) == len(dest_prob) == len(dest_ratios)
                ratio_diffs = [dest_prob[i] - dest_ratios[i] if dest_prob[i] > 0
                               else -1 for i in range(len(dest_nodes))]

                # select the node that farthest away from its weight, ie, has the highest diff
                max_idx = np.argmax(ratio_diffs)
                next_node = dest_nodes[max_idx]

                # increase counter for selected node
                self.params.metrics.metrics['run_flow_counts'][flow.current_node_id][flow.sfc][sf][next_node] += 1

                return next_node

            except Exception as ex:

                # Scheduling rule does not exist: drop flow
                log.warning(f'Flow {flow.flow_id}: Scheduling rule at node {flow.current_node_id} not correct'
                            f'Dropping flow!')
                log.warning(ex)
                self.params.metrics.dropped_flow(flow)
                return None
        else:
            # Scheduling rule does not exist: drop flow
            log.warning(f'Flow {flow.flow_id}: Scheduling rule not found at {flow.current_node_id}. Dropping flow!')
            self.params.metrics.dropped_flow(flow)
            return None
