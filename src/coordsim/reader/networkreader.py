import networkx as nx
from geopy.distance import vincenty
import numpy as np
from coordsim.network.node import Node

# Disclaimer: Some snippets of the following file were imported/modified from B-JointSP on GitHub.
# Original code can be found on https://github.com/CN-UPB/B-JointSP


def read_network(file, node_cap=None, link_cap=None):
    SPEED_OF_LIGHT = 299792458  # meter per second
    PROPAGATION_FACTOR = 0.77  	# https://en.wikipedia.org/wiki/Propagation_delay

    if not file.endswith(".graphml"):
        raise ValueError("{} is not a GraphML file".format(file))
    network = nx.read_graphml(file, node_type=int)

    # set links
    link_ids = [("pop{}".format(e[0]), "pop{}".format(e[1])) for e in network.edges]

    # calculate link delay based on geo positions of nodes; duplicate links for
    # bidirectionality and create complete links array
    edges = {}
    for e in network.edges(data=True):
        # Check whether LinkDelay value is set, otherwise default to -1
        link_delay = e[2].get("LinkDelay", -1)
        link_cap = e[2].get("LinkCap", link_cap)
        if (link_cap is None):
            raise ValueError("Link {} has incorrect or no capacity defined in graphml file.".format(e))
        delay = 0
        if link_delay == -1:
            n1 = network.nodes(data=True)[e[0]]
            n2 = network.nodes(data=True)[e[1]]
            n1_lat, n1_long = n1.get("Latitude"), n1.get("Longitude")
            n2_lat, n2_long = n2.get("Latitude"), n2.get("Longitude")
            distance = vincenty((n1_lat, n1_long), (n2_lat, n2_long)).meters		# in meters
            # round delay to int using np.around for consistency with emulator
            delay = int(np.around((distance / SPEED_OF_LIGHT * 1000) * PROPAGATION_FACTOR))  	# in milliseconds
        else:
            delay = link_delay
        edges[("pop{}".format(e[0]), "pop{}".format(e[1]))] = {"delay": delay, "cap": link_cap}

    # add reversed links for bidirectionality
    for e in network.edges(data=True):
        e = ("pop{}".format(e[0]), "pop{}".format(e[1]))
        e_reversed = (e[1], e[0])
        link_ids.append(e_reversed)
        edges[e_reversed] = edges[e]

    links = []
    for link in edges.keys():
        links.append({"src": link[0], "dest": link[1], "delay": edges[link]["delay"], "cap": edges[link]["cap"]})
    nodes = []
    for n in network.nodes(data=True):
        node_id = "pop{}".format(n[0])
        cap = n[1].get("NodeCap", node_cap)
        node_type = n[1].get("NodeType", "Normal")
        node_name = n[1].get("label", None)
        if (cap is None):
            raise ValueError("No CPU or mem. specified for {} (as cmd argument or in graphml)".format(file))
        # Completing the nodes list with Node objects
        nodes.append(Node(node_id, node_name, node_type, cap))
        # nodes.append({"id": node_id, "name": node_name, "type": node_type, "cpu": cpu, "mem": mem})

    return nodes, links
