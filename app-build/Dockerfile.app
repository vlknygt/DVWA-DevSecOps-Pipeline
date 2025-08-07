FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
    mariadb-server \
    curl \
    iputils-ping \
    net-tools \
    apache2 \
    gpg \
    gnupg2 \
    software-properties-common \
    ca-certificates \
    apt-transport-https \
    lsb-release \
    unzip \
    git \
    php-zip \
    php-mbstring \
    php-xml \
    php-curl \
    php-cli && \
    add-apt-repository ppa:ondrej/php -y && \
    apt-get update && \
    apt-get install -y php8.4 php8.4-mysqli && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Create and go to related directory, copy files
RUN mkdir -p /var/www && \
    mkdir -p /var/www/html

COPY DVWA /var/www/html/DVWA
RUN chmod -R 777 /var/www/html/DVWA

# to set security level low
RUN cd /var/www/html/DVWA/config/ && \
    rm config.inc.php.dist

COPY config.inc.php.dist /var/www/html/DVWA/config/config.inc.php.dist

RUN cd /var/www/html/DVWA/config && \
    cp config.inc.php.dist config.inc.php

COPY .my.cnf /root/
RUN chmod 600 /root/.my.cnf

COPY configure_db.sh .
RUN chmod +x configure_db.sh && \
    ./configure_db.sh

COPY php.ini /etc/php/8.4/apache2/

RUN php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');" && \
    php composer-setup.php --install-dir=/usr/local/bin --filename=composer && \
    cd /var/www/html/DVWA/vulnerabilities/api && \
    composer install

COPY final_db_setup.php /var/www/html/DVWA/final_db_setup.php

# RUN php /var/www/html/DVWA/final_db_setup.php

CMD tail -f /dev/null
