import os
import threading
import logging
import time
import yaml
import concurrent.futures
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from lxml import etree
from argparse import ArgumentParser


class TraceXMLReader():
    node_map_abilene = {'ATLAM5': None,
                        'ATLAng': "pop9",
                        'CHINng': "pop1",
                        'DNVRng': "pop6",
                        'HSTNng': "pop8",
                        'IPLSng': "pop10",
                        'KSCYng': "pop7",
                        'LOSAng': "pop5",
                        'NYCMng': "pop0",
                        'SNVAng': "pop4",
                        'STTLng': "pop3",
                        'WASHng': "pop2"}

    def __init__(self, source=None, _from=0, to=None, scale_factor=0.001, run_duration=100,
                 change_rate=2, node_name_map=None, intermediate_result_filename=None, result_trace_filename=None,
                 ingress_nodes=None, plot_figsize=(20, 10), squash_rate=1, *args, **kwargs):
        """
        Handles all parameters of the reader.
            source: str: path to directory or to intermediat .csv file
            _from and to: ints: in function read_all_files_parallel os.listdir(directory)[_from:to] is called to choose
                                the files
            scale_factor: float: scale data_rate, applied in function process_df
            run_duration: int: used to compute the time column, applied in function process_df
            change_rate: int: number of run_durations the traffic stays constant, used to compute the time column,
                              applied in function process_df
            node_name_map: dict or str(path): defines how to rename nodes (from keys to values). If argumnet is None old
                                              names will be kept. If a node is set to None it will be removed from the
                                              dataframe. If a node is not in the dict or yaml it will be ignored, the
                                              name will be kept. Applied in function read_one_file.
            intermediate_result_filename: str: filename of csv with intermediate results.
                                               If None f'{directory}_{_from}-{to}_intermediate.csv'
            result_trace_filename: str: filename of csv with resulting trace.
                                               If None - f'{directory}_{_from}-{to}_trace.csv'
            ingress_nodes: list: only this nodes in resulting trace. If None - all nodes will appear in the trace.
                                 Applied in function process_df.
        """
        self.source = source
        self._from = _from
        self.to = to
        self._lock = threading.Lock()
        if result_trace_filename:
            self.result_trace_filename = result_trace_filename
        else:
            self.result_trace_filename = f'{source}_{_from}-{to}_trace.csv'
        splitext = os.path.splitext(self.result_trace_filename)
        if not intermediate_result_filename:
            self.intermediate_result_filename = f'{source}_{_from}-{to}_intermediate.csv'
        else:
            self.intermediate_result_filename = intermediate_result_filename
        self.intermediate_result_df = pd.DataFrame({})
        self.old_trace = pd.DataFrame({})
        self.ingress_nodes = ingress_nodes
        self.scale_factor = scale_factor
        self.run_duration = run_duration
        self.change_rate = change_rate  # in runs
        self.squash_rate = squash_rate
        self.meta = {}
        self.meta_filename = splitext[0] + "_meta.yaml"
        self.lock_meta = threading.Lock()
        self.results_trace = None
        self.data_rate_sums = None
        self.data_rate_sums_filename = splitext[0] + "_data_rate_sums.csv"
        self.plot_figsize = plot_figsize
        if isinstance(node_name_map, dict):
            self.node_name_map = node_name_map
        elif isinstance(node_name_map, str):
            with open(node_name_map, "r") as f:
                self.node_name_map = yaml.load(f)

    def append_meta(self, meta):
        """
        Writes variable meta to a dictionary, which is meant be written to a yaml file, containing meta information of a
        trace.
        """
        self.lock_meta.acquire()
        for key, value in meta.items():
            if key in self.meta:
                if isinstance(self.meta[key], list):
                    self.meta[key].append(value)
                elif value != self.meta[key]:
                    self.meta[key] = [self.meta[key], value]
            else:
                self.meta[key] = value
        self.lock_meta.release()

    def read_one_file(self, path):
        """
        Reads relevant information from one xml file. Function meant for starting a new thread.
            Args:
                path: str: path to the file
            Also there is the object attribute self.node_name_map, which defines, what node names will look like and
            which nodes should be removed.

            Returns: None, stores it in self.intermediate_result_df
            Raises: None, Exceptions written to logging.info
        """
        try:
            tree = etree.parse(path)
            root = tree.getroot()

            namespaces = root.nsmap

            meta = {}
            for item in root.find("meta", namespaces):
                meta[etree.QName(item).localname] = item.text

            df = pd.DataFrame({})
            for item in root.find("demands", namespaces):
                if self.node_name_map:
                    node_name = self.node_name_map[item.find("source", namespaces).text]
                else:
                    node_name = item.find("source", namespaces).text
                if node_name:
                    demand_dict = {"time": meta["time"],
                                   "node": node_name,
                                   "demandValue": item.find("demandValue", namespaces).text}
                    df = df.append(demand_dict, ignore_index=True)

            self._lock.acquire()
            self.intermediate_result_df = self.intermediate_result_df.append(df)
            self._lock.release()

            self.append_meta(meta)
        except BaseException as e:
            logging.info(str(type(e)), str(e), str(path))

    def read_files_parallel(self):
        """
        Reads xml files from a given directory using os.listdir(self.source)[self._from:self.to]. Uses function
        read_one_file() to start threads for every file. Behavior defined by object attributes: self.directory,
        self._from, self.to, self.node_name_map.
        """
        files = list(map(lambda file: os.path.join(self.source, file), os.listdir(self.source)))
        files = list(filter(os.path.isfile, files))
        files.sort()
        logging.info(f"{str(len(files))}  files in directory")
        if self.to and self.to <= len(files):
            files = files[self._from:self.to]
            logging.info(f"Chosen files: os.listdir({self.source})[{str(self._from)}:{str(self.to)}]")
        elif self._from <= len(files):
            files = files[self._from:]
            logging.info(f"Chosen files: os.listdir({self.source})[{str(self._from)}:]")
        else:
            logging.info(f"Chosen files: os.listdir({self.source})[:]")

        logging.info(f"{str(len(files))}  files chosen in total")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            logging.info("Starting threads...")
            t0 = time.clock()
            executor.map(self.read_one_file, files)
            logging.info("Started")
            executor.shutdown(wait=True)
            t1 = time.clock() - t0
        logging.info(f"Elapsed time:  {t1}")

        self.intermediate_result_df = self.intermediate_result_df.sort_values("time", ascending=True)
        self.intermediate_result_df["demandValue"] = self.intermediate_result_df["demandValue"].astype(float)
        self.intermediate_result_df.to_csv(self.intermediate_result_filename, index=False)

        try:
            self.meta["time"].sort()
        except BaseException:
            pass
        with open(self.meta_filename, "w") as f:
            yaml.dump(self.meta, f)

    def process_intermediate(self):
        """
        Processes the df with the intermediate results. Applies the scale_factor and converts the data rate into
        inter_arrival_mean. Also the choice of ingress nodes (attribute self.ingress_nodes) is applied here and the time
        axis, which is defined by self.run_duration and self.change_rate is calculated.

        Trace is written to a csv file with the filename self.result_trace_filename.

        Returns dataframe with resulting trace
        """
        df = self.intermediate_result_df

        if self.ingress_nodes:
            mask = df["node"] == self.ingress_nodes[0]
            for ing in self.ingress_nodes[1:]:
                mask = np.logical_or(df["node"] == ing, mask)
            df = df[mask]

        df_sums = df.groupby(["time", "node"]).sum().reset_index()
        df_sums["demandValue"] = df_sums["demandValue"]*self.scale_factor
        self.data_rate_sums = df_sums
        self.data_rate_sums.to_csv(self.data_rate_sums_filename, index=False)
        if self.squash_rate != 1:
            df_sums = self.squash_sums()

        inter_arrival_mean = 1/(df_sums["demandValue"])
        groupby_time = df_sums.groupby(["time"])
        num_timesteps = len(groupby_time)
        arange = np.arange(0, num_timesteps*self.run_duration*self.change_rate, self.run_duration*self.change_rate)

        time_col = np.concatenate([np.array([i]*len(t[1]["node"])) for t, i in zip(groupby_time, arange)])
        df_sums["time"] = time_col
        df_sums["inter_arrival_mean"] = inter_arrival_mean
        df_sums = df_sums.drop(axis=1, labels=["demandValue"])

        self.results_trace = df_sums
        df_sums.to_csv(self.result_trace_filename, index=False)
        logging.info(f"Written to {self.result_trace_filename}. Last time step {df_sums['time'][df_sums['time'].size - 1]}")

        return df_sums

    def squash_sums(self):
        """
        Squashes traffic into a smaller time period
        :return:
        DataFrame with new trace
        """
        df = pd.DataFrame()
        time_steps = list(self.data_rate_sums.groupby(["time"]).groups.keys())
        time_steps.sort()
        time_steps = [time_steps[i:i+self.squash_rate] for i in range(0, len(time_steps), self.squash_rate)]
        for _time_steps in time_steps:
            masks = [self.data_rate_sums["time"] == t for t in _time_steps]
            mask = masks[0]
            for m in masks[1:]:
                mask = np.logical_or(m, mask)
            _df = self.data_rate_sums[mask]
            _df = _df.groupby(["node"]).sum().reset_index()
            _df["time"] = [_time_steps[0]]*_df.shape[0]
            _df["demandValue"] = _df["demandValue"]/self.squash_rate
            df = df.append(_df)
        df = df.reset_index()
        df = df.drop(axis=1, labels=["index"])
        self.data_rate_sums = df
        return df

    def slice_intermediate(self):
        """
        Slices the intermediate DataFrame, applying self._from and self.to.
        :return:
        None
        DataFrame written to self.intermediate_result_df
        """
        groupby = self.intermediate_result_df.groupby(["time"])
        groups = list(groupby.groups.keys())
        groups.sort()

        if self.to and self.to <= len(groups):
            logging.info(f"Chosen trace part: trace[{str(self._from)}:{str(self.to)}]")
            groups = groups[self._from:self.to]
        elif self._from <= len(groups):
            logging.info(f"Chosen trace part: trace[{str(self._from)}:]")
            groups = groups[self._from:]
        else:
            logging.info(f"Chosen trace part: trace[:]")

        self.intermediate_result_df = pd.concat([groupby.get_group(group) for group in groups])

    def plot_data_rate(self):
        """
        Plots data rates from self.intermediate_result_df for all ingress nodes.
        """
        fig, ax = plt.subplots(figsize=self.plot_figsize)
        if self.ingress_nodes:  # filter in ingress nodes
            ingress_nodes = filter(lambda node: node[0] in self.ingress_nodes,
                                   self.data_rate_sums.groupby(["node"]))
        else:  # use all ingress nodes
            ingress_nodes = self.data_rate_sums.groupby(["node"])

        for ing in ingress_nodes:  # # x axis - range(0, last_time_step, time_step_size)
            ax.plot(range(0, len(list(ing[1]["time"])*self.run_duration*self.change_rate),  # x axis
                          self.run_duration*self.change_rate),  # x axis time_step_size
                    ing[1]["demandValue"],  # y axis
                    label=ing[0])

        ax.set_xlabel("Time")
        ax.set_ylabel("demandValue (Data Rate)")
        ax.set_title(f"{str(self.ingress_nodes)}", fontsize=30)
        plt.legend()
        return fig, ax

    def plot_inter_arrival_mean(self):
        """
        Plots inter_arrival_mean from self.results_trace for all ingress nodes.
        """
        fig, ax = plt.subplots(figsize=self.plot_figsize)
        for ing in self.results_trace.groupby(["node"]):
            ax.plot(ing[1]["time"], ing[1]["inter_arrival_mean"], label=ing[0])
            ax.set_xlabel("Time")
            ax.set_ylabel("inter_arrival_mean")

        ax.set_title(f"{str(self.ingress_nodes)}", fontsize=30)
        fig.legend()
        return fig, ax


