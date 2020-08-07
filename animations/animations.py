import matplotlib.pyplot as plt
import numpy as np
import matplotlib
import networkx
import pandas as pd
matplotlib.use('TkAgg')
from matplotlib.animation import FuncAnimation


network_file = "abilene-in3-rand-cap.graphml"
placement_file = "placements.csv"
net_x = networkx.read_graphml(network_file)
placement = pd.read_csv(placement_file)
placement = placement.groupby(["time"])
#print(type(placement.get_group(100)))
component_colors = {"a": "b", "b": "y", "c": "g"}
component_offsets = {"a": -1, "b": 0, "c": 1}

node_names = []
x_coord = []
y_coord = []
for node, data in net_x.nodes(data=True):
    node_names.append(node)
    x_coord.append(data.get("Longitude", None))
    y_coord.append(data.get("Latitude", None))

im = plt.imread("abilene-rand-cap.jpg", )
streching_x = 5
streching_y = 5
extent = [min(x_coord) - streching_x, max(x_coord) + streching_x, min(y_coord) - streching_y, max(y_coord) + streching_y]
fig, ax = plt.subplots()
implot = ax.imshow(im, extent=extent)


ln = plt.plot(x_coord, y_coord, 'ro')

def init():
    ax.set_xlim(min(x_coord) - streching_x, max(x_coord) + streching_x)
    ax.set_ylim(min(y_coord) - streching_y, max(y_coord) + streching_y)
    return ln

def update(frame):
    global ln
    lns = plt.plot([], [])
    ln2 = plt.plot([], [])
    for node, data in placement.get_group(frame).groupby(["node"]):
        x, y = x_coord[node_names.index(node.replace("pop", ""))], y_coord[node_names.index(node.replace("pop", ""))]
        for component in data["sf"]:
            ln2.extend(plt.plot(x+component_offsets[component], y-1, marker='o', color=component_colors[component], label=component))
    lns.extend(ln)
    lns.extend(ln2)
    ax.set_title(str(frame))
    """xdata.append(np.cos(frame))
    ydata.append(np.sin(frame))
    ax.set_xlim(min(xdata)-2, max(xdata)+2)
    ax.set_ylim(min(ydata)-2, max(ydata)+2)
    ln.set_data(xdata, ydata)"""
    return lns

ani = FuncAnimation(fig, update, frames=list(placement.groups),
                    init_func=init, blit=True)
plt.show()