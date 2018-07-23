# irtools

A collection of useful tools for Automation, Devops, or anything really

## What is it?

A set of tools that I find myself using often.
Compiled over many years of use, gathered here and organized.

## Installing with pip

`pip install git+git://github.com/InbarRose/irtools#egg=irtools`

## Usage

To use the tools, you simply do:

`from irtools import *`

* This will gauruntee that you have the optimal situation, where you can access `utils` from your code. 
* It will also make sure that the logging module has been monkey patched with the new `trace` level. (important when running on commandline or with logging enabled)

When running from command line, you should include a call to `utils.logging_setup()` to make sure the logging is setup to work correctly for all the utils.

## Quickstart Examples

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
# content must be able to be converted to string, (if contents is a list of strings uses writelines() to mirror utils.read_file)
path_written = utils.write_file('/path/to/write/file', content)
print path_written   # returns the path that was written
```
```
/path/to/write/file
```

More examples in the [examples folder](examples).

## Authors / Creators / Credits

* **Inbar Rose** - *Owner* - [InbarRose](https://github.com/InbarRose)

## Note about code included or copied from external sources

Throughout the years I have compiled this set of utilities, most of it is written by me (Inbar) But some of it is copied from other sources, everywhere I have copied code I have included a link to the source, and where possible the type of license or a note about the author. If you believe I have made an error, or something I have included is wrong or needs updating, please let me know. It is not my intention to steal or cheat or claim work as my own, and if you dispute my using of your code, I will happily remove it. In some cases I made slight modifications to code mostly for readability, but in some cases I made modifications to enhance capabilities. Again, if anyone has a problem with anything I have done, please let me know. Thanks.

## Future Plans

1. I plan to increase the number of examples to try to cover each util lib.

2. I plan to improve documentation and add additional comments for increased flow readability

3. I plan to include additional tools in the future, not just a set of utils, but also powerful classes to manage common DevOps/Automation challanges...

   1. TaskManager - *To optimize running tasks in parallel or in a specific order*
   2. JsonLoader - *To make reading and writing class structures from JSON easy*
   3. RestfulAPI - *To enhance the ability to use and debug restful interface using requests*
   4. And More.. - *I have a large collection of tools to release*

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
