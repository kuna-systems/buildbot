# This file is part of Buildbot.  Buildbot is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Buildbot Team Members

from __future__ import with_statement

import os
from twisted.trial import unittest
from buildbot.scripts import restart, stop, startup
from buildbot.test.util import dirs, misc

def mkconfig(**kwargs):
    config = dict(quiet=False, basedir=os.path.abspath('basedir'))
    config.update(kwargs)
    return config

class TestStop(misc.StdoutAssertionsMixin, dirs.DirsMixin, unittest.TestCase):

    def setUp(self):
        self.setUpDirs('basedir')
        with open(os.path.join('basedir', 'buildbot.tac'), 'wt') as f:
            f.write("Application('buildmaster')")
        self.setUpStdoutAssertions()

    def tearDown(self):
        self.tearDownDirs()

    # tests

    def test_restart_not_basedir(self):
        self.assertEqual(restart.restart(mkconfig(basedir='doesntexist')), 1)
        self.assertStdout('not a buildmaster directory')

    def test_restart_stop_fails(self):
        self.patch(stop, 'stop', lambda config, wait : 1)
        self.assertEqual(restart.restart(mkconfig()), 1)

    def test_restart_stop_succeeds_start_fails(self):
        self.patch(stop, 'stop', lambda config, wait : 0)
        self.patch(startup, 'start', lambda config : 1)
        self.assertEqual(restart.restart(mkconfig()), 1)

    def test_restart_succeeds(self):
        self.patch(stop, 'stop', lambda config, wait : 0)
        self.patch(startup, 'start', lambda config : 0)
        self.assertEqual(restart.restart(mkconfig()), 0)
        self.assertStdout('now restarting')

    def test_restart_succeeds_quiet(self):
        self.patch(stop, 'stop', lambda config, wait : 0)
        self.patch(startup, 'start', lambda config : 0)
        self.assertEqual(restart.restart(mkconfig(quiet=True)), 0)
        self.assertWasQuiet()
