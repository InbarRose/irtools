# Examples for irtools

More examples in the [examples folder](examples).

## Examples for utils

Following are examples for some of the tools you will find in the `utils` module.

### Examples for iexec

```python
ret = utils.iexec('ping 8.8.8.8')  # using iexec you can run any command
```
```python
print ret.rc  # you can access the ExecResult to see the return code (rc)
```
```
0
```

```python
print ret.debug_output()  # ExecResult also includes many convenience functions
```
```
cmd: ping 8.8.8.8
rc: 0
start: 1532353723.38
start_datetime: 2018-07-23 16:48:43
time: 3.12999987602


Pinging 8.8.8.8 with 32 bytes of data:
Reply from 8.8.8.8: bytes=32 time=80ms TTL=120
Reply from 8.8.8.8: bytes=32 time=72ms TTL=120
Reply from 8.8.8.8: bytes=32 time=87ms TTL=120
Reply from 8.8.8.8: bytes=32 time=84ms TTL=120

Ping statistics for 8.8.8.8:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 72ms, Maximum = 87ms, Average = 80ms
```

```python
# can read a file easily and get contents
content = utils.read_file('/path/to/any/file', as_str=False, strip_newlines=False)
# can write files easily (creates any missing dirs in the path) 
# content must be able to be converted to string, 
# (if contents is a list of strings uses writelines() to mirror utils.read_file)
path_written = utils.write_file('/path/to/write/file', content)
print path_written   # returns the path that was written
```
```
/path/to/write/file
```

## Examples for kits

Following are examples for some of the tools you will find in the `kits` module.

### Examples for taskamanager
