import redis
from redis import ConnectionPool

pool = ConnectionPool(host='localhost', port=6379, db=0)
kvdb = redis.Redis(connection_pool=pool)