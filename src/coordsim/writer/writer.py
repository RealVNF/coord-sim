"""
Simulator file writer module
"""

import csv
import os
import datetime as dt
from spinterface import SimulatorAction, SimulatorState


class ResultWriter():
    """
    Result Writer module
    """
    def __init__(self, test_mode: bool):
        """
        If the simulator is in test mode, create result folder and CSV files
        """
        self.test_mode = test_mode
        if self.test_mode:
            now = dt.datetime.now()

            self.scheduling_file_name = f"results/scheduling-{now.strftime('%d-%m-%Y--%H-%M-%S')}.csv"
            self.placement_file_name = f"results/placements-{now.strftime('%d-%m-%Y--%H-%M-%S')}.csv"
            self.resources_file_name = f"results/resources-{now.strftime('%d-%m-%Y--%H-%M-%S')}.csv"
            self.metrics_file_name = f"results/metrics-{now.strftime('%d-%m-%Y--%H-%M-%S')}.csv"

            # Create the results directory if not exists
            os.makedirs(os.path.dirname(self.placement_file_name), exist_ok=True)

            self.placement_stream = open(self.placement_file_name, 'a+')
            self.scheduleing_stream = open(self.scheduling_file_name, 'a+')
            self.resources_stream = open(self.resources_file_name, 'a+')
            self.metrics_stream = open(self.metrics_file_name, 'a+')

            # Create CSV writers
            self.placement_writer = csv.writer(self.placement_stream)
            self.scheduling_writer = csv.writer(self.scheduleing_stream)
            self.resources_writer = csv.writer(self.resources_stream)
            self.metrics_writer = csv.writer(self.metrics_stream)

            # Write the headers to the files
            self.create_csv_headers()

    def create_csv_headers(self):
        """
        Creates statistics CSV headers and writes them to their files
        """

        # Create CSV headers
        scheduling_output_header = ['time', 'origin_node', 'sfc', 'sf', 'schedule_node', 'schedule_prob']
        placement_output_header = ['time', 'node', 'sf']
        resources_output_header = ['time', 'node', 'node_capacity', 'used_resources']
        metrics_output_header = ['time', 'total_flows', 'successful_flows', 'dropped_flows', 'in_network_flows',
                                 'avg_end_2_end_delay']

        # Write headers to CSV files
        self.placement_writer.writerow(placement_output_header)
        self.scheduling_writer.writerow(scheduling_output_header)
        self.resources_writer.writerow(resources_output_header)
        self.metrics_writer.writerow(metrics_output_header)

    def write_action_result(self, env, action: SimulatorAction):
        """
        Write simulator actions to CSV files for statistics purposes
        """
        if self.test_mode:
            placement = action.placement
            scheduling = action.scheduling
            time = env.now
            placement_output = []
            scheduling_output = []

            for node_id, sfs in placement.items():
                for sf in sfs:
                    placement_output_row = [time, node_id, sf]
                    placement_output.append(placement_output_row)

            for node, sfcs in scheduling.items():
                for sfc, sfs in sfcs.items():
                    for sf, scheduling in sfs.items():
                        for schedule_node, schedule_prob in scheduling.items():
                            scheduling_output_row = [time, node, sfc, sf, schedule_node, schedule_prob]
                            scheduling_output.append(scheduling_output_row)

            self.placement_writer.writerows(placement_output)
            self.scheduling_writer.writerows(scheduling_output)

    def write_state_results(self, env, state: SimulatorState):
        """
        Write node resource consumption to CSV file
        """
        if self.test_mode:
            network = state.network
            stats = state.network_stats
            time = env.now

            metrics_output = [time, stats['total_flows'], stats['successful_flows'], stats['dropped_flows'],
                              stats['in_network_flows'], stats['avg_end_2_end_delay']]

            resource_output = []
            for node in network['nodes']:
                node_id = node['id']
                node_cap = node['resource']
                used_resources = node['used_resources']
                resource_output_row = [time, node_id, node_cap, used_resources]
                resource_output.append(resource_output_row)

            self.metrics_writer.writerow(metrics_output)
            self.resources_writer.writerows(resource_output)

    def close_streams(self):
        """
        Close open streams
        """
        if self.test_mode:
            self.placement_stream.close()
            self.scheduleing_stream.close()
            self.resources_stream.close()
            self.metrics_stream.close()

    def __del__(self):
        # Close all writer streams
        self.close_streams()
