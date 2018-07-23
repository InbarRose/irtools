#! /usr/bin/env python

# This is a file that is needed for the package,
# it knows what machine / distribution we are running on
# it contains many of the constants and does some monkey patching to the logging module to add a trace level.
# it defines the directories that we will use

# Standard Imports
import os
import sys
import platform
import socket
import logging

# platform and OS variables
running_on_windows = bool(sys.platform == 'win32')
running_on_linux = not running_on_windows
current_hostname = platform.node() or socket.gethostname()
# linux variables
linux_distribution = platform.linux_distribution()
linux_distribution_name = linux_distribution[0].lower()
running_on_centos = 'centos' in linux_distribution_name
running_on_debian = 'debian' in linux_distribution_name
running_on_ubuntu = running_on_debian or 'ubuntu' in linux_distribution_name
running_on_suse = 'suse' in linux_distribution_name

# ====================================================== LOGGING! ======================================================
# change WARNING to WARN
# overwrites default "WARNING" output for nice logging level names
logging.addLevelName(logging.WARNING, 'WARN')

# the logging date time format
log_datetime_format = '%Y-%m-%d %H:%M:%S'

# Logging fixes to add "trace" level using monkey-patch method.
TRACE_LOG_LEVEL = 9
logging.TRACE = TRACE_LOG_LEVEL
logging.addLevelName(TRACE_LOG_LEVEL, 'TRACE')


#  monkey patch to add "trace" level to logs so that log.trace() works.
def trace(self, message, *args, **kws):
    if self.isEnabledFor(TRACE_LOG_LEVEL):
        self._log(TRACE_LOG_LEVEL, message, args, **kws)  # Yes, logger takes its '*args' as 'args'.


logging.Logger.trace = trace  # add the new function to the logger class
# ====================================================== LOGGING! ======================================================

# common directories
tools_dir = os.path.dirname(os.path.abspath(__file__))
init_working_directory = os.getcwd()  # the directory that the user was in when this code was initialized

# default artifact and log dirs
artifact_dir = os.path.join(init_working_directory, 'artifact')  # to store files related to tools used
log_dir = os.path.join(init_working_directory, 'log')  # to store logs of tool usage
