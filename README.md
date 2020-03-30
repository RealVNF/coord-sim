[![Build Status](https://travis-ci.com/RealVNF/coord-sim.svg?branch=master)](https://travis-ci.com/RealVNF/coord-sim)

# Simulation: Coordination of chained virtual network functions

Simulate flow-level, inter-node network coordination including scaling and placement of services and scheduling/balancing traffic between them.

<p align="center">
    <img src="docs/realvnf_logo.png" height="150" hspace="30"/>
  <img src="docs/upb.png" width="200" hspace="30"/>
  <img src="docs/huawei_horizontal.png" width="250" hspace="30"/>
</p>


## Citing this work

If you are using this work in whole or in part in your project, please cite it as follows: 

```
@inproceedings{schneider2020coordination,
	author = {Schneider, Stefan and Khalili, Ramin and Manzoor, Adnan and Qarawlus, Haydar and Uthe, Sven and Karl, Holger and Hecker, Artur},
	booktitle = {ACM SIGCOMM NetAI Workshop 2020 (SIGCOMM NetAI ’20)},
	pages = {1--8},
	title = {Self-Driving Coordination of Massively Scaled Services Using Deep Reinforcement Learning},
	year = {2020},
	note = {under review}
}
```

**Features**:

* Simulate any given network topology with arbitrary node and link capacities and link delays
* Simulatie any given network service consisting of linearly chained SFs/VNFs
* VNFs can specify arbitrary resource consumption as function of their load using Python modules. Also VNF delay can be specified individually and may be normally distributed.
* Simulate network traffic in the form of flow arrivals at various ingress nodes with varying arrival rate, flow length, volume, etc according to stochastic distributions
* Simple and clear interface to run algorithms for scaling, placement, and scheduling/load balancing of these incoming flows across the nodes in the network. Coordination within each node is out of scope.
* Interface allows easy integration with OpenAI Gym to enable training and evaluating reinforcement learning algorithms
* Collection of metrics like successful/dropped flows, end-to-end delay, resource consumption, etc over time. Easily extensible.
* Discrete event simulation to evaluate coordination over time with SimPy
* Gracefull adjustment of placements: When VNFs are removed from a placement by an algorithm. Currently processing flows are allowed to finish processing before the VNF is completely removed (see PR [#78](https://github.com/RealVNF/coordination-simulation/pull/78) and [#81](https://github.com/RealVNF/coordination-simulation/pull/81)).


## Setup

Requires Python 3.6. Install with (ideally using [virtualenv](https://virtualenv.pypa.io/en/stable/)):

```bash
pip install -r requirements.txt
```


## Usage

Type `coord-sim -h` for help using the simulator. For now, this should print 

``` 
$ coord-sim -h
usage: coord-sim [-h] -d DURATION -sf SF [-sfr SFR] -n NETWORK -c CONFIG
                 [-t TRACE] [-s SEED]

Coordination-Simulation tool

optional arguments:
  -h, --help            show this help message and exit
  -d DURATION, --duration DURATION
                        The duration of the simulation (simulates
                        milliseconds).
  -sf SF, --sf SF       VNF file which contains the SFCs and their respective
                        SFs and their properties.
  -sfr SFR, --sfr SFR   Path which contains the SF resource consumption
                        functions.
  -n NETWORK, --network NETWORK
                        The GraphML network file that specifies the nodes and
                        edges of the network.
  -c CONFIG, --config CONFIG
                        Path to the simulator config file.
  -t TRACE, --trace TRACE
                        Provide a CSV trace file to configure the traffic the
                        simulator is generating.
  -s SEED, --seed SEED  Random seed
```

You can use the following command as an example (run from the root project folder)

```bash 
coord-sim -d 20 -n params/networks/triangle.graphml -sf params/services/abc.yaml -sfr params/services/resource_functions -c params/config/sim_config.yaml
```
This will run a simulation on a provided GraphML network file and a YAML placement file for a duration of 20 timesteps.


### Dynamic SF resource consumption

By default, all SFs have a node resource consumption, which exactly equals the aggregated traffic that they have to handle.

It is possible to specify arbitrary other resource consumption models simply by implementing a python module with a 
function `resource_function(load)` (see examples [here](https://github.com/RealVNF/coordination-simulation/tree/master/params/services/resource_functions)).

To use these modules, they need to be referenced in the service file:

```
sf_list:
  a:
    processing_delay_mean: 5.0
    processing_delay_stdev: 0.0
    resource_function_id: A
```

And the path to the folder with the Python modules needs to be passed via the `-sfr` argument.

See PR https://github.com/RealVNF/coordination-simulation/pull/78 for details.


## Tests

```bash
# style check
flake8 src

# tests
nose2
```

## Acknowledgement

This project has received funding from German Federal Ministry of Education and Research ([BMBF](https://www.bmbf.de/)) through Software Campus grant 01IS17046 ([RealVNF](https://realvnf.github.io/)).

<p align="center">
  <img src="docs/software_campus.png" width="200"/>
  <img src="docs/BMBF_sponsored_by.jpg" width="250"/>
</p>
