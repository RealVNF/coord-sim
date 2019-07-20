""" 
Simulator file writer module
"""

import csv
import datetime as dt
from spinterface import SimulatorAction

def create_csv_stream():
    """
    Creates a CSV file in append mode. Returns the opened stream
    """
    now = dt.datetime.now()
    file_name = f'results/placements_{now.strftime("%d-%m-%Y--%H-%M-%S")}.csv'
    stream = open(file_name, 'a')
    output_header = ['time', 'node', 'sf']
    writer = csv.writer(stream)
    writer.writerow(output_header)
    return stream

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

    
    

