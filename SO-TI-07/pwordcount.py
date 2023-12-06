import sys
import argparse
from multiprocessing import Process, Lock, Event, Manager, Value, Queue
import os
import signal
import time
from datetime import datetime

def special_cleaner(unclean_words):
    special_chars = '!@#$%^&*()_+[]{}|;:,.<>?/\\"~†–'
    clean_words = [word.translate(str.maketrans('', '', special_chars)).lower() for word in unclean_words if word.strip()]
    return [word for word in clean_words if word not in ['', '-']]

def count_lines(file):
    with open(file, 'r') as f:
        return sum(1 for line in f)

def file_divider(file, n, n_now):
    with open(file, 'r') as file:
        words = special_cleaner(file.read().split())
    start_idx = int((n_now - 1) * len(words) / n)
    end_idx = int(n_now * len(words) / n)
    return words[start_idx:end_idx]

def word_counter(file, n, n_now, shared_data, result_queue):
    words = file_divider(file, n, n_now)
    result_queue.put(('word_counter', len(words), f"Total de {len(words)} palavras entre as linhas {int((n_now-1)*count_lines(file)/n)} e {int(n_now*count_lines(file)/n)} de {file}"))

def unique_word_counter(file, n, n_now, shared_data, result_queue):
    words = file_divider(file, n, n_now)
    unique_words = set(words)
    result_queue.put(('unique_word_counter', len(unique_words), f"{len(unique_words)} palavras únicas entre as linhas {int((n_now-1)*count_lines(file)/n)} e {int(n_now*count_lines(file)/n)} de {file}"))

def occurrence_counter(file, n, n_now, shared_data, result_queue):
    words = file_divider(file, n, n_now)
    word_count = {}
    for word in words:
        word_count[word] = word_count.get(word, 0) + 1

    results = []
    for word, count in word_count.items():
        results.append((word, count))

    result_queue.put(('occurrence_counter', results, f"Ocorrências de Palavras Únicas/Diferentes entre as linhas {int((n_now-1)*count_lines(file)/n)} e {int(n_now*count_lines(file)/n)} de {file}"))

def worker(start_idx, end_idx, pid, n, n_now, input_files, mode, shared_data, result_queue):
    for idx in range(start_idx, end_idx):
        file = input_files[idx]
        if end_idx - start_idx == 1:
            print(f"Process {pid} is working on the file {file}")
        else:
            print(f"Process {pid} is working on files {input_files[start_idx]} to {input_files[end_idx - 1]}")

        if mode == "t":
            word_counter(file, n, n_now, shared_data, result_queue)
        elif mode == "u":
            unique_word_counter(file, n, n_now, shared_data, result_queue)
        elif mode == "o":
            occurrence_counter(file, n, n_now, shared_data, result_queue)

def diveconquer(input_files, mode, parallel, interval, log_file=None):
    manager = Manager()
    shared_data = manager.dict()
    result_queue = manager.Queue()

    num_files = len(input_files)
    num_processes = min(parallel, num_files)

    processes = []
    for i in range(num_processes):
        start_idx = i * (num_files // num_processes)
        end_idx = (i + 1) * (num_files // num_processes) if i < num_processes - 1 else num_files
        pid = os.fork()

        if pid == 0:
            worker(start_idx, end_idx, os.getpid(), 1, 1, input_files, mode, shared_data, result_queue)
            os._exit(0)
        else:
            processes.append(pid)

    signal.signal(signal.SIGINT, lambda signum, frame: signal_handler(signum, frame, processes))

    for pid in processes:
        os.waitpid(pid, 0)

    print_aggregated_results(result_queue)

    if interval > 0:
        start_time = time.time()
        while True:
            time.sleep(interval)
            elapsed_time = time.time() - start_time
            print_partial_results(result_queue)
            if elapsed_time >= interval:
                break

    if log_file:
        with open(log_file, 'a') as log:
            log.write(f"\nResults at {datetime.now()}:")
            print_aggregated_results(result_queue)

def signal_handler(signum, frame, processes):
    print("\nReceived SIGINT. Waiting for child processes to finish...")
    for pid in processes:
        os.kill(pid, signal.SIGTERM)
    sys.exit(0)

def print_partial_results(result_queue):
    while not result_queue.empty():
        result_type, result_data, message = result_queue.get()
        print(f"{message}:", result_data)

def print_aggregated_results(result_queue):
    results = {}
    while not result_queue.empty():
        result_type, result_data, message = result_queue.get()
        results[result_type] = results.get(result_type, []) + [(result_data, message)]

    print("\nAggregated Results:")
    for result_type, result_list in results.items():
        print(f"{result_type.capitalize()} Results:")
        for result_data, message in result_list:
            print(f"{message}: {result_data}")
        print()
    
def parse_arguments():
    parser = argparse.ArgumentParser(description="Tool for Processing Arguments")
    parser.add_argument("input_files", nargs='+', help="Input files")
    parser.add_argument(
        "-m",
        dest="mode",
        choices=["t", "u", "o"],
        default="t",
        help="Define the execution mode. Allowed values: 't' (total), 'u' (unique), 'o' (occurrence)"
    )
    parser.add_argument("-p", dest="parallel", type=int, default=0, help="Define the level of parallelization")
    parser.add_argument("-i", dest="interval", type=int, default=0, help="Interval for periodic printing")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    diveconquer(args.input_files, args.mode, args.parallel, args.interval, log_file=None)
