# Simulation: Coordination of chained virtual network functions

Simulate flow-level, inter-node network coordination including scaling and placement of services and routing flows between them. Note: this repository holds an altered version of the original simulator [coord-sim](https://github.com/RealVNF/coordination-simulation), adapted to my needs in order to accomplish my bachelor thesis.


**Additional features**:

* Forwarding capabilities. Prior to this, forwarding happened implicit. Now flows are explicit forwarded over link, taking into account individual link utilization
* Individual flow forwarding rules. A node can make a forwarding decision on individual flows.
* Individual flow processing rules. A node can explicit decide if it will process a flow.
* Extended simulator state and action interface.
* Algorithm callback interface. To allow a external algorithm to capture certain event, it can register callback functions invoked by the flowsimulator.
* Adapted metrics.


## Setup

Requires Python 3.6. Install with [virtualenv](https://virtualenv.pypa.io/en/stable/) to not break original coord-sim installation. Make sure to install simulator with adapted source files, located on the `adapted` branch:
```bash
git checkout adapted
```

Then follow original setup procedure:
```bash
pip install -r requirements.txt
```
