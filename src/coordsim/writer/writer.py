"""
Simulator file writer module
"""

import csv
import os
import yaml
from spinterface import SimulatorAction, SimulatorState


class ResultWriter():
    """
    Result Writer
    Helper class to write results to CSV files.
    """
    def __init__(self, test_mode: bool, test_dir, write_schedule=False, write_flow_actions=False):
        """
        If the simulator is in test mode, create result folder and CSV files
        """
        self.write_schedule = write_schedule
        self.write_per_flow_actions = write_flow_actions
        self.test_mode = test_mode
        if self.test_mode:
            if self.write_schedule:
                self.scheduling_file_name = f"{test_dir}/scheduling.csv"
            self.placement_file_name = f"{test_dir}/placements.csv"
            self.resources_file_name = f"{test_dir}/node_metrics.csv"
            self.metrics_file_name = f"{test_dir}/metrics.csv"
            self.drop_reasons_file_name = f"{test_dir}/drop_reasons.csv"
            self.dropped_flows_file_name = f"{test_dir}/dropped_flows.yaml"
            self.rl_state_file_name = f"{test_dir}/rl_state.csv"
            self.run_flows_file_name = f"{test_dir}/run_flows.csv"
            self.runtimes_file_name = f"{test_dir}/runtimes.csv"
            self.flow_action_file_name = f"{test_dir}/flow_actions.csv"

            # Create the results directory if not exists
            os.makedirs(os.path.dirname(self.placement_file_name), exist_ok=True)

            self.placement_stream = open(self.placement_file_name, 'a+', newline='')
            self.resources_stream = open(self.resources_file_name, 'a+', newline='')
            self.metrics_stream = open(self.metrics_file_name, 'a+', newline='')
            self.rl_state_stream = open(self.rl_state_file_name, 'a+', newline='')
            self.run_flows_stream = open(self.run_flows_file_name, 'a+', newline='')
            self.runtimes_stream = open(self.runtimes_file_name, 'a+', newline='')
            self.drop_reasons_stream = open(self.drop_reasons_file_name, 'a+', newline='')

            if self.write_schedule:
                self.scheduleing_stream = open(self.scheduling_file_name, 'a+', newline='')
                self.scheduling_writer = csv.writer(self.scheduleing_stream)
            if self.write_per_flow_actions:
                self.flow_action_stream = open(self.flow_action_file_name, 'a+', newline='')
                self.flow_action_writer = csv.writer(self.flow_action_stream)
            # Create CSV writers
            self.placement_writer = csv.writer(self.placement_stream)
            self.resources_writer = csv.writer(self.resources_stream)
            self.metrics_writer = csv.writer(self.metrics_stream)
            self.rl_state_writer = csv.writer(self.rl_state_stream)
            self.run_flows_writer = csv.writer(self.run_flows_stream)
            self.runtimes_writer = csv.writer(self.runtimes_stream)
            self.drop_reasons_writer = csv.writer(self.drop_reasons_stream)
            self.action_number = 0

            # Write the headers to the files
            self.create_csv_headers()

    def __del__(self):
        # Close all writer streams
        if self.test_mode:
            self.placement_stream.close()
            if self.write_schedule:
                self.scheduleing_stream.close()
            self.resources_stream.close()
            self.metrics_stream.close()
            self.rl_state_stream.close()
            if self.write_per_flow_actions:
                self.flow_action_stream.close()
            self.run_flows_stream.close()
            self.runtimes_stream.close()
            self.drop_reasons_stream.close()

    def create_csv_headers(self):
        """
        Creates statistics CSV headers and writes them to their files
        """

        # Create CSV headers
        if self.write_schedule:
            scheduling_output_header = ['episode', 'time', 'origin_node', 'sfc', 'sf', 'schedule_node', 'schedule_prob']
            self.scheduling_writer.writerow(scheduling_output_header)
        placement_output_header = ['episode', 'time', 'node', 'sf']
        resources_output_header = ['episode', 'time', 'node', 'node_capacity', 'used_resources', 'ingress_traffic']
        metrics_output_header = ['episode', 'time', 'total_flows', 'successful_flows', 'dropped_flows',
                                 'in_network_flows', 'avg_end2end_delay']
        run_flows_output_header = ['episode', 'time', 'successful_flows', 'dropped_flows', 'total_flows']
        runtimes_output_header = ['run', 'runtime']
        if self.write_per_flow_actions:
            flow_action_output_header = ['episode', 'time', 'flow_id', 'flow_rem_ttl', 'flow_ttl',
                                         'curr_node_id', 'dest_node', 'cur_node_rem_cap', 'next_node_rem_cap',
                                         'link_cap', 'link_rem_cap']
            self.flow_action_writer.writerow(flow_action_output_header)
        drop_reasons_output_header = ['episode', 'time', 'TTL', 'DECISION', 'LINK_CAP', 'NODE_CAP']

        # Write headers to CSV files
        self.placement_writer.writerow(placement_output_header)
        self.resources_writer.writerow(resources_output_header)
        self.metrics_writer.writerow(metrics_output_header)
        self.run_flows_writer.writerow(run_flows_output_header)
        self.runtimes_writer.writerow(runtimes_output_header)
        self.drop_reasons_writer.writerow(drop_reasons_output_header)

    def write_runtime(self, time):
        """
        Write runtime results to output file
        """
        if self.test_mode:
            self.action_number += 1
            self.runtimes_writer.writerow([self.action_number, time])

    def write_flow_action(self, params, time, flow, current_node_id, destination_node_id):
        if self.test_mode and self.write_per_flow_actions:
            cur_node_rem_cap = params.network.nodes[flow.current_node_id]['remaining_cap']
            if destination_node_id is None:
                dest_node = 'None'
                next_node_rem_cap = -1
                # link_cap = -1
                # rem_cap = -1
            else:
                dest_node = destination_node_id
                next_node_rem_cap = params.network.nodes[dest_node]['remaining_cap']
                if dest_node == flow.current_node_id:
                    link_cap = 'inf'
                    rem_cap = 'inf'
                else:
                    link_cap = params.network.edges[(flow.current_node_id, dest_node)]['cap']
                    rem_cap = params.network.edges[(flow.current_node_id, dest_node)]['remaining_cap']

            flow_action_output = [params.episode, time, flow.flow_id, flow.ttl, flow.original_ttl,
                                  flow.current_node_id, dest_node, cur_node_rem_cap, next_node_rem_cap,
                                  link_cap, rem_cap]
            self.flow_action_writer.writerow(flow_action_output)

    def write_schedule_table(self, params, time, action: SimulatorAction):
        """
        Write schedule to CSV files for statistics purposes
        """
        episode = self.params.episode
        if self.test_mode:
            scheduling_output = []

            if self.write_schedule:
                scheduling = action.scheduling
                for node, sfcs in scheduling.items():
                    for sfc, sfs in sfcs.items():
                        for sf, scheduling in sfs.items():
                            for schedule_node, schedule_prob in scheduling.items():
                                scheduling_output_row = [episode, time, node, sfc, sf, schedule_node, schedule_prob]
                                scheduling_output.append(scheduling_output_row)
                self.scheduling_writer.writerows(scheduling_output)

    def begin_writing(self, env, params):
        """
        Write node resource consumption to CSV file
        """
        self.env = env
        self.params = params
        yield self.env.process(self.write_network_state())

    def write_network_state(self):
        # TODO: Reset run metrics here, rather than in the decision maker
        time = self.env.now
        if self.test_mode:

            metrics = self.params.metrics.get_metrics()
            network = self.params.network

            metrics_output = [self.params.episode, time, metrics['generated_flows'], metrics['processed_flows'],
                              metrics['dropped_flows'], metrics['total_active_flows'], metrics['avg_end2end_delay']]

            resource_output = []
            for node in network.nodes(data=True):
                node_id = node[0]
                node_cap = node[1]['cap']
                used_resources = metrics['run_max_node_usage'][node_id]
                ingress_traffic = 0
                # get all sfc
                sfcs = list(self.params.sfc_list.keys())
                # iterate over sfcs to get traffic from all sfcs
                for sfc in sfcs:
                    ingress_sf = self.params.sfc_list[sfc][0]
                    ingress_traffic += metrics['run_act_total_requested_traffic'].get(
                        node_id, {}).get(
                            sfc, {}).get(
                                ingress_sf, 0)
                resource_output_row = [self.params.episode, time, node_id, node_cap, used_resources, ingress_traffic]
                resource_output.append(resource_output_row)

            run_flows_output = [self.params.episode, time, metrics['run_processed_flows'], metrics['run_dropped_flows'],
                                metrics['run_generated_flows']]

            drop_reasons = metrics['dropped_flow_reasons']
            drop_reasons_output = [
                self.params.episode, time, drop_reasons['TTL'], drop_reasons['DECISION'], drop_reasons['LINK_CAP'],
                drop_reasons['NODE_CAP']
            ]

            self.drop_reasons_writer.writerow(drop_reasons_output)
            self.run_flows_writer.writerow(run_flows_output)
            self.metrics_writer.writerow(metrics_output)
            self.resources_writer.writerows(resource_output)

            # Writing placement
            placement_output = []
            for node in network.nodes(data=True):
                node_id = node[0]
                sfs = list(node[1]['available_sf'].keys())
                for sf in sfs:
                    placement_output_row = [self.params.episode, time, node_id, sf]
                    placement_output.append(placement_output_row)
            self.placement_writer.writerows(placement_output)

        # Wait a timeout then write the states
        yield self.env.timeout(self.params.run_duration)
        yield self.env.process(self.write_network_state())

    def write_dropped_flow_locs(self, dropped_flow_locs):
        """Dump dropped flow counters into yaml file. Called at end of simulation"""
        if self.test_mode:
            with open(self.dropped_flows_file_name, 'w') as f:
                yaml.dump(dropped_flow_locs, f, default_flow_style=False)

    def write_rl_state(self, rl_state):
        if self.test_mode:
            self.rl_state_writer.writerow(rl_state)
