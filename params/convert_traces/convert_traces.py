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

    def __init__(self, directory, _from=0, to=None, scale_factor=0.001, run_duration=100, change_rate=2,
                 node_name_map=node_map_abilene, intermediate_result_filename=None, result_trace_filename=None,
                 ingress_nodes=None, *args, **kwargs):
        self.directory = directory
        self._from = _from
        self.to = to
        self._lock = threading.Lock()
        if not result_trace_filename:
            self.result_trace_filename = result_trace_filename
        else:
            self.result_trace_filename = f'{directory}_{_from}-{to}_trace.csv'
        splitext = os.path.splitext(self.result_trace_filename)
        if not intermediate_result_filename:
            self.intermediate_result_filename = splitext[0] + "_intermediate" + splitext[1]
        else:
            self.intermediate_result_filename = intermediate_result_filename
        self.intermediate_result_df = pd.DataFrame({})
        self.ingress_nodes = ingress_nodes
        self.scale_factor = scale_factor
        self.run_duration = run_duration
        self.change_rate = change_rate  # in runs
        self.meta = {}
        self.meta_filename = splitext[0] + "_meta.yaml"
        self.lock_meta = threading.Lock()
        self.results_trace = None
        if isinstance(node_name_map, dict):
            self.node_name_map = node_name_map
        elif isinstance(node_name_map, str):
            with open(node_name_map, "r") as f:
                self.node_name_map = yaml.load(f)

    def append_meta(self, meta):
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
        files = list(map(lambda file: os.path.join(self.directory, file), os.listdir(self.directory)))
        files = list(filter(os.path.isfile, files))
        logging.info(f"{str(len(files))}  files in directory")
        if self.to and self.to <= len(files):
            files = files[self._from:self.to]
            logging.info(f"Chosen files: os.listdir({self.directory})[{str(self._from)}:{str(self.to)}]")
        elif self._from <= len(files):
            files = files[self._from:]
            logging.info(f"Chosen files: os.listdir({self.directory})[{str(self._from)}:]")
        else:
            logging.info(f"Chosen files: os.listdir({self.directory})[:]")

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

    def process_df(self):
        # 2 runs == 5min
        df = self.intermediate_result_df

        if self.ingress_nodes:
            mask = df["node"] == self.ingress_nodes[0]
            for ing in self.ingress_nodes[1:]:
                mask = np.logical_or(df["node"] == ing, mask)
                df = df[mask]

        df_sums = df.groupby(["time", "node"]).sum().reset_index()

        inter_arrival_mean = 1/(df_sums["demandValue"]*self.scale_factor)
        groupby_time = df_sums.groupby(["time"])
        num_timesteps = len(groupby_time)
        num_ingress = groupby_time.count()["node"][0]
        time_col = np.concatenate([np.array([t]*num_ingress)
                                   for t in np.arange(0,
                                                      num_timesteps*self.run_duration*self.change_rate,
                                                      self.run_duration*self.change_rate)])
        df_sums["time"] = time_col
        df_sums["inter_arrival_mean"] = inter_arrival_mean
        df_sums = df_sums.drop(axis=1, labels=["demandValue"])

        self.results_trace = df_sums
        df_sums.to_csv(self.result_trace_filename, index=False)
        logging.info(f"Written to {self.result_trace_filename}. Last time step {df_sums['time'][df_sums['time'].size - 1]}")

        return df_sums


def main(config_file=None, only_process=False, **kwargs):
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

    if not only_process:
        reader.read_files_parallel()
    else:
        reader.intermediate_result_df = pd.read_csv(reader.intermediate_result_filename)

    df_result = reader.process_df()
    logging.info("\n" + str(df_result))
    logging.info(f'inter_arrival_mean range:{min(df_result["inter_arrival_mean"])}, {max(df_result["inter_arrival_mean"])}')
    logging.info(f'... mean:  {df_result["inter_arrival_mean"].mean()}')
    logging.info(f'... median:  {df_result["inter_arrival_mean"].median()}')
    logging.info(f'... std:  {df_result["inter_arrival_mean"].std()}')

    return df_result


def parse_args(args=None):
    parser = ArgumentParser()

    parser.add_argument("config_file", help="Path to config_file")
    parser.add_argument("--only-process", default=False, action="store_true", help="Reuse and intermediate.csv")
    parser.add_argument("--plot", default=False, action="store_true", help="Plot inter_arrival_mean in the end.")
    return vars(parser.parse_args(args))


if __name__ == "__main__":
    args = parse_args()
    df_result = main(**args)

    if args["plot"]:
        plt.figure()
        for ing in df_result.groupby(["node"]):
            plt.plot(ing[1]["time"], ing[1]["inter_arrival_mean"], label=ing[0])
            plt.xlabel("Time")
            plt.ylabel("inter_arrival_mean")
        plt.legend()
        plt.show()
