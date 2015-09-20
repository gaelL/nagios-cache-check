#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Gaël Lambert (gaelL) <gael.lambert@netwiki.fr>
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

import unittest2 as unittest

import mox
import stubout
import os, sys
import mock
from mock import call
import subprocess
import cache_check

class TestCase(unittest.TestCase):
    def setUp(self):
        super(TestCase, self).setUp()
        self.mox = mox.Mox()
        self.stubs = stubout.StubOutForTesting()

    def tearDown(self):
        self.mox.UnsetStubs()
        self.stubs.UnsetAll()
        self.stubs.SmartUnsetAll()
        self.mox.VerifyAll()
        super(TestCase, self).tearDown()


class Cache_check_TestCase(TestCase):

    def setUp(self):
        super(Cache_check_TestCase, self).setUp()

    def tearDown(self):
        super(Cache_check_TestCase, self).tearDown()

    def test_runcmd_interval_is_respected(self):
        with mock.patch('time.time', mock.MagicMock()) as time_mock:
            # Cache empty so interval respected
            time_mock.return_value = 50
            cache = {}
            result = cache_check._runcmd_interval_is_respected(cache=cache,
                                                               interval=10)
            self.assertTrue(result)

            # Interval not respected
            time_mock.return_value = 50
            cache = {'last_check': 45}
            result = cache_check._runcmd_interval_is_respected(cache=cache,
                                                               interval=10)
            self.assertFalse(result)

            # Cache expired
            time_mock.return_value = 61
            cache = {'last_check': 50}
            result = cache_check._runcmd_interval_is_respected(cache=cache,
                                                               interval=10)
            self.assertTrue(result)

    def test_cache_is_expired(self):
        with mock.patch('time.time', mock.MagicMock()) as time_mock:
            # Cache empty so expired
            time_mock.return_value = 50
            cache = {}
            result = cache_check._cache_is_expired(cache=cache, expire=10)
            self.assertTrue(result)

            # Cache not expired
            time_mock.return_value = 50
            cache = {'last_check': 45}
            result = cache_check._cache_is_expired(cache=cache, expire=10)
            self.assertFalse(result)

            # Cache expired
            time_mock.return_value = 61
            cache = {'last_check': 50}
            result = cache_check._cache_is_expired(cache=cache, expire=10)
            self.assertTrue(result)

    def test_get_cache(self):

        # No cache file
        with mock.patch('__builtin__.open',
                        mock.mock_open(mock=mock.Mock(side_effect=IOError)),
                        create=True) as file_mock:
            result = cache_check._get_cache('foo.json')
            self.assertEquals(result, None)

        with mock.patch('__builtin__.open', mock.mock_open(), create=True) as file_mock:
            # Non json data in cache
            file_mock.return_value.read.return_value = 'not json data'
            result = cache_check._get_cache('foo.json')
            self.assertEquals(result, None)

            # Valid json data in cache
            file_mock.return_value.read.return_value = '{"foo": "bar"}'
            result = cache_check._get_cache('foo.json')
            self.assertEquals(result, {'foo': 'bar'})

    def test_set_cache(self):

        with mock.patch('os.path.isdir', mock.MagicMock()) as isdir_mock, \
             mock.patch('os.mkdir', mock.Mock(side_effect=OSError)):
             #mock.patch('os.mkdir', mock.MagicMock(mock=mock.Mock(side_effect=OSError))):
            # Dir not exist and fail to create it
            isdir_mock.return_value = False
            result = cache_check._set_cache('foo.json', {})
            self.assertEquals(result, False)

        with mock.patch('__builtin__.open',
                        mock.mock_open(mock=mock.Mock(side_effect=IOError)),
                        create=True) as file_mock, \
                  mock.patch('os.path.isdir', mock.MagicMock()) as isdir_mock, \
                  mock.patch('os.mkdir', mock.MagicMock()) as mkdir_mock:
            # Dir exist but unable to write file
            isdir_mock.return_value = True
            result = cache_check._set_cache('foo.json', {})
            self.assertEquals(result, False)


        with mock.patch('__builtin__.open', mock.mock_open(), create=True) as file_mock, \
                  mock.patch('os.path.isdir', mock.MagicMock()) as isdir_mock, \
                  mock.patch('os.mkdir', mock.MagicMock()) as mkdir_mock:
            handle = file_mock()
            # Dir not exist call mkdir and write file
            isdir_mock.return_value = False
            result = cache_check._set_cache('foo.json', {'foo': 'bar'})
            mkdir_mock.assert_called_with(cache_check.CACHE_DIR)
            file_mock.assert_called_with('%s/foo.json' % cache_check.CACHE_DIR, 'w')
            handle.write.assert_called_once_with('{"foo": "bar"}')
            self.assertEquals(result, True)

    def test_run_cmd(self):

        class Fake_Process(object):
            def wait(self):
                return 42
            def communicate(self):
                return 'out', 'err'

        with mock.patch('subprocess.Popen', mock.MagicMock(), create=True) as popen_mock:
            popen_mock.return_value = Fake_Process()
            result = cache_check._run_cmd('foo', 10)
            self.assertEquals(result, (42, 'out', 'err'))
            popen_mock.assert_called_with('timeout 10 foo', shell=True,
                                          stderr=-1, stdout=-1)

    def test_do_check(self):
        with mock.patch('cache_check._get_cache', mock.MagicMock()) as get_cache_mock, \
                  mock.patch('cache_check._set_cache', mock.MagicMock()) as set_cache_mock, \
                  mock.patch('cache_check._cache_is_expired', mock.MagicMock()) as cache_expired_mock, \
                  mock.patch('cache_check._runcmd_interval_is_respected', mock.MagicMock()) as cache_runcmd_interval_is_respected:
            # Empty cache file but can write UNKNOWN
            get_cache_mock.return_value = None
            set_cache_mock.return_value = True
            result = cache_check.do_check('foo.json', 60, -1)
            self.assertEquals(result, (cache_check.UNKNOWN, result[1], True))
            # Empty cache file unable to write CRITICAL
            get_cache_mock.return_value = None
            set_cache_mock.return_value = False
            result = cache_check.do_check('foo.json', 60, -1)
            self.assertEquals(result, (cache_check.CRITICAL, result[1], False))
            # Cache expired CRITICAL
            cache_expired_mock.return_value = True
            get_cache_mock.return_value = {'foo': 'bar'}
            result = cache_check.do_check('foo.json', 60, -1)
            self.assertEquals(result[0], cache_check.CRITICAL)

            # Cache ok, command running : don't run command exit in cache
            # And interval not respected
            cache_expired_mock.return_value = False
            cache_runcmd_interval_is_respected.return_value = False
            get_cache_mock.return_value = {'refresh_launched': True,
                                           'stdout': 'foo',
                                           'stderr': 'bar',
                                           'return_code': cache_check.OK,
                                            }
            result = cache_check.do_check('foo.json', 60, -1)
            self.assertEquals(result, (cache_check.OK, 'foo - bar', False))

            # Cache unknown return code, command not running
            # but interval not respected : don't run command
            cache_expired_mock.return_value = False
            cache_runcmd_interval_is_respected.return_value = False
            get_cache_mock.return_value = {'refresh_launched': False,
                                           'return_code': 42,
                                            }
            result = cache_check.do_check('foo.json', 60, 10)
            self.assertEquals(result, (cache_check.UNKNOWN, result[1], False))

            # Cache unknown return code, command not running : run command
            cache_expired_mock.return_value = False
            cache_runcmd_interval_is_respected.return_value = True
            get_cache_mock.return_value = {'refresh_launched': False,
                                           'return_code': 42,
                                            }
            result = cache_check.do_check('foo.json', 60, -1)
            self.assertEquals(result, (cache_check.UNKNOWN, result[1], True))

    def test_exit_and_refresh_cache(self):

        class Fake_Time(object):
            _times = []
            def time(self):
                return self._times.pop()

        with mock.patch('cache_check.time', Fake_Time()) as time_mock, \
                mock.patch('cache_check._detach_process', mock.MagicMock()) as detach_process_mock, \
                mock.patch('cache_check._get_cache', mock.MagicMock()) as get_cache_mock, \
                mock.patch('cache_check._set_cache', mock.MagicMock()) as set_cache_mock, \
                mock.patch('cache_check._run_cmd', mock.MagicMock()) as run_cmd_mock:

            # cache already exist just change refresh value.
            # Command return code 42 and some stdout and stderr
            # _detach_process called once
            # call _set_cache with _run_cmd output
            get_cache_mock.return_value = {'refresh_launched': False}
            time_mock._times = [1000000051,1000000001]
            run_cmd_mock.return_value = (42, 'foo', 'bar')
            
            cache_check._exit_and_refresh_cache('cmd', 1, 'foo.json', 0)

            calls = [call('foo.json', {'refresh_launched': True}),
                     call('foo.json',
                          {'refresh_launched': False,
                           'command': 'cmd',
                           'stderr': 'bar',
                           'timeout': 1,
                           'stdout': 'foo',
                           'last_check': 1000000051,
                           'last_runtime': 50.0,
                           'return_code': 42})]

            set_cache_mock.assert_has_calls(calls)
            detach_process_mock.assert_called_once_with(parent_exit_code=0)
            run_cmd_mock.assert_called_once_with('cmd', 1)

        with mock.patch('cache_check.time', Fake_Time()) as time_mock, \
                mock.patch('cache_check._detach_process', mock.MagicMock()) as detach_process_mock, \
                mock.patch('cache_check._get_cache', mock.MagicMock()) as get_cache_mock, \
                mock.patch('cache_check._set_cache', mock.MagicMock()) as set_cache_mock, \
                mock.patch('cache_check._run_cmd', mock.MagicMock()) as run_cmd_mock:

            # Cache None generate new cache with UNKNOWN
            get_cache_mock.return_value = None
            time_mock._times = [1000000051, 1000000011, 1000000001]
            run_cmd_mock.return_value = (42, 'foo', 'bar')
            
            cache_check._exit_and_refresh_cache('cmd', 1, 'foo.json', 0)

            calls = [call('foo.json',
                          {'refresh_launched': True,
                           'command': 'cmd',
                           'stderr': '',
                           'timeout': 1,
                           'stdout': '',
                           'last_check': 1000000001,
                           'last_runtime': 0,
                           'return_code': cache_check.UNKNOWN}),
                     call('foo.json',
                          {'refresh_launched': False,
                           'command': 'cmd',
                           'stderr': 'bar',
                           'timeout': 1,
                           'stdout': 'foo',
                           'last_check': 1000000051,
                           'last_runtime': 40.0,
                           'return_code': 42})]

            set_cache_mock.assert_has_calls(calls)
            detach_process_mock.assert_called_once_with(parent_exit_code=0)
            run_cmd_mock.assert_called_once_with('cmd', 1)

if __name__ == '__main__':
    unittest.main()
