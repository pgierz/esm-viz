#!/bin/bash -e

echo "This script sets up automatic ssh keys for you"

echo "Please enter the username for the machine you want to generate keys for and press [ENTER]"
read USER

echo "Please enter the hostname for the machine you want to generate keys for and press [ENTER]"
read HOST

if [ ! -f ${HOME}/.ssh/id_rsa.pub ]; then
        ssh-keygen -t rsa
fi
ssh ${USER}@${HOST} mkdir -p .ssh
cat ${HOME}/.ssh/id_rsa.pub | \
            ssh ${USER}@${HOST} 'cat >> .ssh/authorized_keys'
