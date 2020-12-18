#!/bin/sh

set -e

echo "Downloading binaries..."

mkdir binaries

echo "Downloading kernel 2.6.32 (MIPS)..."
wget -O ./binaries/vmlinux.mipsel https://github.com/firmadyne/kernel-v2.6.32/releases/download/v1.0/vmlinux.mipsel
wget -O ./binaries/vmlinux.mipseb https://github.com/firmadyne/kernel-v2.6.32/releases/download/v1.0/vmlinux.mipseb

echo "Downloading kernel 3.2.0-4 (MIPS)..."
wget -O ./binaries/vmlinux.mipseb_3.2 https://people.debian.org/~aurel32/qemu/mips/vmlinux-3.2.0-4-5kc-malta
wget -O ./binaries/vmlinux.mipsel_3.2 https://people.debian.org/~aurel32/qemu/mipsel/vmlinux-3.2.0-4-5kc-malta

echo "Downloading kernel 4.1 (ARM)..."
wget -O ./binaries/zImage.armel https://github.com/firmadyne/kernel-v4.1/releases/download/v1.0/zImage.armel

echo "Downloading console..."
wget -O ./binaries/console.armel https://github.com/firmadyne/console/releases/download/v1.0/console.armel
wget -O ./binaries/console.mipseb https://github.com/firmadyne/console/releases/download/v1.0/console.mipseb
wget -O ./binaries/console.mipsel https://github.com/firmadyne/console/releases/download/v1.0/console.mipsel

echo "Downloading libnvram..."
wget -O ./binaries/libnvram.so.armel https://github.com/firmadyne/libnvram/releases/download/v1.0c/libnvram.so.armel
wget -O ./binaries/libnvram.so.mipseb https://github.com/firmadyne/libnvram/releases/download/v1.0c/libnvram.so.mipseb
wget -O ./binaries/libnvram.so.mipsel https://github.com/firmadyne/libnvram/releases/download/v1.0c/libnvram.so.mipsel

cd binaries
ln -s ./vmlinux.mipseb ./vmlinux.mips
ln -s ./console.mipseb ./console.mips
ln -s ./libnvram.so.mipseb ./libnvram.so.mips

echo "Done!"
