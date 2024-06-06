# Add the project base directory to the system path
import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

import argparse
import multiprocessing
from dependancies.db import kvdb
from dependancies.serialize import deserialize, serialize
from dependancies.constants import *


def command_line_args_parser() -> dict:
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', choices=['local', 'pull', 'push'], required=True, help='Mode of operation.')
    parser.add_argument('-p', type=int, required=False, help='Port number (only for push/pull).')
    parser.add_argument('-w', type=int, required=False, help='Number of worker processors (only for local).')
    args = parser.parse_args()
    return {'mode': args.m, 'port': args.p, 'num_worker_processors': args.w}


def coordinator(d: dict):
    if d['mode'] == 'local':
        dispatcher_local(d['num_worker_processors'])
    elif d['mode'] == 'pull':
        dispatcher_pull(d['port'])
    elif d['mode'] == 'push':
        dispatcher_push(d['port'])


def dispatcher_local(num_worker_processors: int):
    task_queue = multiprocessing.Queue()
    result_queue = multiprocessing.Queue()
    termination_signal = multiprocessing.Value('i', 0)

    # setup local workers
    slaves_list = []
    for _ in range(num_worker_processors):
        slave = multiprocessing.Process(target=worker, args=(task_queue, result_queue, termination_signal))
        slave.start()
        slaves_list.append(slave)

    # setup several reporters
    num_reporters = 2
    reporters_list = []
    for _ in range(num_reporters):
        rpt = multiprocessing.Process(target=reporter, args=(result_queue,termination_signal))
        rpt.start()
        reporters_list.append(rpt)

    # subscribe to the redis channel
    p = kvdb.pubsub()
    p.subscribe(CHANNEL_NAME)
    try:
        for message in p.listen():
            if message['type'] == 'message':
                task_id_str = message['data'].decode()
                task = deserialize(kvdb.get(task_id_str).decode())
                task_queue.put(task)
    except KeyboardInterrupt:
        termination_signal.value = 1
        print("Termination signal received. Task dispatcher exited gracefully.")


def dispatcher_pull(port: int):

    pass


def dispatcher_push(port: int):
    pass


# Good to have multiprocessing.Queue in place, which avoid being busy-waiting for tasks!
# A worker takes and preforms a task each time in the shared 'task_queue' queue.
# TODO: Still some minor risk of process leak (when code exits abruptly without using Ctrl+C)
def worker(
        task_queue: multiprocessing.Queue,
        result_queue: multiprocessing.Queue,
        termination_signal: multiprocessing.Value
):
    while not termination_signal.value:
        task = task_queue.get()
        func = deserialize(task.fn_payload)
        params = deserialize(task.param_payload)
        try:
            result = func(*params[0], **params[1])
            task.result = serialize(result)
            task.status = 'COMPLETE'
        except Exception as e:
            task.status = 'FAILURE'
        result_queue.put(task)


# A reporter takes a task from the shared 'result_queue' queue. and update its info in redis.
# TODO: Still some minor risk of process leak (when code exits abruptly without using Ctrl+C)
def reporter(
        result_queue: multiprocessing.Queue,
        termination_signal: multiprocessing.Value
):
    while not termination_signal.value:
        task = result_queue.get()  # Get a result from the result queue
        kvdb.set(str(task.task_id), serialize(task))


if __name__ == '__main__':
    coordinator(command_line_args_parser())

