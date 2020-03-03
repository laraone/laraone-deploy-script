 #!/usr/bin/python
# -*- coding: utf-8 -*-

from fabric.api import *

BASE_PACKAGES = "nginx fail2ban mysql-server expect git unzip"
PHP_PACKAGES = "php7.3-fpm php7.3-cli php7.3-mysql php7.3-gd php7.3-common php7.3-dom php7.3-tidy php7.3-xmlrpc php7.3-intl php7.3-bcmath php7.3-mbstring php7.3-xml php7.3-zip php7.3-curl"

env.user = "root"
env.use_ssh_config = True

domainName = None
dbPass = None

def setup_base_packages():
    # install nginx, mysql, git, unzip
    run("apt-get -qqy upgrade")
    run("apt-get -qqy install {}".format(BASE_PACKAGES))

    # add PHP repo for PHP 7.3 packages and install PHP 7.3
    run("add-apt-repository ppa:ondrej/php -y")
    run("apt-get -qqy update")
    run("apt-get -qqy install {}".format(PHP_PACKAGES))

    # install composer, php package manager
    run("wget https://getcomposer.org/installer && php installer && chmod +x composer.phar")
    run("mv composer.phar /usr/bin/composer")

def setup_laraone():
    # checkout laraone backend, copy .env file, run composer and generate application key
    run("git clone https://github.com/laraone/phoenix.git /var/www/" + domainName)
    put("files/var/www/laraone/.env", "/var/www/" + domainName + "/.env")
    run("composer install --no-dev --no-interaction --no-suggest -d /var/www/" + domainName + "/")
    run("php /var/www/" + domainName + "/artisan key:generate --force")

    # setup folder and file permissions
    run("chown -R www-data:www-data /var/www/" + domainName)
    run("find /var/www/" + domainName + " -type f -exec chmod 664 {} \;")
    run("find /var/www/" + domainName + " -type d -exec chmod 777 {} \;")
    run("chmod -R 777 /var/www/" + domainName + "/storage")

    # setup mysql database for CMS, create db_user and set password for that user
    run('mysql -u root -e "CREATE DATABASE laraone CHARACTER SET latin1 COLLATE latin1_swedish_ci;"')
    run('mysql -u root -e "CREATE USER %s@%s IDENTIFIED BY %s;"' % ("'db_user'", "'localhost'", "'" + dbPass + "'"))
    run('mysql -u root -e "GRANT ALL PRIVILEGES ON laraone.* TO %s@%s;"' % ("'db_user'", "'localhost'"))

def setup_firewall():
    run("ufw allow OpenSSH")
    run("ufw allow 'Nginx Full'")
    run("ufw allow https")
    run("ufw allow http")
    run("ufw --force enable")

def setup_ssl_support():
    # add 3rd paty repo and install certbot
    run("apt-get -qqy install software-properties-common")
    run("add-apt-repository universe")
    run("add-apt-repository ppa:certbot/certbot -y")
    run("apt-get -qqy update")
    run("apt-get -qqy install certbot python-certbot-nginx")

def copy_files():
    # copy nginx conf file and create symbolic link
    put("files/etc/nginx/sites-available/laraone.conf", "/etc/nginx/sites-available/" + domainName + ".conf")
    run("ln -s /etc/nginx/sites-available/" + domainName + ".conf" + " /etc/nginx/sites-enabled/")
    
    # remove default symbolic link
    run("unlink /etc/nginx/sites-enabled/default")

    # update conf file with domainName by search and replace
    run('sed -i ' + '"s/REPLACE_WITH_DOMAIN/' + domainName + ' www.' + domainName + '/g"' + ' /etc/nginx/sites-available/' + domainName + ".conf")

def build_base():
    # install base package, php and composer
    setup_base_packages()

    # initial setup for Laraone CMS
    setup_laraone()

    # prepare for ssl support
    setup_ssl_support()

    # copy necessary files
    copy_files()

    # setup and start the firewall
    setup_firewall()

    # restart nginx to pick up all the changes above
    run("sudo systemctl restart nginx")

@task
def build_image(domain, password):
    global domainName
    global dbPass
    domainName = domain
    dbPass = password

    build_base()
    # clean_up()
    print("Build complete.")

