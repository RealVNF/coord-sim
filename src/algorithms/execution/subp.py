import subprocess
import sys

# some code here

config_1 = {
	'network': '../params/networks/dfn_58.graphml',
	'service_functions': '../params/services/3sfcs.yaml',
	'resource_functions': '../params/services/resource_functions',
	'config': '../params/config/probabilistic_discrete_config.yaml',
	'seed': 9999
}

pid = subprocess.Popen(['python', "runner.py", config_1['network']])


print('Hello')