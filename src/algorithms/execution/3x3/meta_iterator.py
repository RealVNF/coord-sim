import sys
import subprocess


def chunkit(runs, chunk_size):
    chunks = []
    size = 0
    chunk = []
    for r in runs:
        chunk.append(r)
        size += 1
        if size >= chunk_size:
            chunks.append(chunk)
            size = 0
            chunk = []
    if len(chunk) > 0:
        chunks.append(chunk)
    return chunks


def main():
    start = int(sys.argv[1])
    end = int(sys.argv[2]) + 1
    chunk_size = int(sys.argv[3])
    pparallel = sys.argv[4]
    poll_pause = sys.argv[5]

    runs = [str(x) for x in range(start, end)]
    sequential_instances = chunkit(runs, chunk_size)

    for sr in sequential_instances:
        processes = []
        for r in sr:
            processes.append(subprocess.Popen(['python', 'iterator.py', r, pparallel, poll_pause]))
            print(f'{r}')
        for p in processes:
            p.wait()


if __name__ == "__main__":
    main()