def main(config_file, **kwargs):
    """
    Main function.
        Args:
            config_file: dict or str(path to a yaml)
            kwargs: possible args: {plot: [data_rate, inter_arrival_mean], save_plots: [data_rate, inter_arrival_mean]}
        Returns dataframe with resulting trace
    """
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

    if isinstance(config_file, dict):
        config = config_file
    elif config_file:
        with open(config_file, "r") as f:
            config = yaml.load(f)
    else:
        config = {}

    reader = TraceXMLReader(**config)

    df_result = None
    if os.path.isdir(reader.source):
        logging.info("Process directory")
        reader.read_files_parallel()
        reader.source = reader.intermediate_result_filename
    if os.path.isfile(reader.source):
        logging.info("Process intermediate csv")
        reader.intermediate_result_df = pd.read_csv(reader.source)
        logging.info("loaded intermediate csv")
        reader.slice_intermediate()
        df_result = reader.process_intermediate()

    logging.info("\n" + str(df_result))
    logging.info(f'inter_arrival_mean range: {min(df_result["inter_arrival_mean"])}, {max(df_result["inter_arrival_mean"])}')
    logging.info(f'... mean:  {df_result["inter_arrival_mean"].mean()}')
    logging.info(f'... median:  {df_result["inter_arrival_mean"].median()}')
    logging.info(f'... std:  {df_result["inter_arrival_mean"].std()}')

    if kwargs.get("plot", None) or kwargs.get("save_plots", None):
        if not reader.intermediate_result_df.empty:
            fig, ax = reader.plot_data_rate()
            if 'data_rate' in kwargs.get("save_plots", None):
                plot_filename = f"""{os.path.splitext(reader.result_trace_filename)[0]}_data_rate.{
                    kwargs.get('plot_format', 'png')}"""
                fig.savefig(plot_filename)
                logging.info(f"""Saved plot: {plot_filename}""")
            if 'data_rate' in kwargs.get("plot"):
                plt.show()

            plt.close()

        fig, ax = reader.plot_inter_arrival_mean()
        if 'inter_arrival_mean' in kwargs.get("save_plots", []):
            plot_filename = f"""{os.path.splitext(reader.result_trace_filename)[0]}_inter_arrival_mean.{
                kwargs.get('plot_format', 'png')}"""
            fig.savefig(plot_filename)
            logging.info(f"""Saved plot: {plot_filename}""")
        if 'inter_arrival_mean' in kwargs.get("plot", []):
            plt.show()

        plt.close()

    return df_result


def parse_args(args=None):
    parser = ArgumentParser()

    parser.add_argument("--config-file", help="Path to config_file")
    parser.add_argument("--plot", default=[], choices=['data_rate', 'inter_arrival_mean'], nargs='*',
                        help="Plot data_rate or inter_arrival_mean and call plt.show() in the end.")
    parser.add_argument("--save-plots", default=[], choices=['data_rate', 'inter_arrival_mean'], nargs='*',
                        help="Saves plots inter_arrival_mean in the end.")
    parser.add_argument("--plot-format", default='png', choices=['pdf', 'png'], help="Plot format to save")
    return vars(parser.parse_args(args))


if __name__ == "__main__":
    args = parse_args()
    print(args)
    df_result = main(**args)
