import sys
import argparse
from multiprocessing import Process, Value, Array, Queue, Semaphore
import os
import signal
import time
from datetime import datetime

lock = multiprocessing.Lock()
exit_event = multiprocessing.Event()
aggregated_results = multiprocessing.Array('i', [0, 0, 0, 0, 0])


def special_cleaner(unclean_words):
    special_chars = '!@#$%^&*()_+[]{}|;:,.<>?/\\"~†–'
    clean_words = [word.translate(str.maketrans('', '', special_chars)).lower() for word in unclean_words if word.strip()]
    clean_words = [word for word in clean_words if word not in ['', '-']]
    return clean_words


def count_lines(file):
    line_count = 0
    with open(file, 'r') as f:
        for line in f:
            line_count += 1
    return line_count


def file_divider(files, n_files, n, n_now):
    with open(files[n_files], 'r') as file:
        words = special_cleaner(file.read().split())
    return words[int((n_now - 1) * len(words) / n):int(n_now * len(words) / n)]


def word_counter(files, n, n_now):
    for nf in range(len(files)):
        words = file_divider(files, nf, n, n_now)
        print(f"Total de {len(words)} palavras entre as linhas {int((n_now-1)*count_lines(files[nf])/n)} "
              f"e {int(n_now*count_lines(files[nf])/n)} de {files[nf]}")
    print("")


def unique_word_counter(files, n, n_now):
    for nf in range(len(files)):
        words = file_divider(files, nf, n, n_now)
        unique_words = set(words)
        print(f"{len(unique_words)} palavras unicas entre as linhas {int((n_now-1)*count_lines(files[nf])/n)} "
              f"e {int(n_now*count_lines(files[nf])/n)} de {files[nf]}")
    print("")


def occurrence_counter(files, n, n_now):
    for nf in range(len(files)):
        word_count = {}
        words = file_divider(files, nf, n, n_now)
        for word in words:
            word_count[word] = word_count.get(word, 0) + 1

        print(f"Ocorrências de Palavras Únicas/Diferentes entre as linhas "
              f"{int((n_now-1)*count_lines(files[nf])/n)} e {int(n_now*count_lines(files[nf])/n)} de {files[nf]}:")

        for word, count in word_count.items():
            print(f"{word}: {count}")

    print("")


def worker(start_idx, end_idx, pid, n, n_now):
    if end_idx - start_idx == 1:
        print(f"Process {pid} is working on the file {input_files[start_idx]}")
    else:
        print(f"Process {pid} is working on files {input_files[start_idx]} to {input_files[end_idx - 1]}")

    result = process_file(input_files[start_idx:end_idx], mode, n, n_now)

    with lock:
        # Update aggregated results based on the result from the current process
        aggregated_results[0] += result[0]
        aggregated_results[1] += result[1]
        aggregated_results[2] += result[2]
        aggregated_results[3] += result[3]
        aggregated_results[4] += result[4]


def process_file(file, mode, n, n_now):
    if mode == "t":
        return word_counter(file, n, n_now)
    elif mode == "u":
        return unique_word_counter(file, n, n_now)
    elif mode == "o":
        return occurrence_counter(file, n, n_now)


def diveconquer(input_files, mode, parallel, interval, log_file):
    num_files = len(input_files)
    num_processes = min(parallel, num_files)

    if interval > 0:
        start_time = time.time()
        while True:
            time.sleep(interval)
            elapsed_time = time.time() - start_time
            print_partial_results()  # Print partial results from the parent process
            if elapsed_time >= interval:
                break

    for i in range(num_processes):
        if exit_event.is_set():
            break

        start_idx = i * (num_files // num_processes)
        end_idx = (i + 1) * (num_files // num_processes) if i < num_processes - 1 else num_files
        pid = os.fork()

        if pid == 0:
            worker(start_idx, end_idx, os.getpid(), 1, 1)
            os._exit(0)
        else:
            os.wait()

    print_aggregated_results()

    if interval > 0:
        start_time = time.time()
        while True:
            time.sleep(interval)
            elapsed_time = time.time() - start_time
            print(f"\nResults after {elapsed_time:.2f} seconds:")
            diveconquer(input_files, mode, parallel, 0, "")  # Print results without additional processing
            if elapsed_time >= interval:
                break

    if log_file:
        with open(log_file, 'a') as log:
            log.write(f"\nResults at {datetime.now()}:")
            diveconquer(input_files, mode, parallel, 0, "")


def init_worker():
    # Ignore SIGINT in child processes
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def signal_handler(signum, frame):
    # Handle SIGINT in the parent process
    print("\nReceived SIGINT. Waiting for child processes to finish...")
    exit_event.set()
    # Perform any necessary cleanup or final calculations
    sys.exit(0)


def print_partial_results():
    # Implement the logic to print partial results
    # Use lock to safely access shared data
    with lock:
        # Print relevant information (timestamp, elapsed time, word count, processed files, remaining files)
        pass


def print_aggregated_results():
    # Print aggregated results
    # (You may need to modify this part based on your specific result structure)
    print(f"Aggregated Results:")
    print(f"Total Words: {aggregated_results[0]}")
    print(f"Unique Words: {aggregated_results[1]}")
    print(f"Occurrences: {aggregated_results[2]}")
    print(f"Processed Files: {aggregated_results[3]}")
    print(f"Remaining Files: {aggregated_results[4]}")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Ferramenta para Processar Argumentos")
    parser.add_argument("-m", dest="mode", choices=["t", "u", "o"], default="t", help="define o modo de execução")
    parser.add_argument("-p", dest="parallel", type=int, default=0, help="define nivel de paralelização")
    parser.add_argument("-i", dest="time", type=int, default=0)
