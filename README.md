# gitsync.py
A simple script to synchronize Git repositories

## Developement information

 * Maintainer  : Thomas Maurice &lt;thomas@maurice.fr&gt;
 * Version     : Alpha v0.1
 * Dev status  : Script is somehow working

## What is this ?
This is a script allowing you to manage versioned scripts across
computers. It is more evolved than a standard cron + git pull since
it allows you to specify what branch you want to have in the target
directory.

In the future you will be able to specify post clone/update commands
to run, to update webapps updates, deployments and so on.

## Configuration
Configuration is achieved with a Yaml file, which format is as
follows :

```yaml
# You have to declare everything into this root element
repositories:
    # Here we have a repo named "heimdall"
    # The name is just for you to see what's going on
    # It does not have any real incidence :)
    heimdall:
        # The url of the repo. Any valid git URL will do
        # i.e. git://git@... provided your system knows
        # where to find the approptiate ssh keys
        url: https://github.com/svartbergtroll/heimdall
        # Declare the branches you want to checkout here
        branches:
            # We want to check out the master branch
            # To checkout "feature", just put "feature" ;)
            master:
                # Destination where the repository will be
                # cloned !
                destination: /home/thomas/repos/master

```

And that's it !

If you called your config file `foo.yml` you have to invoke the
script with

```
./gitsync.py -c foo.yml```

Note that by default, the script will look for a file named `git.yml`
You should have the following output :
```
Syncing https://github.com/svartbergtroll/heimdall:master
 + Destination directory non existant, creating it
 + Cloning the repository
 + Fetching update information
 * Remote is at 350230004a
 * Local copy is in sync at 350230004a
 * Cloned from 350230004a (Merge branch 'master' of svartbergtroll.fr:heimdall)

```

It worked !

You can now have all the repos you want kept under branch version
control.
