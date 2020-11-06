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

    def handle_flow(self, flow: Flow):
        """
        Handles the flow operations
        """
        log.info(
            "Flow {} generated. arrived at node {} Requesting {} - flow duration: {}ms, "
            "flow dr: {}. Time: {}".format(flow.flow_id, flow.current_node_id, flow.sfc, flow.duration, flow.dr,
                                           self.env.now))
        while not flow.departed:
            next_node = self.DecisionMaker.decide_next_node(flow)
            if next_node is not None:
                flow_forwarded = yield self.FlowForwarder.forward_flow(flow, next_node)
                if not flow_forwarded:
                    # Flow was dropped: terminate loop
                    break
                if not flow.forward_to_eg:
                    log.info("Flow {} STARTED ARRIVING at node {} for processing. Time: {}"
                             .format(flow.flow_id, flow.current_node_id, self.env.now))
                    flow_processed = yield self.env.process(self.FlowProcessor.process_flow(flow))
                    if not flow_processed:
                        # Flow was dropped: terminate loop
                        break
            else:
                # No next node: terminate loop
                break

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
