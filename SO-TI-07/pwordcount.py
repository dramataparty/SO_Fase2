import sys
import argparse
from multiprocessing import Process, Lock, Event, Array
import os
import signal
import time
from datetime import datetime

class ProcessData:
    def __init__(self):
        self.lock = Lock()
        self.exit_event = Event()
        self.aggregated_results = Array('i', [0, 0, 0, 0, 0])
        self.elapsed_time = 0
        self.start_time = 0

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

def word_counter(file, n, n_now):
    words = file_divider(file, n, n_now)
    print(f"Total de {len(words)} palavras entre as linhas {int((n_now-1)*count_lines(file)/n)} "
          f"e {int(n_now*count_lines(file)/n)} de {file}")

def unique_word_counter(file, n, n_now):
    words = file_divider(file, n, n_now)
    unique_words = set(words)
    print(f"{len(unique_words)} palavras únicas entre as linhas {int((n_now-1)*count_lines(file)/n)} "
          f"e {int(n_now*count_lines(file)/n)} de {file}")

def occurrence_counter(file, n, n_now):
    words = file_divider(file, n, n_now)
    word_count = {}
    for word in words:
        word_count[word] = word_count.get(word, 0) + 1

    print(f"Ocorrências de Palavras Únicas/Diferentes entre as linhas "
          f"{int((n_now-1)*count_lines(file)/n)} e {int(n_now*count_lines(file)/n)} de {file}:")

    for word, count in word_count.items():
        print(f"{word}: {count}")

def worker(start_idx, end_idx, pid, n, n_now, input_files, mode):
    for idx in range(start_idx, end_idx):
        if exit_event.is_set():
            break

        file = input_files[idx]
        if end_idx - start_idx == 1:
            print(f"Process {pid} is working on the file {file}")
        else:
            print(f"Process {pid} is working on files {input_files[start_idx]} to {input_files[end_idx - 1]}")

        result = process_file(file, mode, n, n_now)

        with lock:
            aggregated_results[0] += result[0]
            aggregated_results[1] += result[1]
            aggregated_results[2] += result[2]
            aggregated_results[3] += result[3]
            aggregated_results[4] += result[4]

        print_partial_results()

def process_file(file, mode, n, n_now):
    if mode == "t":
        return word_counter(file, n, n_now)
    elif mode == "u":
        return unique_word_counter(file, n, n_now)
    elif mode == "o":
        return occurrence_counter(file, n, n_now)

def diveconquer(input_files, mode, parallel, interval, log_file):
    global lock, exit_event, aggregated_results, elapsed_time, start_time

    num_files = len(input_files)
    num_processes = min(parallel, num_files)

    if interval > 0:
        start_time = time.time()
        while True:
            time.sleep(interval)
            elapsed_time = time.time() - start_time
            print_partial_results()
            if elapsed_time >= interval:
                break

    processes = []
    for i in range(num_processes):
        if exit_event.is_set():
            break

        start_idx = i * (num_files // num_processes)
        end_idx = (i + 1) * (num_files // num_processes) if i < num_processes - 1 else num_files
        pid = os.fork()

        if pid == 0:
            worker(start_idx, end_idx, os.getpid(), 1, 1, input_files, mode)
            os._exit(0)
        else:
            processes.append(pid)

    signal.signal(signal.SIGINT, signal_handler)

    for pid in processes:
        os.waitpid(pid, 0)

    print_aggregated_results()

    if interval > 0:
        start_time = time.time()
        while True:
            time.sleep(interval)
            elapsed_time = time.time() - start_time
            print(f"\nResults after {elapsed_time:.2f} seconds:")
            diveconquer(input_files, mode, parallel, 0, "")
            if elapsed_time >= interval:
                break

    if log_file:
        with open(log_file, 'a') as log:
            log.write(f"\nResults at {datetime.now()}:")
            diveconquer(input_files, mode, parallel, 0, "")

def signal_handler(signum, frame):
    print("\nReceived SIGINT. Waiting for child processes to finish...")
    exit_event.set()
    sys.exit(0)

def print_partial_results():
    with lock:
        current_time = time.time()
        elapsed_time = current_time - start_time

        results = {
            "Timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time)),
            "Elapsed Time": round(elapsed_time, 2),
            "Word Count": aggregated_results[0],
            "Processed Files": aggregated_results[3],
            "Remaining Files": aggregated_results[4]
        }

        print("\nPartial Results:")
        for key, value in results.items():
            print(f"{key}: {value}")
        print("\n")

def print_aggregated_results():
    print(f"Aggregated Results:")
    print(f"Total Words: {aggregated_results[0]}")
    print(f"Unique Words: {aggregated_results[1]}")
    print(f"Occurrences: {aggregated_results[2]}")
    print(f"Processed Files: {aggregated_results[3]}")
    print(f"Remaining Files: {aggregated_results[4]}")

def parse_arguments():
    parser = argparse.ArgumentParser(description="Ferramenta para Processar Argumentos")
    parser.add_argument("input_files", nargs='+', help="input files")
    parser.add_argument("-m", dest="mode", choices=["t", "u", "o"], default="t", help="define o modo de execução")
    parser.add_argument("-p", dest="parallel", type=int, default=0, help="define nivel de paralelização")
    parser.add_argument("-i", dest="time", type=int, default=0)
    
    return parser.parse_args()

if __name__ == "__main__":
    process_data = ProcessData()
    args = parse_arguments()
    diveconquer(args.input_files, args.mode, args.parallel, args.time, log_file=None, process_data=process_data)