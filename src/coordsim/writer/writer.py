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
    def __init__(self, test_mode: bool, test_dir, write_schedule=False):
        """
        If the simulator is in test mode, create result folder and CSV files
        """
        self.write_schedule = write_schedule
        self.test_mode = test_mode
        if self.test_mode:
            if self.write_schedule:
                self.scheduling_file_name = f"{test_dir}/scheduling.csv"
            self.placement_file_name = f"{test_dir}/placements.csv"
            self.resources_file_name = f"{test_dir}/resources.csv"
            self.metrics_file_name = f"{test_dir}/metrics.csv"
            self.dropped_flows_file_name = f"{test_dir}/dropped_flows.yaml"
            self.rl_state_file_name = f"{test_dir}/rl_state.csv"
            self.run_flows_file_name = f"{test_dir}/run_flows.csv"

            # Create the results directory if not exists
            os.makedirs(os.path.dirname(self.placement_file_name), exist_ok=True)

            self.placement_stream = open(self.placement_file_name, 'a+', newline='')
            self.resources_stream = open(self.resources_file_name, 'a+', newline='')
            self.metrics_stream = open(self.metrics_file_name, 'a+', newline='')
            self.rl_state_stream = open(self.rl_state_file_name, 'a+', newline='')
            self.run_flows_stream = open(self.run_flows_file_name, 'a+', newline='')

            if self.write_schedule:
                self.scheduleing_stream = open(self.scheduling_file_name, 'a+', newline='')
                self.scheduling_writer = csv.writer(self.scheduleing_stream)
            # Create CSV writers
            self.placement_writer = csv.writer(self.placement_stream)
            self.resources_writer = csv.writer(self.resources_stream)
            self.metrics_writer = csv.writer(self.metrics_stream)
            self.rl_state_writer = csv.writer(self.rl_state_stream)
            self.run_flows_writer = csv.writer(self.run_flows_stream)

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
            self.run_flows_stream.close()

    def create_csv_headers(self):
        """
        Creates statistics CSV headers and writes them to their files
        """

        # Create CSV headers
        if self.write_schedule:
            scheduling_output_header = ['episode', 'time', 'origin_node', 'sfc', 'sf', 'schedule_node', 'schedule_prob']
            self.scheduling_writer.writerow(scheduling_output_header)
        placement_output_header = ['episode', 'time', 'node', 'sf']
        resources_output_header = ['episode', 'time', 'node', 'node_capacity', 'used_resources']
        metrics_output_header = ['episode', 'time', 'total_flows', 'successful_flows', 'dropped_flows',
                                 'in_network_flows', 'avg_end2end_delay']
        run_flows_output_header = ['episode', 'time', 'successful_flows', 'dropped_flows', 'total_flows']

        # Write headers to CSV files
        self.placement_writer.writerow(placement_output_header)
        self.resources_writer.writerow(resources_output_header)
        self.metrics_writer.writerow(metrics_output_header)
        self.run_flows_writer.writerow(run_flows_output_header)

    def write_action_result(self, episode, time, action: SimulatorAction):
        """
        Write simulator actions to CSV files for statistics purposes
        """
        if self.test_mode:
            placement = action.placement
            placement_output = []
            scheduling_output = []

            for node_id, sfs in placement.items():
                for sf in sfs:
                    placement_output_row = [episode, time, node_id, sf]
                    placement_output.append(placement_output_row)
            if self.write_schedule:
                scheduling = action.scheduling
                for node, sfcs in scheduling.items():
                    for sfc, sfs in sfcs.items():
                        for sf, scheduling in sfs.items():
                            for schedule_node, schedule_prob in scheduling.items():
                                scheduling_output_row = [episode, time, node, sfc, sf, schedule_node, schedule_prob]
                                scheduling_output.append(scheduling_output_row)
                self.scheduling_writer.writerows(scheduling_output)

            self.placement_writer.writerows(placement_output)

    def write_state_results(self, episode, time, state: SimulatorState, metrics):
        """
        Write node resource consumption to CSV file
        """
        if self.test_mode:
            network = state.network
            stats = state.network_stats

            metrics_output = [episode, time, stats['total_flows'], stats['successful_flows'], stats['dropped_flows'],
                              stats['in_network_flows'], stats['avg_end2end_delay']]

            resource_output = []
            for node in network['nodes']:
                node_id = node['id']
                node_cap = node['resource']
                used_resources = node['used_resources']
                resource_output_row = [episode, time, node_id, node_cap, used_resources]
                resource_output.append(resource_output_row)

            run_flows_output = [episode, time, metrics['run_processed_flows'], metrics['run_dropped_flows'], metrics['run_generated_flows']]
            self.run_flows_writer.writerow(run_flows_output)
            self.metrics_writer.writerow(metrics_output)
            self.resources_writer.writerows(resource_output)

    def write_dropped_flow_locs(self, dropped_flow_locs):
        """Dump dropped flow counters into yaml file. Called at end of simulation"""
        if self.test_mode:
            with open(self.dropped_flows_file_name, 'w') as f:
                yaml.dump(dropped_flow_locs, f, default_flow_style=False)

    def write_rl_state(self, rl_state):
        if self.test_mode:
            self.rl_state_writer.writerow(rl_state)
