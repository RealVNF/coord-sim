import networkx as nx
from geopy.distance import vincenty
import numpy as np
import logging as log
import yaml
import math
from collections import defaultdict


# Disclaimer: Some snippets of the following file were imported/modified from B-JointSP on GitHub.
# Original code can be found on https://github.com/CN-UPB/B-JointSP

# Returns the current placement of VNF's in the network as a Dict of nodes with the list of VNF's placed in it.
# The Placement for now is done using a static file.
# This later would be changed to the latest placements suggested by an RL Agent.


# Open yaml file and pass data to other functions for procesing.
def network_update(yaml_file, network):
    with open(yaml_file) as yaml_stream:
        yaml_data = yaml.load(yaml_stream)
    return get_placement(yaml_data, network), get_sfc(yaml_data), get_sf(yaml_data)


# Get the placement from the yaml data.
def get_placement(placement_data, network):
    vnf_placements = defaultdict(list)
    # Getting the placements
    for vnf in placement_data['placement']['vnfs']:
        node = vnf['node']
        vnf_name = vnf['name']
        vnf_placements[node].append(vnf_name)
    # Updating the placements in the NetworkX Graph
    for node in network.nodes().items():
        node[1]['available_sf'] = {}
        for sf in vnf_placements[node[0]]:
            node[1]['available_sf'][sf] = 1

    return vnf_placements


# Get the list of SFCs from the yaml data.
def get_sfc(sfc_data):
    sfc_list = {}
    for sfc_name, sfc_sf in sfc_data['sfc_list'].items():
        sfc_list[sfc_name] = sfc_sf
    return sfc_list


# Get the list of SFs and their properties from the yaml data.
def get_sf(sf_data):
    sf_list = {}
    for sf_name, sf_details in sf_data['sf_list'].items():
        sf_list[sf_name] = sf_details
    return sf_list


# edge weight = 1 / (cap + 1/delay) => prefer high cap, use smaller delay as additional influence/tie breaker
def weight(edge_cap, edge_delay):
    if edge_cap == 0:
        return math.inf
    elif edge_delay == 0:
        return 0
    return 1 / (edge_cap + 1 / edge_delay)


# finds the all pairs shortest paths using Johnson Algo
# returns a dictionary, keyed by source and target, of all pairs shortest paths(not the shortest len).
def shortest_paths(networkx_network):
    return dict(nx.johnson(networkx_network,weight='weight'))


# Read the GraphML file and return list of nodes and edges.
def read_network(file, node_cap=None, link_cap=None):
    SPEED_OF_LIGHT = 299792458  # meter per second
    PROPAGATION_FACTOR = 0.77  # https://en.wikipedia.org/wiki/Propagation_delay

    if not file.endswith(".graphml"):
        raise ValueError("{} is not a GraphML file".format(file))
    graphml_network = nx.read_graphml(file, node_type=int)
    networkx_network = nx.DiGraph()

    #  Setting the nodes of the NetworkX Graph
    for n in graphml_network.nodes(data=True):
        node_id = "pop{}".format(n[0])
        cap = n[1].get("NodeCap", None)
        if cap is None:
            cap = node_cap
            log.warning("NodeCap not set in the GraphML file, now using default NodeCap for node: {}".format(n))
        node_type = n[1].get("NodeType", "Normal")
        node_name = n[1].get("label", None)
        if cap is None:
            raise ValueError("No NodeCap. set for node{} in file {} (as cmd argument or in graphml)".format(n, file))
        # Adding a Node in the NetworkX Graph
        # {"id": node_id, "name": node_name, "type": node_type, "cap": cpu})
        # Type of node. For now it is either "Normal" or "Ingress"
        # Init 'remaining_resources' to the node capacity
        networkx_network.add_node(node_id, name=node_name, type=node_type, cap=cap, available_sf={},
                                  remaining_cap=cap)

    # set links
    # calculate link delay based on geo positions of nodes;

    for e in graphml_network.edges(data=True):
        # Check whether LinkDelay value is set, otherwise default to None
        source = "pop{}".format(e[0])
        target = "pop{}".format(e[1])
        link_delay = e[2].get("LinkDelay", None)
        link_fwd_cap = e[2].get("LinkFwdCap", link_cap)
        link_bkwd_cap = e[2].get("LinkBkwdCap", link_cap)
        if e[2].get("LinkFwdCap") is None and e[2].get("LinkBkwdCap") is None:
            log.warning("Link {} has no capacity defined in graphml file. So, Using the default capacity".format(e))
        # Setting a default delay of 3 incase no delay specified in GraphML file
        # and we are unable to set it based on Geo location
        delay = 3
        if link_delay is None:
            n1 = graphml_network.nodes(data=True)[e[0]]
            n2 = graphml_network.nodes(data=True)[e[1]]
            n1_lat, n1_long = n1.get("Latitude", None), n1.get("Longitude", None)
            n2_lat, n2_long = n2.get("Latitude", None), n2.get("Longitude", None)
            if n1_lat is None or n1_long is None or n2_lat is None or n2_long is None:
                log.warning("Link Delay not set in the GraphML file and unable to calc based on Geo Location,"
                            "Now using default delay for edge: ({},{})".format(source, target))
            else:
                distance = vincenty((n1_lat, n1_long), (n2_lat, n2_long)).meters  # in meters
                # round delay to int using np.around for consistency with emulator
                delay = int(np.around((distance / SPEED_OF_LIGHT * 1000) * PROPAGATION_FACTOR))  # in milliseconds
        else:
            delay = link_delay

        # Adding the directed edges(forward and backward) for each link defined in the network.
        # delay = edge delay , cap = edge capacity in that direction
        networkx_network.add_edge(source, target, delay=delay, cap=link_fwd_cap)
        networkx_network.add_edge(target, source, delay=delay, cap=link_bkwd_cap)

    # setting the weight property for each edge in the NetworkX Graph
    # weight attribute is used to find the shortest paths
    for edge in networkx_network.edges.items():
        edge[1]['weight'] = weight(edge[1]['cap'],edge[1]['delay'])

    return networkx_network
