#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=trailing-whitespace
# pylint: disable=bad-continuation

"""Copyright 2015 Thomas Maurice <thomas@maurice.fr>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.


# gitsync.py

This script provides a convenient way to synchronize different git repos at
a given branch into a given environment.

I personally developped it to keep my personnal website under version control,
where I have several git branches :
 * dev
 * testing
 * prod

So that each branch benefits from it's own dedicated set of files and so on.
"""

import yaml
import os
import git
import shlex
import signal
import time
import logging
from subprocess import Popen, PIPE
from docopt import docopt

__authors__ = "Thomas Maurice"
__email__ = "thomas@maurice.fr"
__version__ = "0.1a"
__license__ = "GNU/GPLv3"
__status__ = "Developement"
__help__ = """gitsync.py: Synchronizes git repositories

Usage:
    gitsync.py [--config FILE] [--log FILE]

Options:
    -c --config FILE        configuration file to use [default: git.yml]
    -l --log FILE           logs to this file, overrides the setting of
                            the yaml file
    -h --help               prints out this help
"""

def setup_logger(name, to_stdout=True, file_name=None):
    """Creates the logging object used by the script
    
    By defaults it prints information ton stdout, but
    you can tell it to print out information ton a file too
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'
    )
    
    # reset handlers
    for handler in logger.handlers:
        # Don't close stdout or stderr !
        if handler.__class__ != logging.StreamHandler:
            handler.stream.close()
        logger.removeHandler(handler)
    
    if file_name:
        fhandle = logging.FileHandler(file_name)
        fhandle.setLevel(logging.DEBUG)
        fhandle.setFormatter(formatter)
        logger.addHandler(fhandle)
    
    if to_stdout:
        chandle = logging.StreamHandler()
        chandle.setLevel(logging.DEBUG)
        chandle.setFormatter(formatter)
        logger.addHandler(chandle)
    
    return logger

LOGGER = setup_logger("gitsync")

class Repository(object):
    """Represents a repository object
    
    This class is intended to provide an interface built on
    the top of gitpython's interface, in order to be more suited
    to what it is intended to do, i.e checkout special branches
    in a defined directory, without having to deal with the nightmare
    of GitPython's API"""
    
    def __init__(self, name, repo_dict):
        """Creates a new repository object"""
        self.name = name
        self.url = repo_dict['url']
        self.branches = repo_dict['branches']
        self.repo_dict = repo_dict

    def __str__(self):
        """Textual representation of the object"""
        return self.name + " " + self.url + ":" + str(self.branches.keys())

    def clone_branch(self, branch, destination):
        """clones the given branch
        
        This function will clone the given branch to == None:
                    time.sleepthe given
        destination. If the given destination path does not exist
        it will be created. Upon fail exceptions may be raised.
        
        branch & destination are both strings
        """
        LOGGER.info(" * Cloning %s:%s", self.name, branch)
        repo = None
        
        # If the path does not exist, we create it
        if not os.path.exists(destination):
            LOGGER.info("  + Destination directory non existant, creating it")
            try:
                os.makedirs(destination)
            except OSError as exce:
                LOGGER.error(
                    "  ! Unable to create destination %s: %s",
                    destination,
                    str(exce)
                )
                raise
        # And now the cloning
        try:
            LOGGER.info("  + Cloning the repository in %s", destination)
            repo = git.Repo.clone_from(self.url, destination, branch=branch,
                single_branch=True)
            remote_ref = repo.remotes.origin.refs[branch].commit
            self.run_post_clone(branch, remote_ref)
            LOGGER.info(
                "  * Local copy at revision %s", remote_ref.hexsha[:10]
            )
        except Exception as exce:
            LOGGER.error(
                "  ! Error, unable to clone repository : %s",
                str(exce)
            )
            raise
        
        return True, repo.remotes.origin.refs[branch].commit

    def branch_update(self, branch, destination):
        """updates the given branch into the destination folder
        
        Both branch and destination are strings. If the update fails
        for any reason, exceptions will be raised.
        """
        repo = None
        LOGGER.info(" * Updating %s:%s", self.name, branch)
        # We try to open the repo
        try:
            repo = git.Repo(destination)
            repo.remotes.origin.fetch()
        except Exception as exce:
            LOGGER.error("  ! Error, fetch failed : %s", str(exce))
            raise
        
        # Calculate differences
        remote_ref = repo.remotes.origin.refs[branch].commit
        local_ref = repo.branches[branch].commit
        
        LOGGER.info("  * Remote is at %s", remote_ref.hexsha[:10])
        
        # We want to keep our repositories clean
        if repo.is_dirty():
            LOGGER.info("  - Local copy has changes, discarding them")
            try:
                repo.head.reset(index=True, working_tree=True)
            except Exception as exce:
                LOGGER.error("  ! Reset of local copy failed : %s", str(exce))
                raise
        
        # If we are not at the same commit, update shit
        if local_ref != remote_ref:
            LOGGER.info("  * Local copy is out of date, pulling latest")
            try:
                repo.remotes.origin.pull()
                repo.head.reset(index=True,
                    working_tree=True,
                    commit=remote_ref)
                self.run_post_update(branch, remote_ref)
            except Exception as exce:
                LOGGER.error("  ! Pull of remote copy failed : %s", str(exce))
                raise
        else:
            self.run_post_run(branch, remote_ref)
            LOGGER.info(
                "  * Local copy is in sync at %s", (local_ref.hexsha[:10])
            )
        
        # Return success :)
        return True, local_ref, remote_ref
    
    def run_post_run(self, branch, remote):
        """runs post run actions"""
        if not 'post_run' in self.repo_dict['branches'][branch]:
            return
        
        actions = self.repo_dict['branches'][branch]['post_run']
        env = {
            'destination': self.repo_dict['branches'][branch]['destination'],
            'branch'     : branch,
            'commit'     : remote.hexsha,
        }
        LOGGER.info("  - Running post run actions")
        for action in actions:
            self.run_action(action, env)
    
    def run_post_clone(self, branch, remote):
        """runs post clone actions"""
        if not 'post_clone' in self.repo_dict['branches'][branch]:
            return
        
        actions = self.repo_dict['branches'][branch]['post_clone']
        env = {
            'destination': self.repo_dict['branches'][branch]['destination'],
            'branch'     : branch,
            'commit'     : remote.hexsha,
        }
        LOGGER.info("  - Running post clone actions")
        for action in actions:
            self.run_action(action, env)
    
    def run_post_update(self, branch, remote):
        """runs post update actions"""
        if not 'post_update' in self.repo_dict['branches'][branch]:
            return
            
        actions = self.repo_dict['branches'][branch]['post_update']
        env = {
            'destination': self.repo_dict['branches'][branch]['destination'],
            'branch'     : branch,
            'commit'     : remote.hexsha,
        }
        LOGGER.info("  - Running post update actions")
        for action in actions:
            self.run_action(action, env)
    
    def run_action(self, action, env):
        """run the specified action
        
        actions are a list of dictionaties. The action is for now either
         * run
         * kill
         
        The run command opens a subprocess and runs the command. The kill action
        takes into input a pid file. Either relative or absolute. If the path
        is relative, it will be relative (i.e. concatenated) with the base dir
        we are working into.
        """
        try:
            ac_type = action.keys()[0].format(**env)
            action = action.values()[0].format(**env)
            LOGGER.info("  - Running action '%s %s'", ac_type, action)
            # If the user wants to run a command
            if ac_type == "run":
                command = shlex.split(action)

                process = Popen(command, stdout=PIPE, stderr=PIPE,
                    shell=False, cwd=env['destination'])
                
                while process.poll() == None:
                    time.sleep(0.1)
                    output = process.stdout.readlines()
                    
                    for line in output:
                        LOGGER.info("    run: %s", line.replace('\n', ''))

            # If the user wants to kill a PID retrieved from a pidfile
            elif ac_type == "kill":
                pid_file_dest = action
                if pid_file_dest[0] != '/':
                    pid_file_dest = "{dest}/{pid_file_dest}".format(
                        dest=env['destination'],
                        pid_file_dest=pid_file_dest
                    )
                pidfile = open(pid_file_dest, 'r')
                pid = int(pidfile.read())
                pidfile.close()
                try:
                    os.kill(pid, signal.SIGTERM)
                    LOGGER.info("  * Kill signal sent to pid %s", pid)
                except Exception as exce:
                    LOGGER.error("  ! Kill failed: %s", str(exce))
        except Exception as exce:
            LOGGER.error(" ! Action failed : %s", str(exce))
    
    def branch_exists(self, destination):
        """Returns whereas a .git directory exists
        
        TODO: Create a more valid test or so
        """
        return os.path.exists(os.path.join(destination, '.git'))

    def process_branch(self, branch):
        """processes the given branch
        
        'branch' shall be a dictionary filled with the appropriate
        values. The process function will dtermine wether the directory
        exists, and if not it will clone the repo into it. Otherwise
        it will attempt to update it."""
        
        # May reaise an IndexError in cas the branch does not exist
        branch_dict = self.branches[branch]
        if not self.branch_exists(branch_dict['destination']):
            self.clone_branch(branch, branch_dict['destination'])
        else:
            self.branch_update(branch, branch_dict['destination'])

if __name__ == "__main__":
    # pylint: disable=invalid-name
    args = docopt(__help__)
    config = {}
    try:
        LOGGER.info(" - Parsing configuration file %s", args['--config'])
        conf_file = open(args['--config'], 'r')
        config = yaml.load(conf_file)
        conf_file.close()
        log_stdout = True
        log_file = None
        if 'log_stdout' in config:
            log_stdout = config['log_stdout']
        if 'log_file' in config:
            log_file = config['log_file']
        # The command line argument overrides the default setting
        if args['--log'] != None:
            log_file = args['--log']
        LOGGER = setup_logger('gitsync', log_stdout, log_file)
    except IOError as exce:
        LOGGER.critical(" ! Error: %s", str(exce))
        raise SystemExit(1)
    except Exception as exce:
        LOGGER.error(" ! Error while parsing config: %s", str(exce))
    
    # To be sure to have rights. Otherwise Git could complain
    os.chdir('/tmp')
    
    repositories = config['repositories']
    for r in repositories:
        rep_dict = repositories[r]
        
        rep = Repository(r, rep_dict)
        for bra in rep.branches:
            try:
                rep.process_branch(bra)
            except Exception as e:
                LOGGER.error(" ! Failed to process branch %s : %s", bra, str(e))
