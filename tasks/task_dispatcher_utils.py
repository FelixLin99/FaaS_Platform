# Add the project base directory to the system path
import sys
import os
import time

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

import argparse
import multiprocessing
import zmq
from dependancies.serialize import deserialize, serialize
from dependancies.constants import *
from dependancies.data_models import Task
from dependancies.db import kvdb


def worker(data: bytes) -> Task:
    task_id_str = data.decode()
    task = deserialize(kvdb.get(task_id_str).decode())
    func = deserialize(task.fn_payload)
    params = deserialize(task.param_payload)
    try:
        result = func(*params[0], **params[1])
        task.result = serialize(result)
        task.status = 'COMPLETE'
    except Exception as e:
        task.status = 'FAILURE'
    return task


def reporter(task: Task):
    print(task)
    kvdb.set(str(task.task_id), serialize(task))


def subscriber(task_queue: multiprocessing.Queue):
    sub = kvdb.pubsub()
    sub.subscribe(CHANNEL_NAME)
    try:
        for message in sub.listen():
            if message['type'] == 'message':
                task_id_str = message['data'].decode()
                task = kvdb.get(task_id_str).decode()
                task_queue.put(task)
    except KeyboardInterrupt:
        return



def load_balancer(port, worker_pool, task_queue, id):
    context = zmq.Context()
    socket = context.socket(zmq.DEALER)
    socket.setsockopt(zmq.IDENTITY, id.encode())
    socket.connect(f"tcp://127.0.0.1:{port}")
    print("load_balancer finished setting up ")
    try:
        while True:
            # spin until a worker becomes free
            print("number of workers:", len(worker_pool))
            if len(worker_pool) == 0:
                time.sleep(3)
                continue

            max_pair = max(worker_pool.items(), key=lambda x: x[1])
            num_of_processors_idle = max_pair[1]
            worker_id = max_pair[0]
            if num_of_processors_idle < 1:
                continue

            print(f'worker {worker_id} in place')
            # get a task from queue
            serialized_task = task_queue.get(block=True)

            package = {
                'worker_id': worker_id,
                'task': {
                    'event': TASK,
                    'data': serialized_task
                }
            }

            # update worker_pool
            worker_pool[worker_id] -= 1

            # async sending
            socket.send(serialize(package).encode())
            print(f"message sent to the router")



            # update redis
            task = deserialize(serialized_task)
            task.status = TASK_RUNNING
            kvdb.set(str(task.task_id), serialize(task))

    except KeyboardInterrupt:
        socket.close()
        return
