# Technical Report

## Outline

### - Architecture

### - Data Models

### - Other Dependencies

### - REST API

### - Task Dispatcher & Local Workers

### - Pull Workers

### - Push Workers

### - Error Handling

### - Limitations

## Architecture

We utilized Client-Server, Layer, and Call-and-Return patterns for our project design.

### Client-Server: 

When users want to send functions to this Faas Platform for computing, the user will use clients to do so. They make http requests and receive replies of computing results. The primary part of the Faas Platform is a web server that handles requests to register and execute the functions. 

This allows the platform to handle multiple users to utilize the cloud computing service at the same time, and increases the availability.

### Layer: 

We seperated the platform into different layers. 

In web_server.py, we implemented a multi-threaded REST API via FastAPI. The users can register and execute given functions by using clients to POST requests to the corresponding APIs with given data structures. Also, they can make GET requests to retrieve the current statuses and results of the functions that they have register and executed before.

In web_server_utils.py, the server can process the requests that has been sent to the server through manipulating Redis. After completing the processing of requests, the logic implementation functions will return the results through given data structures in data_models.py.

In task_dispatcher.py, the server can retrieve new tasks, and distribute different tasks in different workers evenly. Also, the dispatcher will maintain the status of tasks.

In task_dispatcher.py, pull_worker.py, and push_worker.py, the tasks are processed, and functions are executed.

This makes different components of the server to be decoupled. It allows the developers to maintain, update, extend, and refactor the current services easily.

### Call-and-Return:

For pull_worker.py and push_worker.py, we can register multiple instances to task dispatcher. Also, we can designate the number of work processes of each worker instances. 

This provides both "vertical" and "horizontal" scalability. maintainers can adjust the computing resources by designating different numbers of work processes to different workers, and also registering and shutting down multiple workers.

## Data Models

### RegisterFn:
Data structure to pass the information of the function to be registered through FastAPI

### RegisterFnRep:
Data structure to return the information of the register function to the client through FastAPI

### ExecuteFnReq:
Data structure to pass the information of the function to be executed through FastAPI

### ExecuteFnRep:
Data structure to return the information of the function to be executed to the client through FastAPI

### TaskStatusRep:
Data structure to return the status of the task being executed to the client through FastAPI

### TaskResultRep:
Data structure to return the result of the task being executed to the client through FastAPI

All the above data structures are inherited from BaseModel in pydantic, to mapping the json-structured data into those data models in python.

The following is the data structure for the internal components of the server to communicate with each other. This maintains the information consistency for all the tasks. 

### Task:
Data structure to keep all the information related to the given task. Note that the result attribute could store either serialized result or serialized error. 

## Other Dependencies

### constants.py
Stores all the constants, for decoupling and easy maintenance.

### db.py
Stores the Redis database connection pool, for decoupling and avoid loop dependency among modules.

### exceptions.py
Stores all the self-built exception class for error handling.

### serialize.py
Stores the serialization and deserialization methods for public usage.

## REST API

### register_function_api(register_func: RegisterFn) -> RegisterFnRep:
Take in information of a function as RegisterFn, and returns its register information by RegisterFnRep

### execute_function_api(execute_func: ExecuteFnReq) -> ExecuteFnRep:
Take in information of a function as ExecuteFnReq, and returns its execute task information by ExecuteFnRep

### task_status_api(task_id: uuid.UUID) -> TaskStatusRep:
Take in a task id as uuid.UUID, and return the status of corresponding task as TaskStatusRep

### task_result_api(task_id: uuid.UUID) -> TaskResultRep:
Take in a task id as uuid.UUID, and return the result of corresponding task as TaskResultRep

## Task Dispatcher & Local Workers

The task interacts with REST API through Redis, and interacts with pull workers or push workers through ZeroMQ.

It has three working patterns:

In local mode, the task dispatcher will manage workers running under its instance. The number of work process is given through command line arguments. The main runtime maintains a process pool and is responsible for fetching tasks that are sent to the redis by client. With a task in place, the dispatcher will put the task to the process pool in which any available process will perform the task and send the result to another avaliable process which send the result to main runtime.  

