import logging
import numpy as np
from coordsim.network.flow import Flow
from coordsim.forwarders import *
from coordsim.flow_generators import *
from coordsim.flow_processors import *
from coordsim.decision_maker import *
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
        self.params.flow_trigger = self.env.event()
        flow_generator_cls = eval(self.params.flow_generator_class)
        self.FlowGenerator = flow_generator_cls(self.env, self.params)
        assert isinstance(self.FlowGenerator, BaseFlowGenerator)
        decision_maker_cls = eval(self.params.decision_maker_class)
        self.DecisionMaker = decision_maker_cls(self.env, self.params)
        assert isinstance(self.DecisionMaker, BaseDecisionMaker)
        flow_forwarder_cls = eval(self.params.flow_forwarder_class)
        self.FlowForwarder = flow_forwarder_cls(self.env, self.params)
        assert isinstance(self.FlowForwarder, BaseFlowForwarder)
        flow_processor_cls = eval(self.params.flow_processor_class)
        self.FlowProcessor = flow_processor_cls(self.env, self.params)
        assert isinstance(self.FlowProcessor, BaseFlowProcessor)

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
            self.env.process(self.init_arrival(node_id))

    def init_arrival(self, node_id):
        """
        Initiates and controls flow arrivals at a node
        """
        while self.params.inter_arr_mean[node_id] is not None:
            self.total_flow_count += 1

            inter_arr_time, flow = self.FlowGenerator.generate_flow(self.total_flow_count, node_id)

            # Generate flows and schedule them at ingress node
            self.env.process(self.handle_flow(flow))
            yield self.env.timeout(inter_arr_time)

    def handle_flow(self, flow: Flow, decision=False):
        """
        Handles the flow operations
        """
        self.params.logger.info(
            "Flow {} generated. arrived at node {} Requesting {} - flow duration: {}ms, "
            "flow dr: {}. Time: {}".format(flow.flow_id, flow.current_node_id, flow.sfc, flow.duration, flow.dr,
                                           self.env.now))
        while not flow.departed:
            if decision is False:
                next_node = yield self.env.process(self.DecisionMaker.decide_next_node(flow))
                if next_node == "External":
                    # If decision maker asked for external decisions from the algo directly
                    # Then exit this simpy process. The runner module will be responsible to call
                    # `handle_flow` again with a decision.
                    return
            else:
                next_node = decision
                # Reset decision
                decision = False
                # TODO: Check if following is needed
                if flow.forward_to_eg and flow.current_node_id == next_node:
                    # If flow finished processing and decision is to keep at the same node: +1 delay
                    yield self.env.timeout(1)
                    flow.ttl -= 1
                    flow.end2end_delay += 1
            if next_node is not None:
                # TODO: Record decision for every flow here. Add to CSV file
                decision_type = self.DecisionMaker.decision_type
                if (decision_type != "PerFlow") or (decision_type == "PerFlow" and next_node == flow.current_node_id):
                    process = True
                else:
                    process = False

                flow_forwarded = yield self.env.process(self.FlowForwarder.forward_flow(flow, next_node))
                if not flow_forwarded:
                    # Flow was dropped: end simpy process
                    # Update metrics for the dropped flow
                    self.params.metrics.dropped_flow(flow, "LINK_CAP")
                    return
                if not flow.forward_to_eg:
                    self.params.logger.info(
                        "Flow {} STARTED ARRIVING at node {} for processing. Time: {}"
                        .format(flow.flow_id, flow.current_node_id, self.env.now))
                    if process:
                        flow_processed = yield self.env.process(self.FlowProcessor.process_flow(flow))
                        if not flow_processed:
                            # Flow was dropped: end simpy process
                            # Update metrics for the dropped flow
                            self.params.metrics.dropped_flow(flow, "NODE_CAP")
                            return
            else:
                # No next node: dropped flow
                self.params.metrics.dropped_flow(flow, "DECISION")
                return
        if flow.departed:
            self.depart_flow(flow)

    def depart_flow(self, flow):
        """
        Process the flow at the requested SF of the current node.
        """
        # Update metrics for the processed flow
        self.params.metrics.completed_flow()
        self.params.metrics.add_end2end_delay(flow.end2end_delay)
        self.params.logger.info(
            "Flow {} was processed and departed the network from {}. Time {}"
            .format(flow.flow_id, flow.current_node_id, self.env.now))
