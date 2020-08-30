from matplotlib.animation import FuncAnimation, ArtistAnimation
from geopy.distance import distance as dist
from matplotlib.widgets import Slider
from argparse import ArgumentParser
from pprint import pprint
import matplotlib.pyplot as plt
import numpy as np
import matplotlib
import networkx
import pandas as pd
import os
matplotlib.use('TkAgg')


class PlacementAnime:

    def __init__(self, test_dir=".", placement_file="placements.csv", rl_state_file="rl_state.csv",
                 resources_file="resources.csv"):
        self.test_dir = test_dir
        self.network_file = self.get_network_filename()
        self.placement_file = os.path.join(test_dir, placement_file)
        self.rl_state_file = os.path.join(test_dir, rl_state_file)
        self.resources_file = os.path.join(test_dir, resources_file)

        self.net_x = networkx.read_graphml(self.network_file)
        self.set_linkDelay()
        self.placement = pd.read_csv(self.placement_file)
        self.placement = self.placement.groupby(["time"])
        self.ingress_traffic = pd.read_csv(self.rl_state_file, header=None)
        self.ingress_traffic.columns = ["episode", "time"]+[f"pop{i}" for i in range(self.net_x.number_of_nodes())]
        self.node_pos = self.determine_node_pos()
        self.edge_pos = self.determine_edge_pos()
        self.extent_offset = 5
        self.axis_extent = self.determine_extent()

        self.component_colors = {"a": "b", "b": "y", "c": "g"}
        self.component_offsets = {"a": -1, "b": 0, "c": 1}
        self.component_offsets_y = 1
        self.ingress_node_colors = {"pop0": "b", "pop1": "y", "pop2": "g"}
        self.last_point = {"pop0": [0, 0], "pop1": [0, 0], "pop2": [0, 0]}

        self.fig = plt.figure()
        #self.ax = plt.subplots(2, 1)
        self.ax, self.ing_traffic_ax = self.fig.add_subplot(211), self.fig.add_subplot(212)
        self.ln = plt.plot([], [])
        self.ln.extend(self.draw_network())
        self.ln.extend(self.plot_capacity())
        self.ln.extend(self.plot_delay())
        #self.time_label = plt.text(self.axis_extent[0, 0] + 1, self.axis_extent[1, 0] + 1, "0")
        #self.ln.append(self.time_label)
        self.animation = None
        self.artists = []
        self.moments = []
        self.ln_ingress = []

        if not test_dir == ".":
            self.video_filename = os.path.basename(os.path.dirname(test_dir))
        else:
            self.video_filename = "animation_video"

    def get_network_filename(self):
        listdir = os.listdir(self.test_dir)
        return os.path.join(self.test_dir, list(filter(lambda f: ".graphml" in f, listdir))[0])

    def draw_network(self):
        ln = plt.plot([], [])
        ln.append(networkx.draw_networkx_nodes(self.net_x, pos=self.node_pos, ax=self.ax))  # , ax=self.ax)
        ln.append(networkx.draw_networkx_edges(self.net_x, pos=self.node_pos, ax=self.ax))
        #ln.append(networkx.draw_networkx_labels(self.net_x, pos=self.node_pos))
        #networkx.draw_networkx_labels(self.net_x, self.apply_label_offset(self.node_pos, 1), labels=dict(zip(list(self.node_pos.keys()), ["test"]*11)))
        return ln

    def apply_label_offset(self, data, offset):
        return {key: np.array([value[0]+offset, value[1]+offset]) for key, value in data.items()}

    def determine_node_pos(self):
        if (all(map(lambda x: x[1].get("Latitude", None), self.net_x.nodes(data=True))) and
                all(map(lambda x: x[1].get("Longitude", None), self.net_x.nodes(data=True)))):
            return {node: np.array([data.get("Longitude", None), data.get("Latitude", None)])
                    for node, data in list(self.net_x.nodes(data=True))}
        else:
            return None

    def determine_edge_pos(self):
        edge_pos = {}
        for source, target, data in self.net_x.edges(data=True):
            edge_pos[(source, target)] = (self.node_pos[source] + self.node_pos[target])/2
        return edge_pos

    def determine_extent(self):
        coordinates = np.array(list(self.node_pos.values()))
        return np.array([[np.min(coordinates[:, 0]) - self.extent_offset, np.max(coordinates[:, 0]) + self.extent_offset],
                         [np.min(coordinates[:, 1]) - self.extent_offset, np.max(coordinates[:, 1]) + self.extent_offset]])

    def set_linkDelay(self):
        SPEED_OF_LIGHT = 299792458  # meter per second
        PROPAGATION_FACTOR = 0.77  # https://en.wikipedia.org/wiki/Propagation_delay
        for e in self.net_x.edges(data=True):
            link_delay = e[2].get("LinkDelay", None)
            # As edges are undirectional, only LinkFwdCap determines the available data rate
            # link_fwd_cap = e[2].get("LinkFwdCap", 1000)
            delay = 3
            if link_delay is None:
                n1 = self.net_x.nodes(data=True)[e[0]]
                n2 = self.net_x.nodes(data=True)[e[1]]
                n1_lat, n1_long = n1.get("Latitude", None), n1.get("Longitude", None)
                n2_lat, n2_long = n2.get("Latitude", None), n2.get("Longitude", None)
                if not (n1_lat is None or n1_long is None or n2_lat is None or n2_long is None):
                    distance = dist((n1_lat, n1_long), (n2_lat, n2_long)).meters  # in meters
                    # round delay to int using np.around for consistency with emulator
                    delay = int(np.around((distance / SPEED_OF_LIGHT * 1000) * PROPAGATION_FACTOR))  # in milliseconds
            else:
                delay = link_delay
            e[2]["LinkDelay"] = delay

    def plot_components(self, frame):
        ln = []
        for node, data in self.placement.get_group(frame).groupby(["node"]):
            x, y = self.node_pos[node.replace("pop", "")]
            for component in data["sf"]:
                ln.append(self.ax.text(x+self.component_offsets[component], y-self.component_offsets_y, component,
                                    color=self.component_colors[component], label=component))
        return ln

    def plot_capacity(self):
        ln = []
        for node, pos in self.node_pos.items():
            ln.append(self.ax.text(*(pos+1), s=self.net_x.nodes(data=True)[node].get("NodeCap", None), fontdict={"color": "b"}))
        return ln

    def plot_delay(self):
        ln = []
        for edge, pos in self.edge_pos.items():
            for e in self.net_x.edges(data=True):
                if edge[0] in e and edge[1] in e:
                    ln.append(self.ax.text(*pos, s=e[2].get("LinkDelay", None), fontdict={"color": "r"}))
        return ln

    def plot_ingress_traffic(self, frame):
        ln = plt.plot([], [])
        for node in self.net_x.nodes:
            x = np.array([self.last_point[f"pop{node}"][0], frame])
            y = np.array([self.last_point[f"pop{node}"][1], self.ingress_traffic[f"pop{node}"][self.ingress_traffic["time"] == frame].iloc[0]])
            #print(frame, y)
            ln.extend(self.ing_traffic_ax.plot(x, y, color=self.ingress_node_colors[f"pop{node}"]))
            self.last_point[f"pop{node}"][0] = x[1]
            self.last_point[f"pop{node}"][1] = y[1]
            #ln.extend(self.ing_traffic_ax.plot([frame], [y], color=self.ingress_node_colors[node]))
        return ln

    def init(self):
        self.ax.set_xlim(self.axis_extent[0, :])  # set limits
        self.ax.set_ylim(self.axis_extent[1, :])
        self.ing_traffic_ax.set_xlim([self.ingress_traffic["time"][0], self.ingress_traffic["time"][self.ingress_traffic["time"].size - 1]])
        #self.ing_traffic_ax.set_xlim([0, 15000])
        self.ing_traffic_ax.set_ylim([0, 0.5])
        return self.ln

    def plot_moment(self, frame):
        ln2 = plt.plot([], [])
        # self.time_label._text = str(frame)
        # print("changed: ", self.time_label)
        ln2.extend(self.plot_components(frame))
        ln2.append(self.ax.text(self.axis_extent[0, 0] + 1, self.axis_extent[1, 0] + 1, str(frame)))
        #self.ln_ingress.extend(self.plot_ingress_traffic(frame))
        #ln2.extend(self.ln_ingress)
        return ln2

    def create_moments(self):
        ln = []
        self.init()
        for frame in self.placement.groups:
            ln.append(self.plot_moment(frame))
        self.moments.extend(ln)

    def update(self, frame):
        lns = plt.plot([], [])
        ln2 = plt.plot([], [])
        #self.time_label._text = str(frame)
        #print("changed: ", self.time_label)
        ln2.extend(self.plot_components(frame))
        ln2.append(self.ax.text(self.axis_extent[0, 0] + 1, self.axis_extent[1, 0] + 1, str(frame)))
        self.ln.extend(self.plot_ingress_traffic(frame))
        lns.extend(self.ln)
        lns.extend(ln2)
        return lns

    def create_artists(self):
        ln = []
        self.init()
        for frame in self.placement.groups:
            ln.append(self.update(frame))
        return ln

    def create_animation(self):
        self.artists = [self.ln]
        self.artists.extend(self.create_artists())
        self.animation = ArtistAnimation(self.fig, self.artists, interval=100, repeat=False)


