"""
Simulator file writer module
"""

import csv
import os
import datetime as dt
from spinterface import SimulatorAction, SimulatorState


def create_csv_streams():
    """
    Creates statistics CSV files in append mode. Returns opened streams
    """
    now = dt.datetime.now()

    scheduling_file_name = f"results/scheduling-{now.strftime('%d-%m-%Y--%H-%M-%S')}.csv"
    placement_file_name = f"results/placements-{now.strftime('%d-%m-%Y--%H-%M-%S')}.csv"
    resources_file_name = f"results/resources-{now.strftime('%d-%m-%Y--%H-%M-%S')}.csv"

    # Create the results directory if not exists
    os.makedirs(os.path.dirname(placement_file_name), exist_ok=True)

    placement_stream = open(placement_file_name, 'a+')
    scheduleing_stream = open(scheduling_file_name, 'a+')
    resources_stream = open(resources_file_name, 'a+')

    # Create CSV headers
    scheduling_output_header = ['time', 'origin_node', 'sfc', 'sf', 'schedule_node', 'schedule_prob']
    placement_output_header = ['time', 'node', 'sf']
    resources_output_header = ['time', 'node', 'node_capacity', 'used_resources']

    # Create CSV writers
    placement_writer = csv.writer(placement_stream)
    scheduling_writer = csv.writer(scheduleing_stream)
    resources_writer = csv.writer(resources_stream)

    # Write headers to CSV files
    placement_writer.writerow(placement_output_header)
    scheduling_writer.writerow(scheduling_output_header)
    resources_writer.writerow(resources_output_header)

    return placement_stream, scheduleing_stream, resources_stream


def write_placement_result(stream, env, action: SimulatorAction):
    """
    Write simulator placement action to a CSV file for statistics purposes
    """
    placement = action.placement
    time = env.now
    writer = csv.writer(stream)
    output = []
    for node_id, sfs in placement.items():
        for sf in sfs:
            output_row = [time, node_id, sf]
            output.append(output_row)
    writer.writerows(output)


def write_scheduling_results(stream, env, action: SimulatorAction):
    """
    Write scheduling rules to a CSV file
    """
    scheduling = action.scheduling
    time = env.now
    writer = csv.writer(stream)
    output = []
    for node, sfcs in scheduling.items():
        for sfc, sfs in sfcs.items():
            for sf, scheduling in sfs.items():
                for schedule_node, schedule_prob in scheduling.items():
                    output_row = [time, node, sfc, sf, schedule_node, schedule_prob]
                    output.append(output_row)
    writer.writerows(output)


def write_resource_results(stream, env, state: SimulatorState):
    """
    Write node resource consumption to CSV file
    """
    network = state.network
    time = env.now
    writer = csv.writer(stream)
    output = []
    for node in network['nodes']:
        node_id = node['id']
        node_cap = node['resource']
        used_resources = node['used_resources']
        output_row = [time, node_id, node_cap, used_resources]
        output.append(output_row)
    writer.writerows(output)
