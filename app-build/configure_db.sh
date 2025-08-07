service mariadb start
sleep 5

mysql -e "create database dvwa;"
mysql -e "create user 'dvwa'@'127.0.0.1' identified by 'p@ssw0rd';" 
mysql -e "grant all privileges on dvwa.* to 'dvwa'@'127.0.0.1';"
