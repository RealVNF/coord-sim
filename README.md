[![Build Status](https://travis-ci.com/RealVNF/coordination-simulation.svg?token=LHEsk5x5tv7SsiZCzuoZ&branch=master)](https://travis-ci.com/RealVNF/coordination-simulation)

# Simulation: Coordination of chained virtual network functions

Simulate flow-level, inter-node network coordination including scaling and placement of services and scheduling/balancing traffic between them.


**Goal**:

* Simulate any given network topology with node and link capacities using NetworkX
* Simulate network traffic in the form of flow arrivals at various ingress nodes with varying arrival rate, flow length, volume, etc
* Run algorithms for scaling, placement, and scheduling/load balancing of these incoming flows across the nodes in the network. Coordination within each node is out of scope (e.g., handled by Kubernetes).
* Discrete event simulation to evaluate coordination over time with SimPy
* Integration with OpenAI Gym to allow training and evaluating reinforcement learning algorithms


## Setup

Requires Python 3.6. Install with (ideally using [virtualenv](https://virtualenv.pypa.io/en/stable/)):

```bash
python setup.py install
```


## Usage

Type `coord-sim -h` for help using the simulator. For now, this should print 

``` 
$ coord-sim -h
usage: coord-sim [-h] -d DURATION -sf SF -n NETWORK [-s SEED]
                 [-iam INTER_ARR_MEAN] [-fdm FLOW_DR_MEAN]
                 [-fds FLOW_DR_STDEV] [-fss FLOW_SIZE_SHAPE]

Coordination-Simulation tool

optional arguments:
  -h, --help            show this help message and exit
  -d DURATION, --duration DURATION
                        The duration of the simulation (simulates
                        milliseconds).
  -sf SF, --sf SF       VNF file which contains the SFCs and their respective
                        SFs and their properties.
  -n NETWORK, --network NETWORK
                        The GraphML network file that specifies the nodes and
                        edges of the network.
  -s SEED, --seed SEED  The seed to use for the random number generator.
  -iam INTER_ARR_MEAN, --inter_arr_mean INTER_ARR_MEAN
                        Inter arrival mean of the flows' arrival at ingress
                        nodes.
  -fdm FLOW_DR_MEAN, --flow_dr_mean FLOW_DR_MEAN
                        The mean value for the generation of data rate values
                        for each flow.
  -fds FLOW_DR_STDEV, --flow_dr_stdev FLOW_DR_STDEV
                        The standard deviation value for the generation of
                        data rate values for each flow.
  -fss FLOW_SIZE_SHAPE, --flow_size_shape FLOW_SIZE_SHAPE
                        The shape of the Pareto distribution for the
                        generation of the flow size values.
```

You can use the following command as an example (run from the root project folder)

```bash 
coord-sim -d 20 -n params/networks/Abilene.graphml -sf params/placements/Abilene.yaml 
```
This will run a simulation on a provided GraphML network file and a YAML placement file for a duration of 20 timesteps. 


## Tests

```bash
# style check
flake8 src

# tests
nose2
```
