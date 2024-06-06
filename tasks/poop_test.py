# Add the project base directory to the system path
import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)


import time
from dependancies.db import kvdb
from dependancies.data_models import *
from dependancies.serialize import *
from dependancies.exceptions import FuncNotFoundException

import time
import random

#test functions
def func_sleep(x):
    import time
    import random
    x = x + 1
    sleep_time = random.uniform(0.01, 5)
    time.sleep(sleep_time)



def register_function(register_fn: RegisterFn) -> RegisterFnRep:
    # if kvdb.exists(register_fn.name):
    #     raise DuplicateFuncException('Function name already registered in database')
    func_id = uuid.uuid4()
    kvdb.set(str(func_id), serialize(register_fn))
    return RegisterFnRep(function_id=func_id)


def execute_function(execute_fn: ExecuteFnReq) -> ExecuteFnRep:
    function_id_str = str(execute_fn.function_id)
    if not kvdb.exists(function_id_str):
        raise FuncNotFoundException('Function id not found in database')
    func_registered = deserialize(kvdb.get(function_id_str).decode())
    task_id = uuid.uuid4()
    kvdb.set(
        str(task_id),
        serialize(
            Task(
                task_id=task_id,
                status="QUEUED",
                fn_payload=func_registered.payload,
                param_payload=execute_fn.payload,
                result='',
                exception=''
            )
        )
    )
    kvdb.publish('TASK', str(task_id))
    return ExecuteFnRep(task_id=task_id)


# Start a separate thread to listen for messages
channel = 'TASK'

register_fn = RegisterFn(name='fun1', payload=serialize(func_sleep))

func_id = register_function(register_fn).function_id

print(func_id)

execute_fn = ExecuteFnReq(function_id=func_id, payload=serialize(((1,), {})))

task_id = execute_function(execute_fn).task_id

print(task_id)
