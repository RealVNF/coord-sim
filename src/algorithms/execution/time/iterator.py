import subprocess
import sys
from timeit import default_timer as timer
from datetime import timedelta


def main():
	runs = [sys.argv[1]]
	config = [sys.argv[2]]
	networks = ['../../../../params/networks/gts_ce_149.graphml']
	algos = ['gpasp', 'spr1', 'spr2']

	start = timer()
	for c in config:
		for r in runs:
			for net in networks:
				processes = []
				for a in algos:
					processes.append(subprocess.Popen(['python', 'iteration_runner.py', c, r, net, a]))
				for p in processes:
					p.wait()
	end = timer()
	print(timedelta(seconds=(end - start)))


if __name__ == "__main__":
	main()