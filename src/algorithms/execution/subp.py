import subprocess
from timeit import default_timer as timer
from datetime import timedelta

def main():
	scenarios = ['llc', 'lnc', 'hc']
	runs = 1
	networks = ['net_x', '../../../params/networks/dfn_58.graphml', '../../../params/networks/intellifiber_73.graphml']
	ingress = ['0.1', '0.15', '0.2', '0.25', '0.3', '0.35', '0.4', '0.45', '0.5']
	algos = ['g1', 'spr1', 'spr2']

	start = timer()
	for s in scenarios:
		for r in range(runs):
			for net in networks:
				for ing in ingress:
					processes = []
					for a in algos:
						processes.append(subprocess.Popen(['python', "runner.py", s, str(r), net, ing, a]))
					for p in processes:
						p.wait()
	end = timer()
	print(timedelta(seconds=end - start))


if __name__ == "__main__":
	main()