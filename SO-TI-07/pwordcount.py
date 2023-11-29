### Grupo: SO-TI-07
### Aluno 1: Diogo Forte (fc56931)
### Aluno 2: Gonçalo Gouveia (fc60289)
### Aluno 3: João Vaz (fc58283)


import sys
import argparse
from multiprocessing import Process, Value, Array, Queue, Semaphore
import os
import signal
#TO-DO: implementar o file/std output

valuewords = Value("i", 0)
arraywords = Array("i", 99)
q = Queue()

def special_cleaner(unclean_words):
    special_chars = '!@#$%^&*()_+[]{}|;:,.<>?/\\"~†–'
    clean_words = [word.translate(str.maketrans('', '', special_chars)).lower() \
        for word in unclean_words if word.strip()]
    for word in clean_words:
        if word == '' or word == '-':
            clean_words.remove(word)
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
    return words[int((n_now-1)*len(words)/n):int(n_now*len(words)/n)]

def word_counter(files, n, n_now):
    for nf in range(len(files)):
        words = file_divider(files, nf, n, n_now)
        valuewords.value += len(words)
    
def unique_word_counter(files, n, n_now):
    for nf in range(len(files)):
        words = file_divider(files, nf, n, n_now)
        unique_words = set(words)
        q.put(unique_words)

def occurence_counter(files, n, n_now):
    for nf in range(len(files)):
        word_count = {}
        words = file_divider(files, nf, n, n_now)
        for word in words:
            if word in word_count:
                word_count[word] += 1
            else:
                word_count[word] = 1
        q.put(word_count)

def diveconquer(input_files, mode, parallel, time, output):
    num_files = len(input_files)
    num_processes = parallel  # Use specified number of processes
    processes = []

    def worker(start_idx, end_idx, n, n_now):
        pid = os.getpid()
        if end_idx - start_idx == 1:
            print(f"Process {pid} is working on the file {input_files[start_idx]}")
        else:
            print(f"Process {pid} is working on files {input_files[start_idx]} to {input_files[end_idx - 1]}")

        process_file(input_files[start_idx:end_idx], mode, n, n_now)
    
    def printer(mode, parallel):
        if mode == "t":
            print("Número total de Palavras:", valuewords.value)
        elif mode == "u":
            uniqueword_sets = []
            for p in range(parallel):
                uniqueword_sets += list(q.get())
            print("Número total de Palavras Únicas:", len(set(uniqueword_sets)))
        elif mode == "o":
            occu_count = {}
            for p in range(parallel):
                words = q.get()
                for word in words:
                    if word in occu_count:
                        occu_count[word] += words[word]
                    else:
                        occu_count[word] = words[word]
            print("Contagem da Ocorrência de Palavras:")
            for word, count in occu_count.items():
                print(word + ":", count)
            

    if num_processes > 1 and num_files == 1:
        for i in range(1, num_processes + 1):
            newprocess = Process(target=worker, args=(0, 1, num_processes, i,))
            newprocess.start()
            processes.append(newprocess)

            # if pid == 0:
            #     signal.signal(signal.SIGINT, signal.SIG_DFL)
            #     worker(0, 1, os.getpid(), num_processes, i)
            #     os._exit(0)
            # else:
            #     os.wait()

    else:
        num_processes = min(parallel, num_files)
        for i in range(num_processes):
            start_idx = i * (num_files // num_processes)
            end_idx = (i + 1) * (num_files // num_processes) if i < num_processes - 1 else num_files
            newprocess = Process(target=worker, args=(start_idx, end_idx, 1, 1,))
            newprocess.start()
            processes.append(newprocess)

            # if pid == 0:
            #     worker(start_idx, end_idx, os.getpid(), 1, 1)
            #     os._exit(0)
            # else:
            #     os.wait()
    
    for pro in processes:
        pro.join()
    
    printer(mode, parallel)
    


def init_worker():
    # Ignore SIGINT in child processes
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def signal_handler(signum, frame):
    # Handle SIGINT in the parent process
    print("\nReceived SIGINT. Waiting for child processes to finish...")
    # Perform any necessary cleanup or final calculations
    sys.exit(0)


def process_file(file, mode, n, n_now):
    if mode == "t":
        return word_counter(file, n, n_now)
    elif mode == "u":
        return unique_word_counter(file, n, n_now)
    elif mode == "o":
        return occurence_counter(file, n, n_now)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Ferramenta para Processar Argumentos")
    parser.add_argument("-m", dest="mode", choices=["t", "u", "o"], default="t", help= "define o modo de execução")
    parser.add_argument("-p", dest="parallel", type=int, default=0, help= "define nivel de paralelização")
    parser.add_argument("-i", dest="time", type=int, default=3, help="define o intervalo de tempo")
    parser.add_argument("-l", dest="output", default="" ,help="define o ficheiro para onde os resultados irão estar. Extensão .log")
    parser.add_argument("input_files",nargs='+', help="Introduza ficheiro(s)")
    return parser.parse_args()

def main(args):
    args = parse_arguments() 
    input_files = args.input_files
    mode = args.mode
    parallel = args.parallel
    time = args.time
    output = args.output
    print('Programa: pwordcount.py')
    print('Argumentos: ', args)
    print('  Nível de Paralelização:', parallel)
    print('  Ficheiros de Entrada:', input_files, "\n")
    diveconquer(input_files,mode,parallel, time, output)
 
if __name__ == "__main__":
    main(sys.argv[1:])
