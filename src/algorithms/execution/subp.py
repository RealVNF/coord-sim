import subprocess

def main():
	scenarios = ['llc', 'lnc', 'hc']
	run = 1
	network = ['../../../params/networks/dfn_58.graphml', '../../../params/networks/intellifiber_73.graphml']
	ingress = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]
	algo = ['g1, spr1, spr2']

	for s in scenarios:
		for r in range(run):
			for net in network:
				for ing in ingress:
					processes = []
					for a in algo:
						processes.append(subprocess.Popen(['python', "runner.py", s, r, net, ing, a]))
					for p in processes:
						p.wait()


if __name__ == "__main__":
	main()