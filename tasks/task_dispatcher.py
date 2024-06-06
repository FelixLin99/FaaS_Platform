# Add the project base directory to the system path
import sys
import os
import uuid

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)


import argparse
import multiprocessing
import zmq
from queue import Empty
from task_dispatcher_utils import *
from redis.client import PubSub
from dependancies.db import kvdb
from dependancies.serialize import deserialize, serialize
from dependancies.constants import *
from dependancies.data_models import Task


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
    with multiprocessing.Pool(processes=num_worker_processors) as pool:
        # subscribe to the redis channel
        p = kvdb.pubsub()
        p.subscribe(CHANNEL_NAME)
        try:
            for message in p.listen():
                if message['type'] == 'message':
                    pool.apply_async(worker, (message['data'],), callback=reporter)
        except KeyboardInterrupt:
            # Handle abrupt termination (e.g., Ctrl+C)
            print("Terminating the program...")


def dispatcher_pull(port: int):
    worker_pool = []

    # run another process as subscriber
    task_queue = multiprocessing.Queue()
    subscriber_init = multiprocessing.Process(target=subscriber, args=(task_queue,))
    subscriber_init.start()

    # process request from workers
    context = zmq.Context()
    dispatcher_socket = context.socket(zmq.REP)
    dispatcher_socket.bind(f"tcp://127.0.0.1:{port}")
    try:
        while True:
            request = dispatcher_socket.recv_json()
            if request['event'] == REGISTER_REQ:
                worker_pool.append(request['id'])
                dispatcher_socket.send_json({
                    'event': REGISTER_REP,
                    'data': None
                })
            elif request['event'] == TASK_REQ:
                try:
                    serialized_task = task_queue.get(block=True, timeout=0.01)
                    response_data = serialized_task
                    task = deserialize(serialized_task)
                    task.status = TASK_RUNNING
                    kvdb.set(str(task.task_id), serialize(task))
                except Empty:
                    response_data = None
                dispatcher_socket.send_json({
                    'event': TASK_REP,
                    'data': response_data
                })
            elif request['event'] == RESULT_REQ:
                data = deserialize(request['data'])
                kvdb.set(str(data.task_id), serialize(data))
                dispatcher_socket.send_json({
                    'event': RESULT_REP,
                    'data': None
                })
            elif request['event'] == FAILURE_REQ:
                data = deserialize(request['data'])
                kvdb.set(str(data.task_id), serialize(data))
                dispatcher_socket.send_json({
                    'event': FAILURE_REP,
                    'data': None
                })
            elif request['event'] == SHUTDOWN_REQ:
                worker_pool.remove(request['id'])
                dispatcher_socket.send_json({
                    'event': SHUTDOWN_REP,
                    'data': None
                })
            else:
                dispatcher_socket.send_json({
                    'event': 'Unknown request',
                    'data': None
                })
    except KeyboardInterrupt:
        subscriber_init.join()
        subscriber_init.close()


def dispatcher_push(port: int):
    context = zmq.Context()
    socket = context.socket(zmq.ROUTER)
    socket.bind(f"tcp://127.0.0.1:{port}")

    # run a process as subscriber
    task_queue = multiprocessing.Queue()
    subscriber_init = multiprocessing.Process(target=subscriber, args=(task_queue,))
    subscriber_init.start()

    # run a process as load_balancer, which is also a dealer
    manager = multiprocessing.Manager()
    worker_pool = manager.dict()
    load_balancer_id = str(uuid.uuid4())
    load_balancer_init = multiprocessing.Process(target=load_balancer, args=(port, worker_pool, task_queue, load_balancer_id))
    load_balancer_init.start()

    # the main runtime itself, it can :
    #   1. continuously receive result/registration from workers
    #   2. continuously receive from load_balancer and allocate the task to a specified worker
    while True:

        encoded_worker_id, encoded_serialized_message = socket.recv_multipart()

        message = deserialize(encoded_serialized_message.decode())
        worker_id = encoded_worker_id.decode()
        # print(message)

        # The message comes from load_balancer
        if worker_id == load_balancer_id:
            destination_worker_id = message['worker_id']
            data = message['task']
            socket.send_multipart([destination_worker_id.encode(), serialize(data).encode()])
            print(f"sent the task to {destination_worker_id}")
            continue

        # The message comes from workers
        if message['event'] == REGISTERATION:
            worker_pool[worker_id] = int(message['num_of_processes'])
        elif message['event'] == RESULT:
            # update redis
            task = deserialize(message['data'])
            task.status = TASK_COMPLETE
            print(task)
            kvdb.set(str(task.task_id), serialize(task))
            # update worker_pool
            worker_id = message['worker_id']
            worker_pool[worker_id] += 1
        elif message['event'] == FAILURE:
            # update redis
            task = deserialize(message['data'])
            task.status = TASK_FAILURE
            print(task)
            kvdb.set(str(task.task_id), serialize(task))
            # update worker_pool
            worker_id = message['worker_id']
            worker_pool[worker_id] += 1
        else:
            pass

    socket.close()

if __name__ == '__main__':
    coordinator(command_line_args_parser())

