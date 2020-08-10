import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from keras.models import Sequential, load_model
from keras.layers import Dense
from keras.layers import LSTM
from coordsim.reader import reader
import numpy as np
import random
from pickle import load, dump
import os
import argparse


class LSTM_Predictor:
    """
    Traffic prediction module based on LSTM neural networks
    NOTICE: Only works with Poisson arrival and trace based scenarios with single ingress node
    Based on work done here:
    https://machinelearningmastery.com/time-series-forecasting-long-short-term-memory-network-python/
    """
    def __init__(self, trace, params, training_repeats=10, nb_epochs=10,
                 weights_dir=False, poisson_data=False):
        """
        Initiate the class
        PARAMETERS:
        ----------
        trace: list: The traffic trace from the simulator. Will be used to generated training data.
        params: SimulatorParams: the simulator parameters class
        training_repeats: int: Number of repetitions for the training process.
        nb_epochs: int: the number of epochs to train the neural network in each repetition.
        run_duration: the simulator interface's run duration.
        weights_dir: path to weights dir. Set to false when training
        poisson: set to True to generate training data randomly based on Poisson process, not the arrival mean
        """
        # Store arguments
        self.trace = trace
        self.params = params
        self.training_repeats = training_repeats
        self.nb_epochs = nb_epochs
        self.run_duration = self.params.run_duration
        self.weights_dir = weights_dir
        if weights_dir:
            self.weights_dir = os.path.join(os.getcwd(), weights_dir)
        self.poisson_data = poisson_data

        self.requested_traffic = []  # empty array that will hold training data for the LSTM NN
        self.training_data = None  # Placeholder for pandas DataFrame to hold training data
        self.predictions = []
        self.last_prediction_index = 0  # Index to keep track of position in testing data

        self.gen_training_data()
        self.prepare_model()

    def gen_training_data(self):
        self.reset_flow_lists()
        for i in range(len(self.trace)):
            cur_time = float(self.trace[i]['time'])
            inter_arr_mean = float(self.trace[i]['inter_arrival_mean'])
            if i < len(self.trace) - 1:
                # Check for multiple runs with the same mean
                while cur_time < float(self.trace[i+1]['time']):
                    self.gen_run_data(cur_time, inter_arr_mean)
                    cur_time += self.run_duration
            else:
                # gen data for the last run in the trace
                # this carries the limitation that the last entry in the trace should represent the last run
                self.gen_run_data(cur_time, inter_arr_mean)
        self.training_data = pd.DataFrame(self.requested_traffic, columns=['requested_data_rate'])

    def prepare_model(self):
        """
        Prepare training and testing data
        """
        # transform data to be stationary
        self.raw_values = self.training_data.values
        self.diff_values = self.difference(self.raw_values, 1)

        # transform data to be supervised learning
        supervised = self.timeseries_to_supervised(self.diff_values, 1)
        supervised_values = supervised.values

        # split data into train and test-sets
        # data_len = len(supervised_values)
        # split_train_test = np.ceil(0.75 * data_len)
        # train, test = supervised_values[0:split_train_test], supervised_values[split_train_test:]

        # train and testing data are the same for now
        self.train, self.test = supervised_values[0:], supervised_values[0:]

        # transform the scale of the data
        self.scaler, self.train_scaled, self.test_scaled = self.scale(self.train, self.test)

        if self.weights_dir:
            self.model = load_model(f"{self.weights_dir}/lstm_model.mdl")
            self.prepare_prediction_model()

    def train_model(self):
        """
        Train the LSTM model
        """
        # fit the model
        self.fit_lstm(self.train_scaled, 1, self.nb_epochs, 4)

    def prepare_prediction_model(self):
        """
        Builds the state of the LSTM to allow for one-step predictions
        """
        # forecast the entire training dataset to build up state for forecasting
        train_reshaped = self.train_scaled[:, 0].reshape(len(self.train_scaled), 1, 1)
        self.model.predict(train_reshaped, batch_size=1)

    def predict_traffic(self):
        """
        Returns the predicted traffic rate for the next run
        """
        # make one-step forecast
        if self.last_prediction_index == len(self.test_scaled):
            X, y = self.test_scaled[self.last_prediction_index-1, 0:-1],
            self.test_scaled[self.last_prediction_index-1, -1]
            yhat = self.forecast_lstm(self.model, 1, np.array([y]))
            self.last_prediction_index -= 1
        else:
            X, y = self.test_scaled[self.last_prediction_index, 0:-1], self.test_scaled[self.last_prediction_index, -1]
            yhat = self.forecast_lstm(self.model, 1, X)
        # invert scaling
        yhat = self.invert_scale(self.scaler, X, yhat)
        # invert differencing
        yhat = self.inverse_difference(self.raw_values, yhat, len(self.test_scaled)+1-self.last_prediction_index)
        # store forecast
        self.predictions.append(yhat)
        self.last_prediction_index += 1
        return yhat[0]

    def reset_flow_lists(self):
        """Reset and re-init flow data lists and index. Called at the beginning of each new episode."""
        # list of generated inter-arrival times, flow sizes, and data rates for the entire episode
        # dict: ingress_id --> list of arrival times, sizes, drs
        self.flow_arrival_list = []
        self.flow_size_list = []
        self.flow_dr_list = []
        self.flow_list_idx = 0
        self.last_arrival_sum = 0

    def gen_run_data(self, now=0, inter_arr_mean=10):
        """
        Generate and append dicts of lists of flow arrival, size, dr for the run duration
        """
        if self.poisson_data:
            flow_arrival = []
            flow_sizes = []
            flow_drs = []
            # generate flows for time frame of num_steps
            run_end = now + self.run_duration
            # Check to see if next flow arrival is before end of run
            while self.last_arrival_sum < run_end:
                inter_arr_time = random.expovariate(lambd=1.0/inter_arr_mean)
                # Generate flow dr
                flow_dr = np.random.normal(self.params.flow_dr_mean, self.params.flow_dr_stdev)
                # generate flow sizes
                if self.params.deterministic_size:
                    flow_size = self.params.flow_size_shape
                else:
                    # heavy-tail flow size
                    flow_size = np.random.pareto(self.params.flow_size_shape) + 1
                # Skip flows with negative flow_dr or flow_size values
                if flow_dr < 0.00 or flow_size < 0.00:
                    continue

                flow_arrival.append(inter_arr_time)
                flow_sizes.append(flow_size)
                flow_drs.append(flow_dr)
                self.last_arrival_sum += inter_arr_time

            # append to existing flow list. it continues to grow across runs within an episode
            self.flow_arrival_list.extend(flow_arrival)
            self.flow_dr_list.extend(flow_drs)
            self.flow_size_list.extend(flow_sizes)
            self.generated_flows = flow_drs

            # append the sum of the requested data rate for this run to generate training data.
            self.requested_traffic.append(sum(flow_drs))
        else:
            # Generate avg flow_dr
            flow_drs = [
                np.random.normal(self.params.flow_dr_mean, self.params.flow_dr_stdev) for _ in range(self.run_duration)
                ]
            mean_flow_dr = np.mean(flow_drs)
            self.requested_traffic.append((self.run_duration / inter_arr_mean) * mean_flow_dr)

    # frame a sequence as a supervised learning problem
    def timeseries_to_supervised(self, data, lag=1):
        df = pd.DataFrame(data)
        columns = [df.shift(i) for i in range(1, lag+1)]
        columns.append(df)
        df = pd.concat(columns, axis=1)
        df.fillna(0, inplace=True)
        return df

    # create a differenced series
    def difference(self, dataset, interval=1):
        diff = list()
        for i in range(interval, len(dataset)):
            value = dataset[i] - dataset[i - interval]
            diff.append(value)
        return pd.Series(diff)

    # invert differenced value
    def inverse_difference(self, history, yhat, interval=1):
        return yhat + history[-interval]

    # scale train and test data to [-1, 1]
    def scale(self, train, test):
        if self.weights_dir:
            # load scaler from file
            scaler = load(open(f"{self.weights_dir}/scaler.pkl", "rb"))
        else:
            # create and fit scaler
            scaler = MinMaxScaler(feature_range=(-1, 1))
            scaler = scaler.fit(train)
        # transform train
        train = train.reshape(train.shape[0], train.shape[1])
        train_scaled = scaler.transform(train)
        # transform test
        test = test.reshape(test.shape[0], test.shape[1])
        test_scaled = scaler.transform(test)
        return scaler, train_scaled, test_scaled

    # inverse scaling for a forecasted value
    def invert_scale(self, scaler, X, value):
        new_row = [x for x in X] + [value]
        array = np.array(new_row)
        array = array.reshape(1, len(array))
        inverted = scaler.inverse_transform(array)
        return inverted[0, -1]

    # fit an LSTM network to training data
    def fit_lstm(self, train, batch_size, nb_epoch, neurons):
        X, y = train[:, 0:-1], train[:, -1]
        X = X.reshape(X.shape[0], 1, X.shape[1])
        self.model = Sequential()
        self.model.add(LSTM(neurons, batch_input_shape=(batch_size, X.shape[1], X.shape[2]), stateful=True))
        self.model.add(Dense(1))
        self.model.compile(loss='mean_squared_error', optimizer='adam')

        for i in range(nb_epoch):
            self.model.fit(X, y, epochs=1, batch_size=batch_size, verbose=0, shuffle=False)
            self.model.reset_states()

    # make a one-step forecast
    def forecast_lstm(self, model, batch_size, X):
        X = X.reshape(1, 1, len(X))
        yhat = model.predict(X, batch_size=batch_size)
        return yhat[0, 0]

    def save_model(self, dest_dir):
        dest_dir = os.path.join(os.getcwd(), dest_dir)
        os.makedirs(dest_dir, exist_ok=True)
        self.model.save(os.path.join(dest_dir, "lstm_model.mdl"))
        dump(self.scaler, open(os.path.join(dest_dir, "scaler.pkl"), "wb"))


