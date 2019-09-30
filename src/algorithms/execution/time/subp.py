import subprocess
from timeit import default_timer as timer
from datetime import timedelta

def main():
	config = ['c1']
	runs = ['0']
	networks = ['../../../../params/networks/dfn_58.graphml']
	algos = ['gpasp', 'spr1', 'spr2']

	start = timer()
	for c in config:
		for r in runs:
			for net in networks:
				processes = []
				for a in algos:
					processes.append(subprocess.Popen(['python', "runner.py", c, r, net, a]))
				for p in processes:
					p.wait()
	end = timer()
	print(timedelta(seconds=end - start))


if __name__ == "__main__":
	main()