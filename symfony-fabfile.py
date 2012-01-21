from fabric.api import *
from fabric.colors import green, red
from fabric.contrib.console import confirm
import os

# Configuration for the current project
# Change these settings
config = {
   'project': 'project',
   'repository': 'repository',
   'symfony_dir': os.getenv('HOME')+'/Developpement/symfony/1.4',
   'samples': { 
        'config/databases.yml':  ['config/databases.sample.yml', 'config/databases.yml.sample'],
        'config/properties.ini': ['config/properties.ini.sample', 'config/properties.sample.ini'],
    },
    'db': {
        'user': 'symfony',
        'password': 'symfony',
        'name': 'db_name',
        'name_test': 'db_name_test',
    },
}

# define roles host
env.roledefs = {
    'test': ['host'],
    'prod': ['host'],
}

# define ssh keys
home = os.getenv("HOME")
keys = [home + '/.ssh/run-deploy', home + '/.ssh/id_rsa']
env.key_filename = [key for key in keys if os.access(key, os.R_OK)]

# Install the project
@task
def install(interactive=True):
    print(green('Installation of %s' % config['project'], True))
    _copy_samples()
    if interactive is True :
        config['db']['user'] = prompt('Mysql user:', default='root')
        config['db']['password'] = prompt('Mysql user password:', default='root')
        config['db']['name'] = prompt('Mysql database name:', default='symfony')
        config['db']['name_test'] = prompt('Mysql test database name:', default='symfony_test')
    _create_db()
    _symfony_init()

# Copy samples
# Samples are configured in the samples var
def _copy_samples():
    for name, files in config['samples'].iteritems():
        for sample in files:
            if os.path.exists(sample):
                if os.path.exists(name):
                    print(green('Remove %s' % name))
                    if env.host is None:
                        local('rm %s' % name)
                    else:
                        run('rm %s' % name)
                print(green('Copy %s into %s' % (sample, name)))
                if env.host is None:
                    local('cp %s %s' % (sample, name))
                else:    
                    run('cp %s %s' % (sample, name))

# Create a user for the database
def _create_db():
    print(green('Configure database (coming soon)'))
    sql = """
GRANT USAGE ON * . * TO '#db.user#'@'localhost' IDENTIFIED BY '#db.password#';
CREATE DATABASE IF NOT EXISTS `#db.name#` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
GRANT ALL PRIVILEGES ON `#db.name#` . * TO  '#db.user#'@'localhost';
CREATE DATABASE IF NOT EXISTS `#db.name_test#` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
GRANT ALL PRIVILEGES ON `#db.name_test#` . * TO  '#db.user#'@'localhost';
FLUSH PRIVILEGES;
"""
    db = config['db']
    sql = sql.replace('#db.user#', db['user'])
    sql = sql.replace('#db.password#', db['password'])
    sql = sql.replace('#db.name#', db['name'])
    sql = sql.replace('#db.name_test#', db['name_test'])

    with settings(warn_only=True):
        if env.host is None:
            result = local('mysql -u%s -p < %s' % (db['user'], sql), True)
        else:
            result = run('mysql -u%s -p < %s' % (db['user'], sql), True)
    if result.failed:
        print(red('User creation failed', True))

def _symfony_init():
    if not os.path.exists('lib/vendor/symfony'):
        if env.host is None:
            local('cd lib/vendor && ln -s %s symfony' % config['symfony_dir']) 
        else:
            run('svn co http://svn.symfony-project.com/branches/1.4 lib/vendor/symfony')
        
    if env.host is None:
        local('php symfony doctrine:build --all-classes -q')
        local('php symfony cc -q')
        local('php symfony plugin:publish-assets -q')
    else:    
        run('php symfony doctrine:build --all-classes -q')
        run('php symfony cc -q')
        run('php symfony plugin:publish-assets -q')
