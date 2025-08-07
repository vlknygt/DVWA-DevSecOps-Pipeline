#!/bin/bash

echo 'Started'
echo 'Saving image as tar'
rm -f /home/ubuntu-jenkins/saved-images/dvwa.tar
docker save -o /home/ubuntu-jenkins/saved-images/dvwa.tar dvwa:latest
ssh volkan@192.168.1.203 rm -f /home/volkan/Desktop/dvwa.tar
echo 'Sending file to Application VM'
scp /home/ubuntu-jenkins/saved-images/dvwa.tar volkan@192.168.1.203:/home/volkan/Desktop/dvwa.tar
#ssh volkan@192.168.1.203 dockerstop
#ssh volkan@192.168.1.203 docker image rm dvwa:latest
echo 'Loading image on Application VM'
ssh volkan@192.168.1.203 docker load -i /home/volkan/Desktop/dvwa.tar
echo 'Finished'

