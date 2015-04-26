#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml
import os
import git
from docopt import docopt

__authors__  = "Thomas Maurice"
__email__    = "thomas@maurice.fr"
__version__  = "0.1a"
__license__  = "GPL"
__status__   = "Developement"
__doc__      = """synchrogit.py: Synchronizes git repositories

Usage:
    synchrogit.py [--config FILE]

Options:
    -c --config FILE        configuration file to use [default: git.yml]
    -h --help               prints out this help

"""

class Repository():
    """Represents a repository object
    
    This class is intended to provide an interface built on
    the top of gitpython's interface, in order to be more suited
    to what it is intended to do, i.e checkout special branches
    in a defined directory, without having to deal with the nightmare
    of GitPython's API"""
    
    def __init__(self, name, repo_dict):
        """Creates a new repository object"""
        self.name = name
        self.url  = repo_dict['url']
        self.branches = repo_dict['branches']
    
    def __str__(self):
        """Textual representation of the object"""
        return self.name + " " + self.url + ":" + str(self.branches.keys())
    
    def clone_branch(self, branch, destination):
        """clones the given branch
        
        This function will clone the given branch to the given
        destination. If the given destination path does not exist
        it will be created. Upon fail exceptions may be raised.
        
        branch & destination are both strings
        """
        print " * Cloning %s:%s" % (self.name, branch)
        repo = None
        if not os.path.exists(destination):
            print "  + Destination directory non existant, creating it"
            try:
                os.makedirs(destination)
            except OSError as exce:
                print "  ! Unable to create destination %s: %s" % (destination, str(exce))
                raise
        try:
            print "  + Cloning the repository"
            repo = git.Repo.clone_from(self.url, destination, branch=branch, single_branch=True)
        except Exception as exce:
            print "  ! Error, unable to clone repository : %s" % str(exce)
            raise
        
        return True, repo.remotes.origin.refs[branch].commit
    
    def branch_update(self, branch, destination):
        """updates the given branch into the destination folder
        
        Both branch and destination are strings. If the update fails
        for any reason, exceptions will be raised.
        """
        repo = None
        print " * Updating %s:%s" % (self.name, branch)
        try:
            repo = git.Repo(destination)
            repo.remotes.origin.fetch()
        except Exception as exce:
            print "  ! Error, fetch failed : %s" % str(exce)
            raise
        
        remote_ref = repo.remotes.origin.refs[branch].commit
        local_ref = repo.branches[branch].commit
        
        print "  * Remote is at %s" % remote_ref.hexsha[:10]
        
        if repo.is_dirty():
            print "  - Local copy has changes, discarding them"
            try:
                repo.head.reset(index=True, working_tree=True)
            except Exception as exce:
                print "  ! Reset of local copy failed : %s" % str(exce)
                raise
                
        if local_ref != remote_ref:
            print "  * Local copy is out of date, pulling latest"
            try:
                repo.remotes.origin.pull()
                updated = True
            except Exception as exce:
                print "  ! Pull of remote copy failed : %s" % str(exce)
                raise
        else:
            print "  * Local copy is in sync at %s" % (local_ref.hexsha[:10])
        
        return True, local_ref, remote_ref
    
    def branch_exists(self, destination):
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
    args = docopt(__doc__)
    config = {}
    try:
        print " - Parsing configuration file %s" % (args['--config'])
        conf_file = open(args['--config'], 'r')
        config = yaml.load(conf_file)
        conf_file.close()
    except IOError as exce:
        print " ! Error", str(exce)
        raise SystemExit(1)
    except Exception as exce:
        print " ! Error while parsing config:", str(exce)
    
    repositories = config['repositories']
    for r in repositories:
        repo_dict = repositories[r]
        
        rep = Repository(r, repo_dict)
        for branch in rep.branches:
            try:
                rep.process_branch(branch)
            except:
                print " ! Failed to process branch %s" % branch
