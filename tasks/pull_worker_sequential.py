# Add the project base directory to the system path
import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from multiprocessing import Pool
import uuid
import zmq
import sys
import argparse
from dependancies.constants import *
from dependancies.data_models import *
from dependancies.serialize import serialize, deserialize


def execute_task(serialized_task: str) -> Task:  # take in a serialized task and return a result (Task)
    task = deserialize(serialized_task)
    fn_payload, param_payload = deserialize(task.fn_payload), deserialize(task.param_payload)
    res = fn_payload(*param_payload[0], **param_payload[1])
    task.result = serialize(res)
    task.status = TASK_COMPLETE
    return task


def fetch_task(worker_id, pull_socket, timeout=0.01):
    pull_socket.send_json({
        "id": worker_id,
        "event": TASK_REQ
    })
    return pull_socket.recv_json()


def error_handler(worker_id, pull_socket):
    # Deprecated
    pass


def main(num_worker_processors, dispatcher_url):
    pull_context = zmq.Context()
    pull_socket = pull_context.socket(zmq.REQ)
    pull_socket.connect(dispatcher_url)
    response = "None"  # just a placeholder, no specific meaning
    worker_id = str(uuid.uuid4())
    try:
        pull_socket.send_json({"id": worker_id,
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

    try:
        while True:
                # Poll the server for tasks
                # this can be done by the server replying with a delay as well
            response = fetch_task(worker_id, pull_socket, timeout=0.01)
            print(response)
            try:
                data = execute_task(response['data'])
                print("Function Execution succeed!")
                print(f"Result:\n {data}")
                pull_socket.send_json({
                    "event": RESULT_REQ,
                    "data": serialize(data)
                })
                pull_socket.recv_json()
            except Exception as e:
                print(f"Function Execution Failed on worker id: {worker_id}")
                print(f"Exception Detail:\n{e}")
                data = deserialize(response['data'])
                data.result = serialize(e)
                data.status = TASK_FAILURE
                pull_socket.send_json({
                    "event": FAILURE_REQ,
                    "data": serialize(data)
                })
                pull_socket.recv_json()
    except KeyboardInterrupt as e:
        print(f"Shutting down pull worker (id: {worker_id})...")
        pull_socket.send_json({
            "id": worker_id,
            "event": SHUTDOWN_REQ,
            "data": serialize(e)
        })
        pull_socket.recv_json()
    except Exception as e:
        print(f"Shutting down pull worker (id: {worker_id})...")
        print(e)
        pull_socket.send_json({
            "id": worker_id,
            "event": SHUTDOWN_REQ,
            "data": serialize(e)
        })
        pull_socket.recv_json()
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