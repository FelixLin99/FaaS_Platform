# project-alex-felix

## /

### requirements.txt 
Python dependencies for the Faas platform project

### .gitignore 
List of files and directories to ignore in version control

### README.md 
Project documentation and instructions

## web_server/

### web_server.py 
End points and error handlers for Faas REST API service

### web_server_utils.py 
Utility functions and business logics for function registration and execution

## tasks/

### task_dispatcher.py 
Task dispatcher logic

### pull_worker.py
Pull worker logic

### push_worker.py
Push worker logic

## dependancies/
Public modules for data models and redis connection pool

### data_models.py
Classes for data models of functions

### redis.py
Redis connection pool

### serialize.py
Serialization and Deserialization functions

### exceptions.py
Self-defined exceptions

## tests/                   
Directory for unit tests

### test_web_service.py
APT tests and integration tests
