import subprocess
import sys
import time
from timeit import default_timer as timer
from datetime import timedelta


def main():
	runs = [sys.argv[1]]
	config = [sys.argv[2]]
	pparallel = int(sys.argv[3])
	poll_pause = int(sys.argv[4])

	networks = ['../../../../params/networks/gts_ce_149.graphml']
	algos = ['gpasp', 'spr1', 'spr2']

	start = timer()
	running_processes = []
	for c in config:
		for r in runs:
			for net in networks:
				for a in algos:
					running_processes.append(subprocess.Popen(['python', 'iteration_runner.py', c, r, net, a]))
					print(f'Start: {c}-{r}-{net}-{a}')
					while len(running_processes) == pparallel:
						unfinished_processes = []
						for p in running_processes:
							if p.poll() is None:
								# process has NOT terminated
								unfinished_processes.append(p)
						if len(unfinished_processes) == len(running_processes):
							time.sleep(poll_pause)
						else:
							running_processes = unfinished_processes
	for p in running_processes:
		p.wait()
	end = timer()
	print(timedelta(seconds=(end - start)))


if __name__ == "__main__":
	main()