
import argparse
import time
import requests
from .serialize import serialize, deserialize
import logging
import random

base_url = "http://127.0.0.1:8000/"

valid_statuses = ["QUEUED", "RUNNING", "COMPLETED", "FAILED"]


def sleep_func(duration):
    import time
    time.sleep(duration)


def noop_func():
    pass


def cpu_intensive_func(duration):
    import time
    start_time = time.time()
    while True:
        if time.time() - start_time >= duration:
            break


def scenario_1_sleep(num_of_tasks, duration=5):
    # register function
    resp = requests.post(base_url + "register_function",
                         json={"name": "sleep_func",
                               "payload": serialize(sleep_func)})
    fn_info = resp.json()
    assert "function_id" in fn_info

    # start timing and execute <duration> number of tasks
    start_time = time.time()
    task_id_list = []
    for _ in range(num_of_tasks):
        resp = requests.post(base_url + "execute_function",
                             json={"function_id": fn_info['function_id'],
                                   "payload": serialize(((duration,), {}))})
        assert resp.status_code == 200
        assert "task_id" in resp.json()
        task_id_list.append(resp.json()["task_id"])

    # wait_until_all_tasks_complete
    wait_until_all_tasks_complete(task_id_list)
    end_time = time.time()

    return end_time - start_time


def scenario_2_noop(num_of_tasks):
    # register function
    resp = requests.post(base_url + "register_function",
                         json={"name": "noop_func",
                               "payload": serialize(noop_func)})
    fn_info = resp.json()
    assert "function_id" in fn_info

    # start timing and execute <duration> number of tasks
    start_time = time.time()
    task_id_list = []
    for _ in range(num_of_tasks):
        resp = requests.post(base_url + "execute_function",
                             json={"function_id": fn_info['function_id'],
                                   "payload": serialize(((), {}))})
        assert resp.status_code == 200
        assert "task_id" in resp.json()
        task_id_list.append(resp.json()["task_id"])

    # wait_until_all_tasks_complete
    wait_until_all_tasks_complete(task_id_list)
    end_time = time.time()

    return end_time - start_time


def scenario_3_intensive(num_of_tasks, duration=5):
    # register function
    resp = requests.post(base_url + "register_function",
                         json={"name": "cpu_intensive_func",
                               "payload": serialize(cpu_intensive_func)})
    fn_info = resp.json()
    assert "function_id" in fn_info

    # start timing and execute <duration> number of tasks
    start_time = time.time()
    task_id_list = []
    for _ in range(num_of_tasks):
        resp = requests.post(base_url + "execute_function",
                             json={"function_id": fn_info['function_id'],
                                   "payload": serialize(((duration,), {}))})
        assert resp.status_code == 200
        assert "task_id" in resp.json()
        task_id_list.append(resp.json()["task_id"])

    # wait_until_all_tasks_complete
    wait_until_all_tasks_complete(task_id_list)
    end_time = time.time()

    return end_time - start_time


def wait_until_all_tasks_complete(task_id_list):
    while len(task_id_list) > 0:
        offset = 0
        for i in range(len(task_id_list)):
            task_id = task_id_list[i-offset]
            resp = requests.get(f"{base_url}result/{task_id}")
            assert resp.status_code == 200
            assert resp.json()["task_id"] == task_id
            if resp.json()['status'] == 'COMPLETED':
                del task_id_list[i-offset]
                offset += 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', choices=['sleep', 'noop', 'intensive'], required=True, help='Type of function.')
    parser.add_argument('-n', type=int, required=True, help='Num of tasks')
    parser.add_argument('-m', type=int, required=True, help='Run <m> times and return the average time')
    parser.add_argument('-d', type=int, required=False, help='Duration')
    args = parser.parse_args()

    run_time_list = []
    for _ in args.m:
        if args.f == 'sleep':
            run_time_list.append(scenario_1_sleep(args.n, args.d))
        elif args.f == 'noop':
            run_time_list.append(scenario_2_noop(args.n))
        elif args.f == 'intensive':
            run_time_list.append(scenario_3_intensive(args.n, args.d))
        else:
            pass

    print(sum(run_time_list) / len(run_time_list))