class PlacementAnimesManager:

    def __init__(self, results_dir):
        self.cur_anime = None
        self.animes = []
        for root, subdirs, files in os.walk(results_dir):
            if len(files) != 0 and "test" in root:
                self.animes.append(root)

    def load_animation(self, root):
        self.cur_anime = PlacementAnime(root)
        self.cur_anime.create_animation()
        return self.cur_anime


def parse_args(args=None):
    parser = ArgumentParser()
    parser.add_argument("--results_dir", default=None)
    parser.add_argument("--test_dir", default=None)
    #parser.add_argument("-a", "--timestamp_seed_agent", default=None, dest="timestamp_seed_agent")
    #parser.add_argument("-t", "--timestamp_seed_test", default=None, dest="timestamp_seed_test")
    parser.add_argument("-st", "--show_tests", default=False, action="store_true", dest="show_tests")
    parser.add_argument("--show", default=False, action="store_true")
    parser.add_argument("--save", default=False, action="store_true")
    return vars(parser.parse_args(args))


def list_tests(results_dir):
    animes = []
    for root, subdirs, files in os.walk(results_dir):
        if len(files) != 0 and "test" in root:
            animes.append(root)
    return animes


def main(args=None):
    args = parse_args(args)
    tests = None
    if args["results_dir"]:
        tests = list_tests(args["results_dir"])
    print(args)
    if args["show_tests"]:
        pprint(tests)
    else:
        if not args["test_dir"]:
            args["test_dir"] = tests[0]
        pa = PlacementAnime(args["test_dir"])
        pa.create_animation()
        if args["show"]:
            plt.show()
        if args["save"]:
            print(f'{pa.video_filename}.html')
            html = pa.animation.to_html5_video()
            with open(f'{pa.video_filename}.html', 'w') as f:
                f.write(html)

    # plt.show()
    #list(pam.animes.values())[0].fig.show()


if __name__ == "__main__":
    #main(["--test_dir", ".", "--show"])
    main()
    """pa = PlacementAnime()
    artists = [pa.ln]
    artists.extend(pa.create_artists())
    ani = ArtistAnimation(pa.fig, artists, interval=1, repeat=False)

    plt.show()"""
    """html = ani.to_html5_video()
    with open('ani.html', 'w') as f:
        f.write(html)"""
