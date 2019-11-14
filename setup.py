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

''' Install the SAS Scripting Wrapper for Analytics Transfer (SWAT) module '''

import contextlib
import glob
import io
import os
import pipes
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from setuptools.command.build_ext import build_ext
from setuptools import setup, find_packages, Extension

LIBSWAT_ROOT = 'gitlab.sas.com/kesmit/go-libswat'
GO_GET_FLAGS  = '-insecure'
GO_BUILD_FLAGS = ''


def get_file(fname):
    with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), fname),
                 encoding='utf8') as infile:
        return infile.read()


class BuildExtCommand(build_ext):
    ''' Custom build command for Go extension '''

    def build_extension(self, ext):
        ''' Build libswat.a before building the extension '''
        try:
            self._check_call(['go', 'version'], os.getcwd(), {},
                             stderr=getattr(subprocess, 'DEVNULL', None),
                             stdout=getattr(subprocess, 'DEVNULL', None))
        except subprocess.CalledProcessError:
            raise RuntimeError('The Go tools do not appear to be installed.  '
                               'Make sure that they are installed '
                               '(see https://golang.org) and that the go '
                               'command is in your system path.')

        try:
            self._check_call(['swig', '-version'], os.getcwd(), {},
                             stderr=getattr(subprocess, 'DEVNULL', None),
                             stdout=getattr(subprocess, 'DEVNULL', None))
        except subprocess.CalledProcessError:
            raise RuntimeError('SWIG does not appear to be installed.  '
                               'Make sure that it is installed '
                               '(see http://www.swig.org) and that the swig '
                               'command is in your system path.')

        platform = sys.platform.lower()
        if platform.startswith('win'):
            platform = 'win'
        elif platform.startswith('darwin'):
            platform = 'osx'
        else:
            platform = 'unix'

        with self._tmpdir() as tempdir:
            libswat_root = os.environ.get('LIBSWAT_ROOT', LIBSWAT_ROOT)
            src_path = os.path.join(tempdir, 'src')
            mod_path = os.path.join(tempdir, 'pkg', 'mod')
            libswat_a = os.path.join(src_path, 'libswat.a')
            if platform == 'win':
                root_path = os.path.join(src_path, libswat_root.replace('/', '\\'))
            else:
                root_path = os.path.join(src_path, libswat_root)

            os.makedirs(src_path)

            env = {str('GOPATH'): tempdir, str('GO111MODULE'): 'auto'}

            cmd = ['go', 'get', '-d'] + \
                  [x for x in os.environ.get('GO_GET_FLAGS', GO_GET_FLAGS).split() if x] + \
                  [libswat_root]
            try:
                self._check_call(cmd, src_path, env)
            except:
                pass
            try:
                self._check_call(cmd, src_path, env)
            except:
                pass

            # Set os x build target
            if platform == 'osx':
                plat = os.environ.get('PLAT', '-10.7-').split('-')
                if len(plat) > 1 and re.match(r'^\d+\.\d+', plat[1]):
                    env[str('MACOSX_DEPLOYMENT_TARGET')] = plat[1]
                # Use older compiler if available to support more versions of OSX
                if os.path.isfile('/usr/bin/gcc'):
                    env[str('CC')] = str('/usr/bin/gcc')

            # Run swig to get the Python interface file
            cmd = ['swig', '-outdir', src_path, '-python', '-builtin',
                   '-module', 'pyswat', '-o', os.path.join(src_path, 'pyswat.c'), 
                   os.path.join(root_path, 'swat.i')]
            self._check_call(cmd, root_path, env)

            ext.sources.append(os.path.join(src_path, 'pyswat.c'))

            cmd = ['go', 'build', '-buildmode=c-archive'] + \
                  [x for x in os.environ.get('GO_BUILD_FLAGS', GO_BUILD_FLAGS).split() if x] + \
                  ['-o', libswat_a]
            self._check_call(cmd, root_path, env)

            ext.extra_compile_args.append('-Wno-unused-variable')
            ext.extra_compile_args.append('-Wno-unused-label')
            ext.extra_compile_args.append('-Wno-unused-function')
            ext.extra_compile_args.append('-Wno-visibility')
            ext.extra_compile_args.append('-Wno-strict-prototypes')

            if root_path not in ext.include_dirs:
                ext.include_dirs.append(root_path)

            if libswat_a not in ext.extra_link_args:
                ext.extra_link_args.append(libswat_a)

            if platform == 'win':
                prefix = getattr(sys, 'real_prefix', sys.prefix)
                libs = ['-L%s' % os.path.join(prefix, 'libs'),
                        '-lpython%s%s' % tuple(sys.version_info[:2])]

                cmd = ['gcc'] + ext.sources + \
                      ext.extra_link_args + \
                      ['-D', 'MS_WIN64', '-O2'] + \
                      ['-I%s' % x for x in ext.include_dirs] + \
                      ['-I%s' % x for x in self.compiler.include_dirs] + \
                      ext.extra_compile_args + \
                      libs + ['-fpic', '-shared'] + \
                      ['-o', os.path.abspath(self.get_ext_fullpath(ext.name))]
                self._check_call(cmd, os.getcwd(), env)

                return

            build_ext.build_extension(self, ext)

    def _check_call(self, cmd, cwd, env, stdout=None, stderr=None):
        ''' Run command and check return value '''
        envparts = ['{}={}'.format(k, pipes.quote(v)) for k, v in sorted(tuple(env.items()))]
        sys.stderr.write('$ {}\n'.format(' '.join(envparts + [pipes.quote(p) for p in cmd])))
        subprocess.check_call(cmd, cwd=cwd, env=dict(os.environ, **env), stdout=stdout, stderr=stderr)

    @contextlib.contextmanager
    def _tmpdir(self):
        tempdir = tempfile.mkdtemp()
        try:
            yield tempdir
        finally:
            def err(action, name, exc):  # pragma: no cover (windows)
                ''' windows: can't remove readonly files, make them writeable! '''
                os.chmod(name, stat.S_IWRITE)
                action(name)
            shutil.rmtree(tempdir, onerror=err)


setup(
    zip_safe=False,
    name='swat',
    version='1.5.3-dev',
    description='SAS Scripting Wrapper for Analytics Transfer (SWAT)',
    long_description=get_file('README.md'),
    long_description_content_type='text/markdown',
    author='SAS',
    author_email='Kevin.Smith@sas.com',
    url='http://github.com/sassoftware/python-swat/',
    license='Apache v2.0 (SWAT)',
    packages=find_packages(),
    package_data={
        'swat': ['lib/*/*.*', 'tests/datasources/*.*'],
    },
    install_requires=[
        'pandas >= 0.18.0',
        'six >= 1.9.0',
        'requests',
    ],
    platforms='any',
#   python_requires='>=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Scientific/Engineering',
    ],
    cmdclass={
        'build_ext': BuildExtCommand,
    },
    ext_modules=[Extension('_pyswat', [])],
)
