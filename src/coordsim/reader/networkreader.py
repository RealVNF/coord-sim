import networkx as nx
from geopy.distance import vincenty
import numpy as np
import logging as log
import yaml
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
    print(sf_data['sf_list'])
    sf_list = {}
    for sf_name, sf_details in sf_data['sf_list'].items():
        sf_list[sf_name] = sf_details
    return sf_list


# Read the GraphML file and return list of nodes and edges.
def read_network(file, node_cap=None, link_fwd_cap=None, link_bkwd_cap=None):
    SPEED_OF_LIGHT = 299792458  # meter per second
    PROPAGATION_FACTOR = 0.77  # https://en.wikipedia.org/wiki/Propagation_delay

    if not file.endswith(".graphml"):
        raise ValueError("{} is not a GraphML file".format(file))
    graphml_network = nx.read_graphml(file, node_type=int)
    networkx_network = nx.DiGraph()

    #  Setting the nodes of the NetworkX Graph
    for n in graphml_network.nodes(data=True):
        node_id = "pop{}".format(n[0])
        cap = n[1].get("NodeCap", node_cap)
        if cap == node_cap:
            log.warning("Using default NodeCap for node: {}".format(n))
        node_type = n[1].get("NodeType", "Normal")
        node_name = n[1].get("label", None)
        if cap is None:
            raise ValueError("No NodeCap. set for node{} in file {} (as cmd argument or in graphml)".format(n, file))
        # Adding a Node object as a Node in the NetworkX Graph
        # {"id": node_id, "name": node_name, "type": node_type, "cap": cpu})
        # Type of node. For now it is either "Normal" or "Ingress"
        networkx_network.add_node(node_id, name=node_name, type=node_type, cap=cap, available_sf={})

    # set links
    # calculate link delay based on geo positions of nodes;

    for e in graphml_network.edges(data=True):
        # Check whether LinkDelay value is set, otherwise default to -1
        source = "pop{}".format(e[0])
        target = "pop{}".format(e[1])
        link_delay = e[2].get("LinkDelay", -1)
        link_fwd_cap = e[2].get("LinkFwdCap", link_fwd_cap)
        link_bkwd_cap = e[2].get("LinkBkwdCap", link_bkwd_cap)
        if link_fwd_cap is None and link_bkwd_cap is None:
            raise ValueError("Link {} has incorrect or no capacity defined in graphml file.".format(e))
        delay = 0
        if link_delay == -1:
            n1 = graphml_network.nodes(data=True)[e[0]]
            n2 = graphml_network.nodes(data=True)[e[1]]
            n1_lat, n1_long = n1.get("Latitude"), n1.get("Longitude")
            n2_lat, n2_long = n2.get("Latitude"), n2.get("Longitude")
            distance = vincenty((n1_lat, n1_long), (n2_lat, n2_long)).meters  # in meters
            # round delay to int using np.around for consistency with emulator
            delay = int(np.around((distance / SPEED_OF_LIGHT * 1000) * PROPAGATION_FACTOR))  # in milliseconds
        else:
            delay = link_delay
        # delay = edge delay , cap = edge capacity in that direction
        if e[2].get("LinkFwdCap") is not None:
            networkx_network.add_edge(source, target, delay=delay, cap=link_fwd_cap)
        if e[2].get("LinkBkwdCap") is not None:
            networkx_network.add_edge(target, source, delay=delay, cap=link_bkwd_cap)

    return networkx_network
