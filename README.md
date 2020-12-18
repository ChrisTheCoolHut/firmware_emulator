# Firmware Emulator

This project is designed to replace [Firmadyne](https://github.com/firmadyne/firmadyne) through better headless firmware emulation support and a new interactive emulation feature. This project has been written entirely in python to ease debugging and tracking down QEMU or NVRAM specific issues in firmware images.

## Installation

This project requires python 3.6+ as it depends on `riposte`
```bash
./install.sh
```

This project can export emulated router images and those exported images have fewer dependencies to run:
```
sudo apt-get install qemu-system-arm qemu-system-mips qemu-system-x86 qemu-utils kpartx uml-utilities bridge-utils
```

## Basic Usage

Headless mode

### Headless mode help
```bash
$ ./emulate_me.py -h
usage: emulate_me.py [-h] Firmware

positional arguments:
  Firmware

optional arguments:
  -h, --help  show this help message and exit

```

### Headless mode on the WNAP320

This mode will automatically go through a standard emulation process. If the default networking method fails, it will aggressively try to force any network interfaces on the device to be assigned IP addresses. Should the script succede, a folder titled `FW_OUTPUT` will be created with the firmware image, firmware kernel, and a runner script.

```bash
$ python emulate_me.py WNAP320.zip
Cleaning /tmp/
INFO:root:Using firmadyne extractor

/home/chris/projects/firmware_emulator/WNAP320.zip
>> MD5: 51eddc7046d77a752ca4b39fbda50aff
>> Tag: WNAP320.zip_51eddc7046d77a752ca4b39fbda50aff
>> Temp: /tmp/tmpmsp80v1o
>> Status: Kernel: True, Rootfs: False, Do_Kernel: False,                 Do_Rootfs: True
>>>> Zip archive data, at least v2.0 to extract, compressed size: 1197, uncompressed size: 2667, name: ReleaseNotes_WNAP320_fw_2.0.3.HTML
>> Recursing into archive ...

/tmp/tmpmsp80v1o/_WNAP320.zip.extracted/WNAP320_V2.0.3_firmware.tar
	>> MD5: 6b66d0c845ea6f086e0424158d8e5f26
	>> Tag: WNAP320.zip_51eddc7046d77a752ca4b39fbda50aff
	>> Temp: /tmp/tmppu19mrit
	>> Status: Kernel: True, Rootfs: False, Do_Kernel: False,                 Do_Rootfs: True
	>>>> POSIX tar archive (GNU), owner user name: "gz.uImage"
	>> Recursing into archive ...

/tmp/tmppu19mrit/_WNAP320_V2.0.3_firmware.tar.extracted/kernel.md5
		>> MD5: 0e15e5398024c854756d3e5f7bc78877
		>> Skipping: text/plain...

/tmp/tmppu19mrit/_WNAP320_V2.0.3_firmware.tar.extracted/root_fs.md5
		>> MD5: b43dc86ce23660652d37d97651ba1c77
		>> Skipping: text/plain...
.... SNIP ....
Select (default p): Partition number (1-4, default 1): First sector (2048-2097151, default 2048): Last sector, +sectors or +size{K,M,G,T,P} (2048-2097151, default 2097151):
Created a new partition 1 of type 'Linux' and of size 1023 MiB.

Command (m for help): The partition table has been altered.
Syncing disks.

[sudo] password for chris:
.... SNIP ....
qemu-system-mips: warning: vlan 3 is not connected to host network
qemu-system-mips: warning: vlan 2 is not connected to host network
qemu-system-mips: warning: vlan 1 is not connected to host network
DEBUG:root:done
[{'ip': '192.168.0.100', 'host_ip': '192.168.0.99', 'dev': 'eth0', 'vlan': None, 'mac': None, 'tap_dev': 'tap_0', 'host_net_dev': 'tap_0'}]
```

```
$ ls FW_OUTPUT
image.raw  vmlinux.mips  WNAP320.zip_runner_.sh
```

### Interactive mode usage

Please see WIKI entry for [interactive firmware emulating](https://breaking-bits.gitbook.io/breaking-bits/interactive-firmware-emulator-usage)

The general flow of interactive editing is:
```
emu:~$ make_image <Path to Firmware Image>
emu:~$ setup_network
# Either
emu:~$ export <Path to runner directory>
# Or
emu:~$ run
```
