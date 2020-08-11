from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
import numpy as np
import matplotlib
import networkx
import pandas as pd
import os
matplotlib.use('TkAgg')


class PlacementAnime:

    def __init__(self, test_dir=None):
        self.test_dir = test_dir
        self.network_file = "abilene-in1-rand-cap0-2.graphml"
        self.placement_file = "placements.csv"
        self.rl_state_file = "rl_state.csv"
        self.resources_file = "resources.csv"
        self.net_x = networkx.read_graphml(self.network_file)
        self.placement = pd.read_csv(self.placement_file)
        self.placement = self.placement.groupby(["time"])
        self.node_pos = self.determine_node_pos()
        self.extent_offset = 5
        self.axis_extent = self.determine_extent()

        self.component_colors = {"a": "b", "b": "y", "c": "g"}
        self.component_offsets = {"a": -1, "b": 0, "c": 1}
        self.component_offsets_y = 1
        self.fig, self.ax = plt.subplots()
        self.ln = plt.plot([], [])
        self.draw_network()

    def get_filenames(self):
        listdir = os.listdir(self.test_dir)
        self.network_file = filter(lambda f: ".graphml")

    def draw_network(self):
        networkx.draw_networkx(self.net_x, pos=self.node_pos, ax=self.ax)
        #networkx.draw_networkx_labels(self.net_x, self.apply_label_offset(self.node_pos, 1), labels=dict(zip(list(self.node_pos.keys()), ["test"]*11)))

    def apply_label_offset(self, data, offset):
        return {key: np.array([value[0]+offset, value[1]+offset]) for key, value in data.items()}

    def determine_node_pos(self):
        if (all(map(lambda x: x[1].get("Latitude", None), self.net_x.nodes(data=True))) and
                all(map(lambda x: x[1].get("Longitude", None), self.net_x.nodes(data=True)))):
            return {node: np.array([data.get("Longitude", None), data.get("Latitude", None)])
                    for node, data in list(self.net_x.nodes(data=True))}
        else:
            return None

    def determine_extent(self):
        coordinates = np.array(list(self.node_pos.values()))
        return np.array([[np.min(coordinates[:, 0]) - self.extent_offset, np.max(coordinates[:, 0]) + self.extent_offset],
                         [np.min(coordinates[:, 1]) - self.extent_offset, np.max(coordinates[:, 1]) + self.extent_offset]])

    def plot_components(self, frame):
        ln = []
        for node, data in self.placement.get_group(frame).groupby(["node"]):
            x, y = self.node_pos[node.replace("pop", "")]
            for component in data["sf"]:
                ln.append(plt.text(x+self.component_offsets[component], y-self.component_offsets_y, component,
                                    color=self.component_colors[component], label=component))
        return ln

    def plot_used_resources_capacity(self):
        pass

    def init(self):
        self.ax.set_xlim(self.axis_extent[0, :])  # set limits
        self.ax.set_ylim(self.axis_extent[1, :])
        return self.ln

    def update(self, frame):
        lns = plt.plot([], [])
        ln2 = plt.plot([], [])
        ln2.append(plt.text(self.axis_extent[0, 0]+1, self.axis_extent[1, 0]+1, str(frame)))
        ln2.extend(self.plot_components(frame))
        lns.extend(self.ln)
        lns.extend(ln2)
        return lns

#print(type(placement.get_group(100)))


im = plt.imread("abilene-rand-cap.jpg", )

#implot = ax.imshow(im, extent=extent)

pa = PlacementAnime()
ani = FuncAnimation(pa.fig, pa.update, frames=list(pa.placement.groups), init_func=pa.init, blit=True)
plt.show()
