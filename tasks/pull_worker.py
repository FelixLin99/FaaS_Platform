# Add the project base directory to the system path
import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)


from multiprocessing import Pool
import uuid
import zmq
import sys
import time
import argparse
import multiprocessing
from dependancies.constants import *
from dependancies.serialize import serialize, deserialize


pull_context = zmq.Context()
pull_socket = pull_context.socket(zmq.REQ)
# Create a lock object
lock = multiprocessing.Lock()


def execute_task(serialized_task: str, dispatcher_url):
    pull_socket.connect(dispatcher_url)
    task = deserialize(serialized_task)
    fn_payload, param_payload = deserialize(task.fn_payload), deserialize(task.param_payload)
    try:
        task.result = fn_payload(*param_payload[0], **param_payload[1])
        task.status = TASK_COMPLETE
        event = RESULT_REQ
        print("Function Execution succeed!")
        print(f"Result:\n {task}")
    except Exception as e:
        task.status = TASK_FAILURE
        task.result = serialize(e)
        event = FAILURE_REQ
        print(f"Function Execution Failed")
        print(f"Exception Detail:\n{e}")

    with lock:
        print("get the lock!")
        pull_socket.send_json({
            "event": event,
            "data": serialize(task)
        })
        print("send the result!")
        print(pull_socket.recv_json())


def fetch_task(timeout=0.01):
    time.sleep(timeout)
    with lock:
        pull_socket.send_json({
            "event": TASK_REQ,
            "data": None
        })
        return pull_socket.recv_json()['data']


def exception_handler(e, task, worker_id):
    print(f"Function Execution Failed on worker id: {worker_id}")
    print(f"Exception Detail:\n{e}")
    task.result = serialize(e)
    task.status = TASK_FAILURE
    with lock:
        pull_socket.send_json({
            "event": FAILURE_REQ,
            "data": serialize(task)
        })
        pull_socket.recv_json()


def shutdown_handler(e, worker_id):
    print(f"Shutting down pull worker (id: {worker_id})...")
    print(e)
    with lock:
        pull_socket.send_json({
            "event": SHUTDOWN_REQ,
            "data": serialize(e)
        })
        pull_socket.recv_json()


def main(num_worker_processors, dispatcher_url):
    pull_socket.connect(dispatcher_url)
    response = "None"  # just a placeholder, no specific meaning
    worker_id = str(uuid.uuid4())
    try:
        pull_socket.send_json({
            "id": worker_id,
            "event": REGISTER_REQ
        })
        response = pull_socket.recv_json()
        print(response)
        assert response['event'] == REGISTER_REP
    except Exception as e:
        # Connection failed (Rejected since wrong type of worker or else)
        print(response)
        print(e)
        pull_socket.close()
        pull_context.term()
        return

    # Task dispatching
    with multiprocessing.Pool(processes=num_worker_processors) as pool:
        try:
            while True:
                # Poll the server for tasks
                # this can be done by the server replying with a delay as well
                serialized_task = fetch_task(timeout=0.02)
                if serialized_task is not None:
                    pool.apply_async(execute_task, (serialized_task,dispatcher_url,))
        except KeyboardInterrupt as e:
            shutdown_handler(e, worker_id)
        except Exception as e:
            shutdown_handler(e, worker_id)
        finally:
            pull_socket.close()
            pull_context.term()


if __name__ == "__main__":
    # Create an ArgumentParser object
    parser = argparse.ArgumentParser()

    # Add arguments
    parser.add_argument('num_worker_processors', type=int, help='Number of worker processors')
    parser.add_argument('dispatcher_url', type=str, help='Dispatcher URL')

    # Parse arguments
    args = parser.parse_args()

    # Call main function with arguments
    main(args.num_worker_processors, args.dispatcher_url)