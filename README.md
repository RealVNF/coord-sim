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
usage: coord-sim [-h] -d DURATION [-r RATE] [-s SEED] -n NETWORK
                 [-rm RAND_MEAN]

Coordination-Simulation tool

optional arguments:
  -h, --help            show this help message and exit
  -d DURATION, --duration DURATION
  -r RATE, --rate RATE
  -s SEED, --seed SEED
  -n NETWORK, --network NETWORK
  -rm RAND_MEAN, --randmean RAND_MEAN
```

You can use the following command as an example (run from the root project folder)

```bash 
coord-sim -d 20 -n params/networks/Abilene.graphml -p params/placements/Abilene.yaml 
```
This will run a simulation on a provided GraphML file for a duration of 20 timesteps. 

## Tests

## Development