In pull mode, the task dispatcher will accept registrations from one or multiple pull workers, and assign tasks for them to execute. Task dispatcher will assign the task whenever a pull worker requests for it, and listen to receive the results from the worker. The task dispatcher owns a REP socket and each worker has a REQ socket. 

In push mode, the task dispatcher will accept registrations from one or multiple push workers, and maintains the pair <worker_id: worker_workload> in an in-memory data structure. Tasks will be sent to waiting workers using the ZMQ DEALER/ROUTER pattern. The router(dispatcher) also spawns a subprocessor that acts as a dealer to balance workload between workers.

We are using multiprocessing.Pool to manage the work processes in local workers, pull workers and push workers. The wrapper class will help maintain the workload of each process in the pool and orchestrate the executions of tasks through a queueing-like pattern.

For the local worker, the task dispatcher will keep listening to a pubsub channel in Redis, which will notify the task dispatcher when a new task is assigned in database. Then task dispatcher will pass the task to Pool, and choose a worker process to execute the task. After execution, Pool will make calls to the given callback function, which is reporter() here, using the execution results as arguments to update the task information inside Redis. The loop body will keep running until forced to stop, such as keyboard interruption.

## Pull Workers

A pull worker instance will firstly initiate a REQ socket and a lock as global objects. After connecting the socket to given dispatcher url from command line and generating a worker_id, the pull worker will send a REQ message to the REP socket in dispatcher to register. If the returning message from dispatcher shows not registered, then the worker will shut down. Otherwise, the worker will initiate a multiprocessing.Pool object, and use a while loop to keep processing the tasks from dispatcher. 

Inside the loop body, worker will fetch a task by sending a structured message to the dispatcher, showing that it needs a task, when the task returned, it retrieves the task, and passes the task to the execute_task function, where the task will be executed, and update the status and result. Then the updated task object will be sent to the dispatcher, and receive a received response from the dispatcher.

## Push Workers

A push worker instance will firstly initiate a DEALER socket and assign its identity as the worker id of current worker. After connecting the socket to given dispatcher url from command line, the push worker will send message to the ROUTE socket in dispatcher to register. Then the worker will initiate a multiprocessing.Pool object, and use a while loop to keep processing the tasks from dispatcher. 

Inside the loop body, worker will fetch a task directly from the dispatcher, and it retrieves the task inside the response, and passes the task to the execute_task function, where the task will be executed, and update the status and result. Then the updated task object will be sent to the dispatcher. Here we do not need to receive a message before the next iteration, as the Router in dispatcher will reply with another task directly in the next iteration to show that they have received previous task result.

## Error Handling
We designed a multiple-layered error handling mechanism. 

### HTTP Request Error
The app.exception_handler in web_server.py will try to handle all the exceptions in the entire system. They will catch the exception raised from not only FastAPI system (400 Bad Request for example), but also from dispatcher and workers. And then it will return a JSON response to the client, with given status code, showing what kind of exception has been catched while registering/executing the function/task.

### Execution Error
In task dispatcher and all kinds of the workers, if a code snippet is prone to throw an exception, and is crucial to error diagnosis, we will place the code snippet in a try-except branch, catch the exceptions, and incorporate them into the Task object to be sent to FastAPI for further handling.

## Limitations

Our current version of Faas Platform has the following limitations:

### Lack of recovery for failing worker instances
In our implementation, we only catch failing worker instance exceptions, but did not try to initiate new instances to recover that. Also, we did not have remedy for lost tasks on the failing worker by reassigning them to other workers.

### Limited throughput via Redis
We are using the same Redis connection pool in db.py, which is not assigned with band-width and maximum connections. The availability of our Redis database will be the bottleneck and place constraints on performance of the whole system.

### No archive for historical tasks / function records
As more functions and tasks are registered, the memory usage of Redis will increase. But in our current version, the Redis system only runs on a single machine. It will be better off if we utilize a distributed Redis system, or archive some completed tasks in other databases on disk in future versions.

### Insufficient load balance over the workers