#!/bin/sh

# Maybe i should just write this in c. Coreutils like to crash during emulation
for i in $(cat /proc/net/dev | grep ':' | cut -f 1 -d ':'); do ifconfig $i down;done
for i in $(cat /proc/net/dev | grep ':' | cut -f 1 -d ':' | grep eth); do ifconfig $i 192.168.0.1;break;done
for i in $(cat /proc/net/dev | grep ':' | cut -f 1 -d ':' | grep ens); do ifconfig $i 192.168.0.1;break;done
sleep 10
for i in $(cat /proc/net/dev | grep ':' | cut -f 1 -d ':'); do ifconfig $i down;done
for i in $(cat /proc/net/dev | grep ':' | cut -f 1 -d ':' | grep eth); do ifconfig $i 192.168.0.1;break;done
for i in $(cat /proc/net/dev | grep ':' | cut -f 1 -d ':' | grep ens); do ifconfig $i 192.168.0.1;break;done
sleep 10
for i in $(cat /proc/net/dev | grep ':' | cut -f 1 -d ':'); do ifconfig $i down;done
for i in $(cat /proc/net/dev | grep ':' | cut -f 1 -d ':' | grep eth); do ifconfig $i 192.168.0.1;break;done
for i in $(cat /proc/net/dev | grep ':' | cut -f 1 -d ':' | grep ens); do ifconfig $i 192.168.0.1;break;done
sleep 10

iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT
iptables -P OUTPUT ACCEPT
iptables -I INPUT -j ACCEPT
