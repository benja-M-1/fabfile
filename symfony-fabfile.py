from fabric.api import *
from fabric.colors import green, red
from fabric.contrib.console import confirm
import os
import ConfigParser

#Symfony commands
CMD_SF_CC = 'php symfony cc'
CMD_SF_BUILD_CLASSES = 'php symfony doctrine:build --all-classes'
CMD_SF_DOCTRINE_REBUILD_ALL = 'php symfony doctrine:build --all --and-load --no-confirmation'
CMD_SF_DOCTRINE_REBUILD_ALL_TEST = CMD_SF_DOCTRINE_REBUILD_ALL+' --env=test'
CMD_SF_DOCTRINE_CLEAN_MODEL_FILES = 'php symfony doctrine:clean-model-files'
CMD_SF_PUBLISH_ASSETS = 'php symfony plugin:publish-assets'
#PhpUnit commands
CMD_PHPUNIT_TEST_ALL = 'phpunit --log-junit=undercontrol.xml --configuration=phpunit.xml.dist --coverage-clover=clover.xml'
#GIT commands
CMD_GIT_CLONE = 'git clone %s .' #arg1 = repository
CMD_GIT_FETCH = 'git fetch'
CMD_GIT_CHECKOUT = 'git checkout -q %s' #arg1 = tag
CMD_GIT_SUBMODULE_UPDATE = 'git submodule update --init --recursive --quiet'
CMD_GIT_TAG = 'git tag %s' #arg1 = tag
CMD_GIT_TAG_D = 'git tag -d %s' #arg1 = tag
CMD_GIT_PUSH = 'git push -q %s :refs/tags/%s' #arg1 = remote, #arg2 = tag
#MySQL commands
CMD_SQL_EXECUTE_FILE = 'mysql -u%s -p < %s' #arg1 = sql file
#Shell commands
CMD_COPY = 'cp %s %s'
CMD_REMOVE_ALL = 'rm -rf * .git*'



