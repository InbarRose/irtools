# irtools

A collection of useful tools for Automation, Devops, or anything really

## News:

> Now hosted on pypi !

https://pypi.org/project/py-irtools/

> Now with a Slack Channel!

https://py-irtools.slack.com

> Now with Travis CI

https://travis-ci.org/InbarRose/irtools

## What is it?

A set of tools that I find myself using often.
Compiled over many years of use, gathered here and organized.

## Installing with pip

> To get the most stable version (**recommended**) 

`pip install py-irtools`

> To get the development version

`pip install git+git://github.com/InbarRose/irtools@development#egg=irtools`

## Usage

To use the tools, you simply do:

`from irtools import *`

* This will gauruntee that you have the optimal situation, where you can access `utils` from your code. 
* It will also make sure that the logging module has been monkey patched with the new `trace` level. (important when running on commandline or with logging enabled)

When running from command line, you should include a call to `utils.logging_setup()` to make sure the logging is setup to work correctly for all the utils.

## Examples

```python
ret = utils.iexec('ping 8.8.8.8')  # using iexec you can run any command
```
See the rest of this example and more in the [quickstart examples file](examples/quickstart_examples.md)

More examples in the [examples folder](examples).

## Authors / Creators / Credits

* **Inbar Rose** - *Owner* - [InbarRose](https://github.com/InbarRose)

## Note about code included or copied from external sources

Throughout the years I have compiled this set of utilities, most of it is written by me (Inbar) But some of it is copied from other sources, everywhere I have copied code I have included a link to the source, and where possible the type of license or a note about the author. If you believe I have made an error, or something I have included is wrong or needs updating, please let me know. It is not my intention to steal or cheat or claim work as my own, and if you dispute my using of your code, I will happily remove it. In some cases I made slight modifications to code mostly for readability, but in some cases I made modifications to enhance capabilities. Again, if anyone has a problem with anything I have done, please let me know. Thanks.

## Future Plans

1. Add examples to try to cover each util lib and kit. (Assistance is welcomed)

2. Improve documentation and add additional comments for increased flow readability (Assistance is welcomed)

3. I plan to include additional tools in the future, not just a set of utils, but also powerful classes to manage common DevOps/Automation challanges...

   1. [x] ~~TaskManager~~ - *To optimize running tasks in parallel or in a specific order*
   2. [x] ~~JsonLoader~~ - *To make reading and writing class structures from JSON easy*
   3. [x] ~~RestfulAPI~~ - *To enhance the ability to use and debug restful interface using requests*
   4. [ ] And More.. - *I have a large collection of tools to release*

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
