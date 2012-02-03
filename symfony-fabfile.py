from fabric.api import *
from fabric.colors import green, red
from fabric.contrib.console import confirm
import os
from ConfigParser import ConfigParser
import yaml
import re
import getpass

# define roles host
env.roledefs = {
    'test': ['host'],
    'prod': ['host'],
}

# define ssh keys
home = os.getenv("HOME")
keys = [home + '/.ssh/run-deploy', home + '/.ssh/id_rsa']
env.key_filename = [key for key in keys if os.access(key, os.R_OK)]

@task
def install(interactive=True, tag=None, config_file='config/properties.ini'):
    """ 
    Installs the project
    """
    copy_sample(config_file)
    config = parse_config(config_file)
    #print(config.get('symfony', 'name'))
    print(green('Installation of %s' % config.get('symfony','name'), True))
    if env.host is not None:
        print('Installing the project...')
        delete('.*', 'rf')
        delete('.git*', 'rf')
        git_clone(config.get('symfony', 'repository'))

    configure_db(config, interactive)
    create_db(config)
    symfony_install(config)
    print(green('Installation done.', True))

@task
@roles('test')
def deploy(tag=None, install=False):
    """ 
    Deploys the project
    """
    if tag is None:
        tag = get_last_tag()

    print(green('Deploying tag "%s"' % tag))

    # Connect to the remote server
    with cd(get_remote_path()):
        if install is not False:
            install(tag=tag, interactive=True)
        # update the project version
        git_fetch()
        git_checkout(tag)
        git_submodule_update()
        if install is False:
            symfony_install()
    print(green('Installation done.', True))

@task
def rebuild():
    """ 
    Clean the cache, rebuild and publish the assets of the project
    """
    symfony_clear_cache()
    symfony_build(only_classes=False)
    symfony_clean_model_files()
    symfony_publish_assets()

@task
def reset_test_data(config_file='config/properties.ini'):
    """ 
    Resets the test data of the project
    """
    copy_sample(config_file)
    config = parse_config(config_file)
    create_db(config)

    symfony_build()
    symfony_clear_cache()

@task
def run_tests():
    """ 
    Launches all the PHPunit tests
    """
    reset_test_data()
    do('phpunit')

def configure_db(config, interactive=False):
    """
    Configure the database configuration list.
    """
    # Read the databases.yml.sample to get the default values
    db_config = yaml.load(open(config.get('samples','database')+'.sample', 'r'))
    config.add_section('database')
    config.add_section('database_default')
    config.set('database_default', 'username', db_config['all']['doctrine']['param']['username'])
    config.set('database_default', 'password', db_config['all']['doctrine']['param']['password'])
    config.set('database_default', 'name', re.split("[;=]", db_config['all']['doctrine']['param']['dsn']).pop())
    config.set('database_default', 'name_test', re.split("[;=]", db_config['test']['doctrine']['param']['dsn']).pop())

    if interactive is True :
        config.set('database', 'username', prompt('Mysql user:', default=config.get('database_default', 'username')))
        config.set('database', 'password', getpass.getpass('Mysql user password: [%s]' % config.get('database_default', 'password')))
        config.set('database', 'name', prompt('Mysql database name:', default=config.get('database_default', 'name')))
        config.set('database', 'name_test', prompt('Mysql test database name:', default=config.get('database_default', 'name_test')))
    else:
        # Copy default values in the database section if not interactive.
        for key, value in config.items('database_default'):
            config.set('database', key, value)
    

