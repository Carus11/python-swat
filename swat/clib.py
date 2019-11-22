#!/usr/bin/env python
# encoding: utf-8
#
# Copyright SAS Institute
#
#  Licensed under the Apache License, Version 2.0 (the License);
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

'''
SWAT C library functions

'''

from __future__ import print_function, division, absolute_import, unicode_literals

import glob
import os
import platform
import struct
import sys
from .utils.compat import PY3, WIDE_CHARS, a2u
from .exceptions import SWATError
try:
    _pyswat_loaded = False
    import _pyswat
    _pyswat_loaded = True
except ImportError:
    pass


# pylint: disable=E1101

def _pyswat_error():
    raise ValueError('Could not import import C extension.  This is likely due to '
                     'the SWAT package being installed from source rather than being '
                     'compiled. You can try using the REST interface as an alternative.')


def SW_CASConnection(*args, **kwargs):
    ''' Return a CASConnection (importing _pyswat as needed) '''
    if not _pyswat_loaded:
        _pyswat_error()
    return _pyswat.SW_CASConnection(*args, **kwargs)


def SW_CASValueList(*args, **kwargs):
    ''' Return a CASValueList (importing _pyswat as needed) '''
    if not _pyswat_loaded:
        _pyswat_error()
    return _pyswat.SW_CASValueList(*args, **kwargs)


def SW_CASFormatter(*args, **kwargs):
    ''' Return a CASFormatter (importing _pyswat as needed) '''
    if not _pyswat_loaded:
        _pyswat_error()
    return _pyswat.SW_CASFormatter(*args, **kwargs)


def SW_CASConnectionEventWatcher(*args, **kwargs):
    ''' Return a CASConnectionEventWatcher (importing _pyswat as needed) '''
    if not _pyswat_loaded:
        _pyswat_error()
    return _pyswat.SW_CASConnectionEventWatcher(*args, **kwargs)


def SW_CASDataBuffer(*args, **kwargs):
    ''' Return a CASDataBuffer (importing _pyswat as needed) '''
    if not _pyswat_loaded:
        _pyswat_error()
    return _pyswat.SW_CASDataBuffer(*args, **kwargs)


def SW_CASError(*args, **kwargs):
    ''' Return a CASError (importing _pyswat as needed) '''
    if not _pyswat_loaded:
        _pyswat_error()
    return _pyswat.SW_CASError(*args, **kwargs)


def InitializeTK(*args, **kwargs):
    ''' Initialize the TK subsystem (importing _pyswat as needed) '''
    if _pyswat is None:
        _import_pyswat()

    # Patch ppc linux path
    set_tkpath_env = 'ppc' in platform.machine() and 'TKPATH' not in os.environ
    if set_tkpath_env and args:
        os.environ['TKPATH'] = args[0]

    try:
        out = _pyswat.InitializeTK(*args, **kwargs)

    finally:
        if set_tkpath_env:
            del os.environ['TKPATH']

        # Override TKPATH after initialization so that other TK applications
        # won't be affected (Windows only).
        if sys.platform.lower().startswith('win') and 'TKPATH' not in os.environ:
            os.environ['TKPATH'] = os.pathsep

    return out


def errorcheck(expr, obj):
    '''
    Check for generated error message

    Parameters
    ----------
    expr : any
       Result to return if no error happens
    obj : SWIG-based class
       Object to check for messages

    Raises
    ------
    SWATError
       If error message exists

    Returns
    -------
    `expr` argument
       The result of `expr`

    '''
    if obj is not None:
        msg = obj.getLastErrorMessage()
        if msg:
            raise SWATError(a2u(msg, 'utf-8'))
    return expr
