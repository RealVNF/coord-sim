import networkx as nx
import json
import os

def main():
    done = ['dfn_58.graphml', 'colt_153.graphml', 'gts_ce_149.graphml', 'intellifiber_73.graphml', 'triangle.graphml']
    networks = ['abilene_11.graphml']

    for net_file in networks:
        node_connectivity = {}
        edge_connectivity = {}
        graphml_network = nx.read_graphml(net_file, node_type=int)
        for u in graphml_network.nodes():
            u_id = f'pop{u}'
            node_connectivity[u_id] = {}
            edge_connectivity[u_id] = {}
            for v in graphml_network.nodes():
                v_id = f'pop{v}'
                if u_id != v_id:
                    node_connectivity[u_id][v_id] = nx.node_connectivity(graphml_network, s=u, t=v)
                    edge_connectivity[u_id][v_id] = nx.edge_connectivity(graphml_network, s=u, t=v)

        os.makedirs('connectivity/', exist_ok=True)
        with open(f'connectivity/{net_file}_node_con.json', 'w') as fp:
            json.dump(node_connectivity, fp)
        with open(f'connectivity/{net_file}_edge_con.json', 'w') as fp:
            json.dump(edge_connectivity, fp)


if __name__ == "__main__":
    main()