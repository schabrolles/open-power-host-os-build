# Copyright (C) IBM Corp. 2016.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import os
import subprocess
import time


from lib import exception

LOG = logging.getLogger(__name__)


def retry_on_error(f, error=Exception, failure_handler=None,
                   max_retries=2, seconds_between_retries=5):
    """
    Retries running [f] when an exception occurs.
        Returns the result of [f] if it succeeds.

    Args:
        f: function to execute. Takes no arguments.

    Options:
        error: exception to watch for retry attempt.
        failure_handler: function be run when all retry attempts fail.
            Takes an exception as argument.
        max_retries: total number of retries to attempt.
        seconds_between_retries: time to wait until next retry.
    """
    assert max_retries >= 0

    def _reraise_exception(exc):
        raise exc
    
    failure_handler = failure_handler or _reraise_exception

    while True:
        try:
            return f()
        except error as exc:
            max_retries -= 1
            if max_retries < 0:
                return failure_handler(exc)
            time.sleep(seconds_between_retries)


def retry_on_timeout(f, is_timeout_error_f,
                     max_retries=2,
                     seconds_between_retries=5,
                     initial_timeout=120,
                     timeout_incr_f=lambda t: t * 2):
    """
    Retries running [f] when a timeout error is detected.
    Returns the result of [f] when it succeeds.

    Args:
        f: function to execute. Takes a timeout value as argument.
        is_timeout_error_f: function to check if the exception raised by [f]
            is a timeout error. Takes an exception as argument.

    Options:
        max_retries: total number of retries to attempt.
        seconds_between_retries: number of seconds to wait before retrying [f].
        initial_timeout: timeout value (seconds) of first [f] execution.
        timeout_incr_f: function that returns a new timeout value, based on the
            current one.
    """
    assert max_retries >= 0

    timeout = initial_timeout
    retries_left = max_retries

    while True:
        try:
            return f(timeout)
        except Exception as exc:
            if not is_timeout_error_f(exc):
                raise exc
   
            retries_left -= 1

            if retries_left < 0:
                raise exception.TimeoutError(
                    func_name=f.__name__,
                    num_attempts=max_retries + 1,
                    initial_timeout=initial_timeout,
                    final_timeout=timeout)

            timeout = timeout_incr_f(timeout)
            time.sleep(seconds_between_retries)


def set_http_proxy_env(proxy):
    LOG.info('Setting up http proxy: {}'.format(proxy))
    os.environ['https_proxy'] = proxy
    os.environ['http_proxy'] = proxy


def run_command(cmd, **kwargs):
    LOG.debug("Command: %s" % cmd)
    shell = kwargs.pop('shell', True)
    success_return_codes = kwargs.pop('success_return_codes', [0])

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, shell=shell, **kwargs)
    output, error_output = process.communicate()

    LOG.debug("stdout: %s" % output)
    LOG.debug("stderr: %s" % error_output)

    if process.returncode not in success_return_codes:
        raise exception.SubprocessError(cmd=cmd, returncode=process.returncode,
                                        stdout=output, stderr=error_output)

    return output
