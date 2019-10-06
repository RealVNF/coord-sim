import subprocess


def main():
    runs = ['0', '1', '2']

    processes = []
    for r in runs:
        processes.append(subprocess.Popen(['python', 'iterator.py', r]))
    for p in processes:
        p.wait()


if __name__ == "__main__":
    main()