from matplotlib.animation import ArtistAnimation
from geopy.distance import distance as dist
from argparse import ArgumentParser
from pprint import pprint
import matplotlib.pyplot as plt
import numpy as np
import matplotlib
import networkx
import pandas as pd
import os
import matplotlib.gridspec as gridspec
matplotlib.use('TkAgg')


class PlacementAnime:
    """
    Class for handling data for the animation.
    """
    def __init__(self, test_dir=".", placement_file="placements.csv", rl_state_file="rl_state.csv",
                 resources_file="resources.csv"):
        # directories for the source files
        self.test_dir = test_dir
        self.network_file = self.get_network_filename()
        self.placement_file = os.path.join(test_dir, placement_file)
        self.rl_state_file = os.path.join(test_dir, rl_state_file)
        self.resources_file = os.path.join(test_dir, resources_file)
        if not test_dir == ".":
            self.video_filename = os.path.basename(os.path.dirname(test_dir))
        else:
            self.video_filename = "animation_video"

        self.resources = pd.read_csv(self.resources_file).groupby(["time"])

        self.net_x = networkx.read_graphml(self.network_file)
        self.set_linkDelay()  # compute LinkDelay from nodes positions and write it to the networkx object
        self.placement = pd.read_csv(self.placement_file)
        self.placement = self.placement.groupby(["time"])
        self.ingress_traffic = pd.read_csv(self.rl_state_file, header=None)
        self.ingress_traffic.columns = ["episode", "time"]+[f"pop{i}" for i in range(self.net_x.number_of_nodes())]

        # positions in the format for networkx plot function
        # position dictionaries related to networkx objects have keys "0", "1", "2" etc. not "pop0", "pop1", "pop2" etc.
        self.node_pos = self.determine_node_pos()
        self.edge_pos = self.determine_edge_pos()
        self.extent_offset = 5
        self.axis_extent = self.determine_extent()  # axis limits of the plot
        self.node_colors = [(0, 0, 1) for i in self.net_x.nodes]
        self.node_load_cmap = plt.cm.get_cmap("RdYlGn_r", 10)

        self.component_colors = {"a": "b", "b": "y", "c": "g"}
        # component placement marks offset on x axis in relation to the node position
        self.component_offsets = {"a": -1, "b": 0, "c": 1}
        self.component_offsets_y = 1  # same for the y axis
        cm = plt.cm.get_cmap("hsv", self.net_x.number_of_nodes())
        # curve color in the ingress traffic plot
        self.ingress_node_colors = {f"pop{i}": cm(i) for i in range(self.net_x.number_of_nodes())}
        self.last_point = {f"pop{i}": [0, 0] for i in range(self.net_x.number_of_nodes())}

        # object variables for plot object, set in function create_animation and other
        self.fig = None
        # self.ax = plt.subplots(2, 1)
        self.ax, self.ing_traffic_ax = None, None
        self.ln = None  # contains static parts of the plot
        # self.time_label = plt.text(self.axis_extent[0, 0] + 1, self.axis_extent[1, 0] + 1, "0")
        # self.ln.append(self.time_label)
        self.artists = []  # list of artists to pass to the ArtistAnimation object
        self.animation = None  # animation object

        self.moments = []  # for the slider attempt
        self.ln_ingress = []

    def get_network_filename(self):
        listdir = os.listdir(self.test_dir)
        print(os.path.join(self.test_dir, list(filter(lambda f: ".graphml" in f, listdir))[0]))
        return os.path.join(self.test_dir, list(filter(lambda f: ".graphml" in f, listdir))[0])

    def draw_network(self):
        ln = [#networkx.draw_networkx_nodes(self.net_x, pos=self.node_pos, ax=self.ax),
              networkx.draw_networkx_edges(self.net_x, pos=self.node_pos, ax=self.ax)]
        return ln

    def apply_label_offset(self, data, offset):
        """
        Currently not used. Was for using the networkx plot funtions with offsets.
        :param data: dict of the form {key1: [x1, y1], key2: [x2, y2], ...}
        :param offset: int
        :return: dict of the form {key1: [x1 + offset, y1 + offset], key2: [x2 + offset, y2 + offset], ...}
        """
        return {key: np.array([value[0]+offset, value[1]+offset]) for key, value in data.items()}

    def determine_node_pos(self):
        # if all nodes have those properties
        if (all(map(lambda x: x[1].get("Latitude", None), self.net_x.nodes(data=True))) and
                all(map(lambda x: x[1].get("Longitude", None), self.net_x.nodes(data=True)))):
            return {node: np.array([data.get("Longitude", None), data.get("Latitude", None)])
                    for node, data in list(self.net_x.nodes(data=True))}  # format for networkx plot functions
        else:
            return None

    def determine_edge_pos(self):
        # same format as for the nodes, but not used anymore
        edge_pos = {}
        for source, target, data in self.net_x.edges(data=True):
            edge_pos[(source, target)] = (self.node_pos[source] + self.node_pos[target])/2
        return edge_pos

    def determine_extent(self):
        # used for xlim and ylim plot properties: outmost node position + extent_offset
        coordinates = np.array(list(self.node_pos.values()))
        return np.array(
            [[np.min(coordinates[:, 0]) - self.extent_offset, np.max(coordinates[:, 0]) + self.extent_offset],
             [np.min(coordinates[:, 1]) - self.extent_offset, np.max(coordinates[:, 1]) + self.extent_offset]]
        )

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
        """
        Plots component letters for a point in time (frame) using plt.text
        :param frame: int
        :return: axis
        """
        ln = []
        for node, data in self.placement.get_group(frame).groupby(["node"]):
            x, y = self.node_pos[node.replace("pop", "")]
            for component in data["sf"]:
                ln.append(self.ax.text(x+self.component_offsets[component], y-self.component_offsets_y, component,
                                       color=self.component_colors[component], label=component))
        return ln

    def plot_capacity(self):
        """
        plots capacity in the right upper coner from the node (offset +1)
        :return: axis
        """
        ln = []
        for node, pos in self.node_pos.items():
            ln.append(self.ax.text(*(pos+1), s=self.net_x.nodes(data=True)[node].get("NodeCap", None),
                                   fontdict={"color": "b"}))
        return ln

    def plot_node_load(self, frame):
        """
        Plots node_load in the format <used_resources>/<node_capacity>
        :param frame:
        :return: axis
        """
        ln = []
        node_colors = [(0.0, 0.0, 0.0, 1.0)]*self.net_x.number_of_nodes()
        for node, data in self.resources.get_group(frame).groupby(["node"]):
            x, y = self.node_pos[node.replace("pop", "")] + 1
            capacity = data['node_capacity'].iloc[0]
            if capacity != 0:
                node_load = data['used_resources'].iloc[0]/capacity
                node_color = self.node_load_cmap(node_load)
            else:
                node_load = 0
                node_color = (0.0, 0.0, 0.0, 1.0)
            node_colors[int(node.replace("pop", ""))] = node_color
            ln.append(self.ax.text(x, y, f"{data['used_resources'].iloc[0]}/{data['node_capacity'].iloc[0]}",
                                   color=node_color))
        ln.append(networkx.draw_networkx_nodes(self.net_x, pos=self.node_pos, ax=self.ax, node_color=node_colors))
        return ln

    def plot_delay(self):
        """
        plots delay on the edges
        :return: axis
        """
        ln = []
        for edge, pos in self.edge_pos.items():
            for e in self.net_x.edges(data=True):
                if edge[0] in e and edge[1] in e:
                    ln.append(self.ax.text(*pos, s=e[2].get("LinkDelay", None), fontdict={"color": "r"}))
        return ln

    def plot_node_ids(self):
        ln = []
        for node, pos in self.node_pos.items():
            ln.append(self.ax.text(*(pos-0.2), s=str(node)))
        return ln

    def plot_ingress_traffic(self, frame):
        """
        plots a line from the previous point self.last_point[node]==[frame-1, value] to the current point (frame, value)
        :param frame: int
        :return: axis
        """
        ln = plt.plot([], [])
        for node in self.net_x.nodes:
            x = np.array([self.last_point[f"pop{node}"][0], frame])
            y = np.array([self.last_point[f"pop{node}"][1],
                          self.ingress_traffic[f"pop{node}"][self.ingress_traffic["time"] == frame].iloc[0]])

            ln.extend(self.ing_traffic_ax.plot(x, y, color=self.ingress_node_colors[f"pop{node}"]))

            self.last_point[f"pop{node}"][0] = x[1]
            self.last_point[f"pop{node}"][1] = y[1]
            # ln.extend(self.ing_traffic_ax.plot([frame], [y], color=self.ingress_node_colors[node]))
        return ln

    def init(self):
        """
        Sets xlim and ylim for both axis objects
        :return:
        """
        self.ax.set_xlim(self.axis_extent[0, :])  # set limits
        self.ax.set_ylim(self.axis_extent[1, :])

        # xlim = [first point in time, last point in time]
        self.ing_traffic_ax.set_xlim([self.ingress_traffic["time"][0],
                                      self.ingress_traffic["time"][self.ingress_traffic["time"].size - 1]])
        columns = [col for col in self.ingress_traffic.columns if "pop" in col]
        ing_max = np.max(np.max(self.ingress_traffic[columns]))
        self.ing_traffic_ax.set_ylim([0, ing_max * 1.01])
        return self.ln

    def plot_moment(self, frame):
        # for the slider attempt
        ln2 = plt.plot([], [])
        # self.time_label._text = str(frame)
        # print("changed: ", self.time_label)
        ln2.extend(self.plot_components(frame))
        ln2.append(self.ax.text(self.axis_extent[0, 0] + 1, self.axis_extent[1, 0] + 1, str(frame)))
        # self.ln_ingress.extend(self.plot_ingress_traffic(frame))
        # ln2.extend(self.ln_ingress)
        return ln2

    def create_moments(self):
        # for the slider attempt
        ln = []
        self.init()
        for frame in self.placement.groups:
            ln.append(self.plot_moment(frame))
        self.moments.extend(ln)

    def update(self, frame):
        """
        Creates plots for one single frame==point in time
        :param frame: int
        :return: axis
        """
        lns = plt.plot([], [])
        ln2 = plt.plot([], [])
        # self.time_label._text = str(frame)
        # print("changed: ", self.time_label)
        ln2.extend(self.plot_components(frame))
        if frame == 0:
            pass
        else:
            ln2.extend(self.plot_node_load(frame))

        # plot the point in time as text: 1 point from the left lower corner
        ln2.append(self.ax.text(self.axis_extent[0, 0] + 1, self.axis_extent[1, 0] + 1, str(frame)))

        self.ln.extend(self.plot_ingress_traffic(frame))
        lns.extend(self.ln)
        lns.extend(ln2)
        return lns

    def create_artists(self):
        """
        Creates artists
        :return: axis
        """
        ln = []
        for frame in self.placement.groups:
            ln.append(self.update(frame))
        return ln

    def create_animation(self):
        """
        Upper function. Calls other functions and creates the animation object
        :return: None
        """
        self.fig = plt.figure()
        gs = self.fig.add_gridspec(10, 1)
        self.ax, self.ing_traffic_ax = self.fig.add_subplot(gs[:-1, 0]), self.fig.add_subplot(gs[-1, 0])
        self.init()

        self.ln = plt.plot([], [])
        self.ln.extend(self.draw_network())
        # self.plot_node_ids()
        # self.ln.extend(self.plot_capacity())
        self.ln.extend(self.plot_delay())

        self.artists = [self.ln]
        self.artists.extend(self.create_artists())
        self.animation = ArtistAnimation(self.fig, self.artists, interval=100, repeat=False)

    def save_animation(self, mode, VIDEO_DIR="."):
        """
        Create and save matplotlib animation
        :param mode: How to save the animation. Options: 'video' (=html5) or 'gif' (requires ImageMagick)
        """

        # save html5 video
        if mode == 'html' or mode == 'both':
            html = self.animation.to_html5_video()
            with open(f'{VIDEO_DIR}/{self.video_filename}.html', 'w') as f:
                f.write(html)
            # self.log.info('Video saved', path=f'{VIDEO_DIR}/{self.result_filename}.html')

        # save gif; requires external dependency ImageMagick
        if mode == 'gif' or mode == 'both':
            try:
                self.animation.save(f'{VIDEO_DIR}/{self.video_filename}.gif', writer='imagemagick')
                # self.log.info('Gif saved', path=f'{VIDEO_DIR}/{self.result_filename}.gif')
            except TypeError as e:
                # self.log.error('ImageMagick needs to be installed for saving gifs.')
                print(type(e), e)


