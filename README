Set of fabfiles for install/deploy project.

Types of project :
- symfony 1.4.x
- Symfony 2.x (todo)

What these fables can do ?
===

* install the project (copy sample files, configure the database, run symfony task…)
* rebuild the doctrine files (models, forms and filters), clear the cache, publish the assets
* reset the data tests

Use
===

Symfony 1.4.x project installation
---
Thanks to the ```symfony-fabfile.py``` you can now easily install any symfony 1.4.x project. 

First of all you need to create or complete the ```config/properties.ini``` like this:

	; Project configuration
    [symfony]
    name=fabfile ; project name
    author=Benjamin Grandfond <benjamin.grandfond@gmail.com> ; author of the project
    orm=Doctrine
    repository=git@github.com:benja-M-1/fabfile.git ; git repository of the project
    dir=~/Dev/symfony/1.4 ; path to symfony 
  
	; List of samples files to copy
	; The name of the sample files must be like databases.yml.sample
    [samples]
    database=config/databases.yml 

Then create the database sample configuration file ```config/databases.yml.sample```

	all:
	  doctrine:
    	class: sfDoctrineDatabase
	    param:
	      dsn:      mysql:host=#db_host#;dbname=#db_name#
	      username: #db_user#
	      password: #db_password#

	test:
	  doctrine:
	    param:
    	  dsn:      mysql:host=#db_host#;dbname=#db_name_test#
	      username: #db_user#
	      password: #db_password#

When you are done, you can now run the command

	~:$ fab install

This command will :

* copy ```config/properties.ini.sample``` into ```config/properties.ini```
* ask you to give the mysql user, password, database name and test database test name you want use for your project
* create the user, the two databases and grant the user the privileges he needs on the two databases
* copy ```config/databases.yml.sample``` into ```config/databases.yml```
* change the keys by the configured values in the databases configuration file
* create a symbolic link of the symfony core in ```lib/vendor```
* build doctrine classes
* clear the symfony cache
* publish assets

You can use another ```.ini``` file for your settings :

	~:$ fab install:config_file=my_ini_file.ini

You can set the mysql user, password and databases directly in the ```fabfile``` if you prefer, change the ```db``` values and run the install command like this :

	~:$ fab install:interactive=False


Requirements
===

To use these fabfiles you need [fabric](http://docs.fabfile.org/en/1.3.3/index.html).

TODO
===
* add the possibility of the reset test data task to take a sql file and load it
