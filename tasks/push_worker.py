# Add the project base directory to the system path
import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

import zmq
import sys
import argparse
import uuid
import multiprocessing
from dependancies.constants import *
from dependancies.serialize import *
from dependancies.data_models import *

push_context = zmq.Context()
push_socket = push_context.socket(zmq.DEALER)


# Each subprocess actually creates its own socket = =
def execute_task(serialized_task: str, dispatcher_url, worker_id):
    temp_id = str(uuid.uuid4())
    push_socket.setsockopt(zmq.IDENTITY, temp_id.encode())
    push_socket.connect(dispatcher_url)

    task = deserialize(serialized_task)
    fn_payload, param_payload = deserialize(task.fn_payload), deserialize(task.param_payload)
    try:
        task.result = fn_payload(*param_payload[0], **param_payload[1])
        task.status = TASK_COMPLETE
        event = RESULT
        print("Function Execution succeed!")
        print(f"Result:\n {task}")
    except Exception as e:
        task.status = TASK_FAILURE
        task.result = serialize(e)
        event = FAILURE
        print(f"Function Execution Failed")
        print(f"Exception Detail:\n{e}")
    push_socket.send(
        serialize({
            "event": event,
            'worker_id': worker_id,   # important
            "data": serialize(task)
        }).encode()
    )


def exception_handler(e, task, worker_id):
    print(f"worker id: {worker_id} exception")
    print(e)
    task.result = serialize(e)
    task.status = TASK_FAILURE
    push_socket.send({
        "event": TASK,
        "data": serialize(task)
    })


def shutdown_handler(e, worker_id):
    print(f"Shutting down pull worker (id: {worker_id})...")
    print(e)
    push_socket.send({
        "event": SHUTDOWN,
        "data": serialize(e)
    })


def main(num_worker_processors, dispatcher_url):
    worker_id = str(uuid.uuid4())
    push_socket.setsockopt(zmq.IDENTITY, worker_id.encode())
    push_socket.connect(dispatcher_url)
    response = "None"  # just a placeholder, no specific meaning
    try:
        push_socket.send(serialize({
            "event": REGISTERATION,
            "num_of_processes": num_worker_processors
        }).encode())
    except Exception as e:
        # Connection failed (Rejected since wrong type of worker or else)
        print(response)
        print(e)
        push_socket.close()
        push_context.term()
        return
    with multiprocessing.Pool(processes=num_worker_processors) as pool:
        try:
            while True:
                # Receiving a message on the router (server) side
                encoded_serialized_message = push_socket.recv()
                message = deserialize(encoded_serialized_message.decode())
                print(f"Worker {worker_id} received message from dispatcher")
                print(f"message: {message}")
                pool.apply_async(execute_task, (message['data'], dispatcher_url, worker_id))
        except KeyboardInterrupt as e:
            shutdown_handler(e, worker_id)
        except Exception as e:
            shutdown_handler(e, worker_id)
        finally:
            push_socket.close()
            push_context.term()


if __name__ == "__main__":
    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description='Process some integers.')

    # Add arguments
    parser.add_argument('num_worker_processors', type=int, help='Number of worker processors')
    parser.add_argument('dispatcher_url', type=str, help='Dispatcher URL')

    # Parse arguments
    args = parser.parse_args()

    # Call main function with arguments
    main(args.num_worker_processors, args.dispatcher_url)