def create_db(config):
    """
    Recreates the tables and generates the databases.yml file
    """
    # Creating user
    print(green('Creating database user'))
    sql = """GRANT USAGE ON * . * TO '#db.user#'@'localhost' IDENTIFIED BY '#db.password#';
CREATE DATABASE IF NOT EXISTS `#db.name#` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
GRANT ALL PRIVILEGES ON `#db.name#` . * TO '#db.user#'@'localhost';
CREATE DATABASE IF NOT EXISTS `#db.name_test#` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
GRANT ALL PRIVILEGES ON `#db.name_test#` . * TO  '#db.user#'@'localhost';
FLUSH PRIVILEGES;"""

    sql = sql.replace('#db.user#', config.get('database', 'username'))
    sql = sql.replace('#db.password#', config.get('database', 'password'))
    sql = sql.replace('#db.name#', config.get('database', 'name'))
    sql = sql.replace('#db.name_test#', config.get('database', 'name_test'))

    query_file_name = 'config/create_dbs.sql';
    query_file = open(query_file_name,'w')
    query_file.write(sql);
    query_file.close();

    with settings(warn_only=True):
        result = sql_load(user=config.get('database', 'username'), password=config.get('database', 'password'), sql=query_file_name)
    if result.failed:
        print(red('User creation failed', True))

    # Generating database file
    print(green('Generating database.yml file'))
    db_config = yaml.load(open(config.get('samples','database')+'.sample', 'r'))
    db_config['all']['doctrine']['param']['username'] = config.get('database', 'username')
    db_config['all']['doctrine']['param']['username'] = config.get('database', 'password')
    db_config['all']['doctrine']['param']['dsn'] = db_config['all']['doctrine']['param']['dsn'].replace(config.get('database_default', 'name'), config.get('database', 'name'))
    db_config['test']['doctrine']['param']['dsn'] = db_config['test']['doctrine']['param']['dsn'].replace(config.get('database_default', 'name_test'), config.get('database', 'name_test'))
    yaml.dump(db_config, open(config.get('samples','database'), 'w'), indent=2, default_flow_style=False)

def symfony_install(config):
    """
    Creates symbolic links / checkout symfony's SVN, build classes, clear cache and publish assets
    """
    if not os.path.exists('lib/vendor/symfony'):
        if env.host is None:
            local('cd lib/vendor && ln -s %s symfony' % config.get('symfony', 'dir')) 
        else:
            run('svn co http://svn.symfony-project.com/branches/1.4 lib/vendor/symfony')

    symfony_build()
    symfony_clear_cache()
    symfony_publish_assets()

def get_role():
    """
    Return the current role
    """
    if env.host in env.roledefs['test']:
        return 'test'
    else:
        return 'prod'

def get_last_tag():
    """
    Return the latest tag
    """
    git_fetch()
    return local('git tag -l | sort | tail -n1', True)

def get_remote_path():
    """
    Return the path to the remote server
    """
    return path[get_role()]

def copy_sample(file):
    """
    Checks if the file exists, if not, creates it from the <file>.sample file
    """
    if not os.path.exists(file):
        if not os.path.exists(file+'.sample'):
            abort(red(file+'.sample does not exists',True))

        copy(file+'.sample', file)
    else:
        print(green(file+' already exists',True))

def parse_config(file):
    """
    Reads the config file with the ConfigParser module
    """
    config = ConfigParser()
    config.read(file)
    return config

def do(*args, **kwargs):
    """
    Execute a command with the right method
    as the env is local or remote
    """
    if env.host is None:
        return local(*args, **kwargs)
    else:
        return run(*args, **kwargs)

def go(*args, **kwargs):
    """
    Execute cd or lcd depending of the host.
    """
    if env.host is None:
        lcd(*args, **kwargs)
    else:
        cd(*args, **kwargs)

def symfony_clear_cache(hard=False):
    """
    Clear the symfony cache
    """
    if hard is True:
        do('rm -rf cache/*')
    else:
        do('php symfony cc')

def symfony_build(only_classes=True, load=False, env='all'):
    """
    Run doctrine build command
    """ 
    options = ['--all-classes' if only_classes is True else '--all']
    if load is True:
        options.append('--and-load')
    options.append('--env=\'%s\'' % env)
    options.append('--no-confirmation')
    options.append('--quiet')
    do('php symfony doctrine:build %s' % ' '.join(options))

def symfony_publish_assets():
    """
    Publish assets
    """
    do('php symfony plugin:publish-assets')

def symfony_clean_model_files():
    """
    Clean model fils that no longer exists in YAML schema
    """
    do('php symfony doctrine:clean-model-files')

def git_clone(repository, path='.'):
    """
    Clone a repository in a specific path
    """
    do('git clone %s %s' % (repository, path))

def git_fetch():
    """
    Fetch a repository
    """
    do('git fetch --all')

def git_checkout(commit):
    """
    Checkout a commit, branch or a tag
    """
    do('git checkout -q %s' % commit)

def git_submodule_update():
   """
   Update submodules
   """
   do('git submodule update --init --recursive --quiet')

def sql_load(user, sql, password=''):
    """
    Load an sql file.
    """
    return do('mysql -u%s -p%s < %s' % (user, password, sql), capture=True)

def copy(source, target):
    """
    Copy a file or a folder in a target
    """
    do('cp %s %s' % (source, target))

def delete(path, options=''):
    """
    Delete a file or a directory.
    Add options to the rm command (rf for instance)
    """
    do('rm %s %s' % (options, path))
