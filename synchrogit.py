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
        conf_file = open(args['--config'], 'r')
        config = yaml.load(conf_file)
        conf_file.close()
    except IOError as exce:
        print "Error", str(exce)
        raise SystemExit(1)
    except Exception as exce:
        print "Error while parsing config:", str(exce)
    
    repositories = config['repositories']
    for r in repositories:
        repo_dict = repositories[r]
        updated = False
        print "Syncing %s" % repo_dict['url']
        if not os.path.exists(repo_dict['destination']):
            try:
                os.makedirs(repo_dict['destination'])
            except OSError as exce:
                print "%s" % str(exce)
                continue
            
            repo = git.Repo.clone_from(repo_dict['url'], repo_dict['destination'], branch=repo_dict['branch'], single_branch=True)
            updated = True
        
        # If it exists, update it
        repo = git.Repo(repo_dict['destination'])
        
        repo.remotes.origin.fetch()
                
        remote_ref = repo.remotes.origin.refs[repo_dict['branch']].commit
        local_ref = repo.branches[repo_dict['branch']].commit
        
        if repo.is_dirty():
            updated = True
            repo.head.reset(index=True, working_tree=True)
            
        if local_ref != remote_ref:
            updated = True
            repo.remotes.origin.pull()
            
        if updated:
            print "Updated to revision", remote_ref.hexsha[:10]
        