class SimConfig:
    """
    Class to hold simulator config parameters similar to SimulatorParams class but more tailored for LSTM use.
    """
    def __init__(self, config):
        self.inter_arrival_mean = config['inter_arrival_mean']
        self.deterministic_arrival = config['deterministic_arrival']
        self.flow_dr_mean = config['flow_dr_mean']
        self.flow_dr_stdev = config['flow_dr_stdev']
        self.flow_size_shape = config['flow_size_shape']
        self.deterministic_size = config['deterministic_size']
        self.run_duration = int(config['run_duration'])


def main():
    # parse CLI args (when using simulator as stand-alone, not triggered through the interface)
    parser = argparse.ArgumentParser(description="Trainer tool for LSTM prediction for Coord-sim simulator")
    parser.add_argument('-c', '--config', required=True, dest="sim_config",
                        help="The simulator config file")
    args = parser.parse_args()

    print("Loading arguments")
    sim_config = reader.get_config(args.sim_config)
    trace = reader.get_trace(sim_config['trace_path'])
    dest_dir = sim_config['lstm_weights']
    params = SimConfig(sim_config)
    print(f"Loaded trace with {len(trace)} entries")

    predictor = LSTM_Predictor(trace, params)

    print("Training LSTM model")
    predictor.train_model()
    print(f"Saving model to {dest_dir}")
    predictor.save_model(dest_dir)

    del predictor

    print("Load weights to test prediction")
    predictor = LSTM_Predictor(trace, params=params, weights_dir=dest_dir)
    print(f"Prediction made from loading weights: {predictor.predict_traffic()}")

    print("Done with no errors!")


# predictor = LSTM_Predictor(trace, simparams)
if __name__ == "__main__":
    main()
