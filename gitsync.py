#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml
import os
import git
from docopt import docopt

__doc__ = """synchrogit.py: Synchronizes git repositories

Usage:
    synchrogit.py [--config FILE]

Options:
    -c --config FILE        configuration file to use [default: git.yml]
    -h --help               prints out this help

"""

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
        branches = repo_dict['branches'].keys()
        for branch in branches:
            print " * Syncing %s:%s" % (r, branch)
            destination = repo_dict['branches'][branch]['destination']
            updated = False
            cloned = False
            if not os.path.exists(destination):
                print "  + Destination directory non existant, creating it"
                try:
                    os.makedirs(destination)
                except OSError as exce:
                    print "  ! Unable to create destination %s: %s" % (destination, str(exce))
                    continue
                try:
                    print "  + Cloning the repository"
                    repo = git.Repo.clone_from(repo_dict['url'], destination, branch=branch, single_branch=True)
                    cloned = True
                except Exception as exce:
                    print "  ! Error, unable to clone repository : %s" % str(exce)
                    continue
            
            print "  + Fetching update information"
            
            try:
                repo = git.Repo(destination)
                repo.remotes.origin.fetch()
            except Exception as exce:
                print "  ! Error, fetch failed : %s" % str(exce)
                continue
            
            remote_ref = repo.remotes.origin.refs[branch].commit
            local_ref = repo.branches[branch].commit
            
            print "  * Remote is at %s" % remote_ref.hexsha[:10]
            
            if repo.is_dirty():
                print "  - Local copy has changes, discarding them"
                try:
                    repo.head.reset(index=True, working_tree=True)
                    updated = True
                except Exception as exce:
                    print "  ! Reset of local copy failed : %s" % str(exce)
                    continue
                    
            if local_ref != remote_ref:
                print "  * Local copy is out of date, pulling latest"
                try:
                    repo.remotes.origin.pull()
                    updated = True
                except Exception as exce:
                    print "  ! Pull of remote copy failed : %s" % str(exce)
                    continue
            else:
                print "  * Local copy is in sync at %s" % (local_ref.hexsha[:10])
                    
            if updated:
                print "  * Updated from %s to %s (%s)" % (local_ref.hexsha[:10], remote_ref.hexsha[:10], remote_ref.summary)
                
            if cloned:
                print "  * Cloned from %s (%s)" % (remote_ref.hexsha[:10], remote_ref.summary)
        
