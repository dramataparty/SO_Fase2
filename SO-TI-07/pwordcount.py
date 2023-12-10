import sys
import os
import signal
import time
from datetime import datetime
from multiprocessing import Process, Lock, Event, Manager, Value, Queue, Array
import argparse


finished = 0

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
    start_idx = int(n_now * len(words) / n)
    end_idx = int((n_now + 1) * len(words) / n)
    return words[start_idx:end_idx]

def word_counter(file, n, n_now, shared_data, lock):
    words = file_divider(file, n, n_now)
    with lock:
        for word in words:
            shared_data.value += 1
    os.kill(os.getppid(), signal.SIGUSR1)

def unique_word_counter(file, n, n_now, shared_data, result_queue, nbProcess):
    words = file_divider(file, n, n_now)
    unique_words = set(words)
    for word in unique_words:
        shared_data[nbProcess] += 1
    result_queue.put(unique_words)
    os.kill(os.getppid(), signal.SIGUSR1)

def occurrence_counter(file, n, n_now, shared_data, result_queue, nbProcess):
    words = file_divider(file, n, n_now)
    word_count = {}
    for word in words:
        word_count[word] = word_count.get(word, 0) + 1
    for word in word_count:
        shared_data[nbProcess] += 1
    result_queue.put(word_count)
    os.kill(os.getppid(), signal.SIGUSR1)

def worker(start_idx, end_idx, pid, n, n_now, input_files, mode, shared_data, result_queue, nbProcess, lock):
    for idx in range(start_idx, end_idx):
        file = input_files[idx]
        print(f"Process {pid} is working on the file {file}")

        if mode == "t":
            word_counter(file, n, n_now, shared_data, lock)
        elif mode == "u":
            unique_word_counter(file, n, n_now, shared_data, result_queue, nbProcess)
        elif mode == "o":
            occurrence_counter(file, n, n_now, shared_data, result_queue, nbProcess)

def diveconquer(input_files, mode, parallel, interval, log_file):
    start_time = time.time()
    manager = Manager()
    shared_data = manager.dict()
    result_queue = manager.Queue()
    shared_data = None
    lock = Lock()
    if mode == "t":
        shared_data = Value("i", 0) 
    else:
        shared_data = Array("i", [0]*parallel)
            
    num_files = len(input_files)
    num_processes = parallel
    text_blocks = 0

    processes = []
    if num_processes > 1 and num_files == 1:
        text_blocks = num_processes
        for i in range(num_processes) :
            pid = os.fork()
            if pid == 0:
                worker(0, 1, os.getpid(), num_processes, i, input_files, mode, shared_data, result_queue, i, lock)
                os._exit(0)
            else:
                processes.append(pid)
    else:
        num_processes = min(parallel, num_files)
        text_blocks = num_files
        for i in range(num_processes):
            start_idx = i * (num_files // num_processes)
            end_idx = (i + 1) * (num_files // num_processes) if i < num_processes - 1 else num_files
            pid = os.fork()

            if pid == 0:
                worker(start_idx, end_idx, os.getpid(), 1, 0, input_files, mode, shared_data, result_queue, i, lock)
                os._exit(0)
            else:
                processes.append(pid)

    signal.signal(signal.SIGINT, lambda signum, frame: signal_handler(signum, frame, processes, shared_data, result_queue, mode))
    signal.signal(signal.SIGUSR1, signal_counter)

    if interval > 0:
        last_time = time.time()
        elapsed_time = 0
        k = 0
        while True:
            current_time = time.time() - last_time
            if current_time >= interval:
                if text_blocks == finished:
                    k += 1
                    if k == 2:
                        break
                last_time = time.time()
                elapsed_time = current_time - start_time + last_time
                print_partial_results(mode, text_blocks, shared_data, elapsed_time, log_file)
                      
    print_aggregated_results(shared_data, result_queue, mode)

def signal_handler(signum, frame, processes, shared_data, result_queue, mode):
    print("\nReceived SIGINT. Waiting for child processes to finish...")
    for pid in processes:
        os.kill(pid, signal.SIGTERM)
    
    print_aggregated_results(shared_data, result_queue, mode)
        
    sys.exit(0)

def signal_counter(signum, frame):
    global finished
    finished += 1

def print_partial_results(mode, processes, shared_data, elapsed_time, output=None):
    total_words = 0
    if mode == "t":
        total_words += shared_data.value
    else:
        for counter in shared_data:
            total_words += counter

    if output:
        with open(output, 'a') as log:
            date=str(datetime.now())
            log.write(date[0:10] + "_" + date[11:19] + " ")
            log.write(str(int(elapsed_time*1e6)) + " ")
            log.write(str(total_words) + " ")
            log.write(str(finished) + " ")
            log.write(str(processes-finished) + "\n")
            
    else:
        date=str(datetime.now())
        print(date[0:10] + "_" + date[11:19], str(int(elapsed_time*1e6)), str(total_words), str(finished), str(processes-finished))

def print_aggregated_results(shared_data, result_queue, mode):
    print("\nAggregated Results:")
    if mode == "t":
        print("Número total de Palavras encontradas:", shared_data.value)
        
    elif mode == "u":
        result_data = set()
        while not result_queue.empty():
            result_data.update(result_queue.get())
        print("Número total de Palavras Únicas encontradas:", len(result_data))
        
    elif mode == "o":
        results_dict = {}
        while not result_queue.empty():
            words = result_queue.get()
            for word in words.keys():
                results_dict[word] = results_dict.get(word, 0) + words[word]
        results = []
        for word, count in results_dict.items():
                results.append((word, count))
        print("Número de Ocorrências de cada Palavra:", results)

    
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
    parser.add_argument("-i", dest="interval", type=int, default=3, help="Interval for periodic printing")
    parser.add_argument("-l", dest="outfile", type=str, default=None, help="Output (file/stdout)")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    diveconquer(args.input_files, args.mode, args.parallel, args.interval, args.outfile)
