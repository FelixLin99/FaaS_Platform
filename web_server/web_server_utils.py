from dependancies.data_models import (RegisterFn,
                                     RegisterFnRep,
                                     ExecuteFnReq,
                                     ExecuteFnRep,
                                     TaskStatusRep,
                                     TaskResultRep,
                                     Task)
from dependancies.db import kvdb
from dependancies.exceptions import FuncNotFoundException, TaskNotFoundException, TaskNotFinishedException
from dependancies.serialize import serialize, deserialize
from dependancies.constants import CHANNEL_NAME
import uuid


def register_function(register_fn: RegisterFn) -> RegisterFnRep:
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
    kvdb.publish(CHANNEL_NAME, str(task_id))
    return ExecuteFnRep(task_id=task_id)


def task_status(task_id: uuid.UUID) -> TaskStatusRep:
    if not kvdb.exists(task_id):
        raise TaskNotFoundException('task_id not found in database')
    task = deserialize(kvdb.get(str(task_id)).decode())
    return TaskStatusRep(task_id=task_id, status=task.status)


def task_result(task_id: uuid.UUID) -> TaskResultRep:
    if not kvdb.exists(task_id):
        raise TaskNotFoundException('task_id not found in database')
    task = deserialize(kvdb.get(str(task_id)).decode())
    if task.status == "FAILURE":
        return TaskResultRep(task_id=task_id,
                             status=task.status,
                             result=str(deserialize(task.result)))
    elif task.status == "COMPLETE":
        return TaskResultRep(task_id=task_id,
                             status=task.status,
                             result=task.result)
    else:
        return TaskResultRep(task_id=task_id,
                             status=task.status,
                             result=TaskNotFinishedException('task has not finished yet'))
