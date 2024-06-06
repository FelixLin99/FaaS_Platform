from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dependancies.data_models import *
from web_server_utils import (register_function,
                              execute_function,
                              task_status,
                              task_result)
from dependancies.exceptions import (DuplicateFuncException,
                                     FuncNotFoundException,
                                     TaskNotFoundException)
import uuid
app = FastAPI()


@app.get("/")
def hello():
    return {"hello": "world"}


@app.exception_handler(ValueError)
async def global_valueerror_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=500,
        content={"Original request": request,
            "Error content": str(exc)},
    )


@app.exception_handler(KeyError)
async def global_keyerror_handler(request: Request, exc: KeyError):
    return JSONResponse(
        status_code=500,
        content={"Original request": request,
            "Error content": str(exc)},
    )


@app.exception_handler(TypeError)
async def global_typeerror_handler(request: Request, exc: TypeError):
    return JSONResponse(
        status_code=500,
        content={"Original request": request,
            "Error content": str(exc)},
    )


@app.exception_handler(DuplicateFuncException)
async def global_duplicate_func_handler(request: Request, exc: DuplicateFuncException):
    return JSONResponse(
        status_code=500,
        content={"Original request": request,
            "Error content": str(exc)},
    )


@app.exception_handler(FuncNotFoundException)
async def global_func_not_found_handler(request: Request, exc: FuncNotFoundException):
    return JSONResponse(
        status_code=404,
        content={"Original request": request,
            "Error content": str(exc)},
    )


@app.exception_handler(TaskNotFoundException)
async def global_func_not_found_handler(request: Request, exc: TaskNotFoundException):
    return JSONResponse(
        status_code=404,
        content={"Original request": request,
            "Error content": str(exc)},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"Original request": request,
            "Error content": str(exc)},
    )


@app.post("/register_function")
async def register_function_api(register_func: RegisterFn) -> RegisterFnRep:
    return register_function(register_func)


@app.post("/execute_function")
async def execute_function_api(execute_func: ExecuteFnReq) -> ExecuteFnRep:
    return execute_function(execute_func)


@app.get("/status/<task_id>")
async def task_status_api(task_id: uuid.UUID) -> TaskStatusRep:
    return task_status(task_id)


@app.get("/api/v1/result/<task_id>")
async def task_result_api(task_id: uuid.UUID) -> TaskResultRep:
    return task_result(task_id)