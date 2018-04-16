# Usage

Defaults to connection on localhost:6379.

export 
`REDIS_HOST` and `REDIS_PORT` to override with custom settings


## Supported Redis Types:

* ZSET - `redis_types.SortedSet`
* SET - `redis_types.Set`
* HASH - `redis_types.Hash`
* LIST - `redis_types.List`
