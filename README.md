# This is ill conceived and bad. Never use this.

PLEASE DON'T USE THIS CODE, LEAVING HERE AS EXAMPLE TO MYSELF OF HOW NOT TO PROGRAM

The reason I think this code (while well intended) is bad is because it needlessly 
abstracts from the use of redis and only for the gain of some syntactic ease of use while adding lots of overhead.

It also makes it much harder to see and debug where and when your code is using redis, which is something
you want to be able to determine very easily.

TL;DR Some times it ok to have uglier code, and writing a few extra symbols here and there is not such a bad 
trade for clarity.

<3 owiewestside

# Usage

Defaults to connection on localhost:6379.

export 
`REDIS_HOST` and `REDIS_PORT` to override with custom settings


## Supported Redis Types:

* ZSET - `redis_types.SortedSet`
* SET - `redis_types.Set`
* HASH - `redis_types.Hash`
* LIST - `redis_types.List`