# Configuration for the current project
# Change these settings
db = {
	'user': 'symfony',
	'password': 'symfony',
	'name': 'db_name',
	'name_test': 'db_name_test'
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
        run(CMD_REMOVE_ALL) 
        run(CMD_GIT_CLONE % config.get('symfony', 'repository'))

    if interactive is True :
        db['user'] = prompt('Mysql user:', default='root')
        db['password'] = prompt('Mysql user password:', default='root')
        db['name'] = prompt('Mysql database name:', default='symfony')
        db['name_test'] = prompt('Mysql test database name:', default='symfony_test')
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
        run(CMD_GIT_FETCH)
        run(CMD_GIT_CHECKOUT % tag)
        run(CMD_GIT_SUBMODULE_UPDATE)
        if install is False:
            _symfony_install()
    print(green('Installation done.', True))

@task
def rebuild():
    """ 
    Clean the cache, rebuild and publish the assets of the project
    """
    if env.host is not None:
        run(CMD_SF_CC)
        run(CMD_SF_DOCTRINE_REBUILD_ALL_TEST)
        run(CMD_SF_DOCTRINE_REBUILD_ALL)
        run(CMD_SF_DOCTRINE_CLEAN_MODEL_FILES)
        run(CMD_SF_CC)
        run(CMD_SF_PUBLISH_ASSETS)
    else:
        local(CMD_SF_CC)
        local(CMD_SF_DOCTRINE_REBUILD_ALL_TEST)
        local(CMD_SF_DOCTRINE_REBUILD_ALL)
        local(CMD_SF_DOCTRINE_CLEAN_MODEL_FILES)
        local(CMD_SF_CC)
        local(CMD_SF_PUBLISH_ASSETS)

@task
def reset_test_data(config_file='config/properties.ini'):
    """ 
    Resets the test data of the project
    """
    copy_sample(config_file)
    config = parse_config(config_file)
    create_db(config)
    
    if env.host is not None:
        run(CMD_SF_DOCTRINE_REBUILD_ALL+' --quiet')
        run(CMD_SF_CC+' --quiet')
    else:
        local(CMD_SF_DOCTRINE_REBUILD_ALL+' --quiet')
        local(CMD_SF_CC+' --quiet')

@task
def run_tests():
    """ 
    Launches all the PHPunit tests
    """
    reset_test_data()
    if env.host is not None:
        run(CMD_PHPUNIT_TEST_ALL)
    else:
        local(CMD_PHPUNIT_TEST_ALL)

@task
def tag(tag, remote='origin'):
    """ 
    Creates a new git tag
    """
    print(green('Creating tag "%s" on remote "%s"' % (tag, remote)))
    local(CMD_GIT_TAG % tag)
    local("git push %s --tags" % remote)

@task
def remove_tag(tag, remote='origin'):
    """ 
    Removes a git tag
    """
    print(green('Remove tag "%s" on remote "%s"' % (tag, remote)))
    local(CMD_GIT_FETCH+' -q')
    local(CMD_GIT_TAG_D % tag)
    local(CMD_GIT_PUSH % (remote, tag))


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

    sql = sql.replace('#db.user#', db['user'])
    sql = sql.replace('#db.password#', db['password'])
    sql = sql.replace('#db.name#', db['name'])
    sql = sql.replace('#db.name_test#', db['name_test'])
    
    query_file_name = 'config/create_dbs.sql';
    query_file = open(query_file_name,'w')
    query_file.write(sql);
    query_file.close();
    
    with settings(warn_only=True):
        if env.host is None:
            result = local(CMD_SQL_EXECUTE_FILE % (db['user'], query_file_name), True)
        else:
            result = run(CMD_SQL_EXECUTE_FILE % (db['user'], query_file_name), True)
    if result.failed:
        print(red('User creation failed', True))
    
    # Generating database file
    print(green('Generating database.yml file'))
    db_file = open(config.get('samples','database')+'.sample', 'r')
    file_content = db_file.read()
    file_content = file_content.replace('#db.user#', db['user'])
    file_content = file_content.replace('#db.password#', db['password'])
    file_content = file_content.replace('#db.name#', db['name'])
    file_content = file_content.replace('#db.name_test#', db['name_test'])
    db_file_out = open(config.get('samples','database'), 'w')
    db_file_out.write(file_content)
    db_file.close()
    db_file_out.close()

def symfony_install(config):
    """
    Creates symbolic links / checkout symfony's SVN, build classes, clear cache and publish assets
    """
    if not os.path.exists('lib/vendor/symfony'):
        if env.host is None:
            local('cd lib/vendor && ln -s %s symfony' % config.get('symfony', 'dir')) 
        else:
            run('svn co http://svn.symfony-project.com/branches/1.4 lib/vendor/symfony')
        
    if env.host is None:
        local(CMD_SF_BUILD_CLASSES+' --quiet')
        local(CMD_SF_CC+' --quiet')
        local(CMD_SF_PUBLISH_ASSETS+' --quiet')
    else:    
        run(CMD_SF_BUILD_CLASSES+' --quiet')
        run(CMD_SF_CC+' --quiet')
        run(CMD_SF_PUBLISH_ASSETS+' --quiet')

def getrole():
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
    local(CMD_GIT_FETCH)
    return local('git tag -l | sort | tail -n1', True)

def get_remote_path():
    """
    Return the path to the remote server
    """
    return path[getrole()]

def copy_sample(file):
    """
    Checks if the file exists, if not, creates it from the <file>.sample file
    """
    if not os.path.exists(file):
        if not os.path.exists(file+'.sample'):
           abort(red(file+'.sample does not exists',True))

        if env.host is None:
            local(CMD_COPY % (file+'.sample', file))
        else:
            run(CMD_COPY %  (file+'.sample', file))
    else:
		print(green(file+' already exists',True))

def parse_config(file):
    """
    Reads the config file with the ConfigParser module
    """
    config = ConfigParser.ConfigParser()
    config.read(file)
    return config