class PlacementAnimesManager:
    """
    For the dropdown menu attempt
    """
    def __init__(self, results_dir):
        """finds all the test directories"""
        self.cur_anime = None
        self.animes = []
        for root, subdirs, files in os.walk(results_dir):
            if len(files) != 0 and "test" in root:
                self.animes.append(root)

    def load_animation(self, root):
        """
        Creates the animation
        :param root: test directory
        :return:
        """
        self.cur_anime = PlacementAnime(root)
        self.cur_anime.create_animation()
        return self.cur_anime


def parse_args(args=None):
    parser = ArgumentParser()
    parser.add_argument("--results_dir", default=None)
    parser.add_argument("--test_dir", default=None)
    # parser.add_argument("-a", "--timestamp_seed_agent", default=None, dest="timestamp_seed_agent")
    # parser.add_argument("-t", "--timestamp_seed_test", default=None, dest="timestamp_seed_test")
    parser.add_argument("-st", "--show_tests", default=False, action="store_true", dest="show_tests")
    parser.add_argument("--show", default=False, action="store_true",)
    parser.add_argument("--save", default=None, choices=["html", "gif", "both"])
    return vars(parser.parse_args(args))


def list_tests(results_dir):
    """
    Finds all the test directories of a results directory
    :param results_dir: str
    :return: list of directory strings (relative to current execution point)
    """
    animes = []
    for root, subdirs, files in os.walk(results_dir):
        if len(files) != 0 and "test" in root:
            animes.append(root)
    return animes


def main(args=None):
    """
    Main function
    :param args:
    :return:
    """
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
            pa.save_animation(args["save"])
            if args["save"] == "both":
                print(f'{pa.video_filename}.html', " and ", f'{pa.video_filename}.gif')
            else:
                print(f'{pa.video_filename}.{args["save"]}')

    # plt.show()
    # list(pam.animes.values())[0].fig.show()


if __name__ == "__main__":
    main(["--results_dir", "w-prediction", "--show"])
    #main()
    """pa = PlacementAnime()
    artists = [pa.ln]
    artists.extend(pa.create_artists())
    ani = ArtistAnimation(pa.fig, artists, interval=1, repeat=False)

    plt.show()"""
    """html = ani.to_html5_video()
    with open('ani.html', 'w') as f:
        f.write(html)"""
