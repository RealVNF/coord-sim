import subprocess


def main():
    v = 'link_weight'
    runs = ['0', '1', '2']

    processes = []
    for r in runs:
        processes.append(subprocess.Popen(['python', 'iterator.py', v, r]))
    for p in processes:
        p.wait()


if __name__ == "__main__":
    main()