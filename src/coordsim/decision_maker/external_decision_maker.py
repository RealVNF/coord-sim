import logging
import numpy as np
import random
import simpy
from coordsim.network.flow import Flow
from coordsim.simulation.simulatorparams import SimulatorParams
from coordsim.decision_maker import BaseDecisionMaker


class ExternalDecisionMaker(BaseDecisionMaker):
    """
    This is the default decision maker class. It makes flow decisions based on the scheduling table
    """

    def __init__(self, env, params):
        super().__init__(env, params)
        # TODO: Implement this properly using Enums or sth similar
        self.decision_type = "PerFlow"

    def decide_next_node(self, flow: Flow):
        """
        Check for conflicting events to schedule per-flow decisions from external algorithms
        If conflicting event exists, yield a backoff time before triggering the event
        Return `External` to indicate that a decision from an external algorithm is required for the flow
        """
        if flow.ttl <= 0:
            self.params.metrics.dropped_flow(flow)
            return None

        events_list = self.env._queue
        events_now = [event for event in events_list if event[0] == self.env.now]
        for event in events_now:
            event_object = event[-1]
            if isinstance(event_object, simpy.events.Event) and event_object.value is not None:
                # There is a scheduling conflict, wait a backoff time (between 0 and 1) and restart
                backoff_time = random.random() / 10
                yield self.env.timeout(backoff_time)
        # Trigger the event to register in Simpy
        self.params.flow_trigger.succeed(value=flow)
        # Reset it immediately
        self.params.flow_trigger = self.env.event()
        # Check flow TTL and drop if zero or less
        return "External"
