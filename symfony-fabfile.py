from fabric.api import *
from fabric.colors import green, red
from fabric.contrib.console import confirm
import os

# Configuration for the current project
# Change these settings
config = {
   'project': 'Auto-Planning',
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

@task
def install():
    print(green('Installation of %s' % config['project'], True))
    _copy_samples()
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
                    local('rm %s' % name)
                print(green('Copy %s into %s' % (sample, name)))
                local('cp %s %s' % (sample, name))

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
        result = local('mysql -u%s -p < %s' % (db['user'], sql), True)
    if result.failed:
        print(red('User creation failed', True))

def _symfony_init():
    if os.path.exists('lib/vendor/symfony') == False:
        local('cd lib/vendor && ln -s %s symfony' % config['symfony_dir']) 
        
    local('php symfony doctrine:build --all-classes -q')
    local('php symfony cc -q')
    local('php symfony plugin:publish-assets -q')
