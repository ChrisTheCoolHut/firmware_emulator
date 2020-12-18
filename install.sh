#!/bin/bash
# install binwalk
./download.sh
git clone https://github.com/devttys0/binwalk.git
cd binwalk
sudo ./deps.sh
sudo python3 setup.py install

sudo -H pip3 install git+https://github.com/ahupp/python-magic
sudo -H pip3 install git+https://github.com/sviehb/jefferson

pip3 install cle python-magic riposte

sudo apt-get install qemu-system-arm qemu-system-mips qemu-system-x86 qemu-utils kpartx uml-utilities bridge-utils
