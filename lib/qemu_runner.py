import os
import subprocess
import logging
import re
import shlex
import socket
import struct
import shutil
import copy

# Main directory
parent_directory = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

qemu_commands = {
    "mipsel": "qemu-system-mipsel",
    "mipseb": "qemu-system-mips",
    "mips": "qemu-system-mips",
    "arm": "qemu-system-arm",
}
machine_args = [
    '-append "firmadyne.syscall={} root=/dev/sda1 console=ttyS0 nandsim.parts=64,64,64,64,64,64,64,64,64,64 rdinit=/firmadyne/preInit.sh rw debug ignore_loglevel print-fatal-signals=1"',
    "-m 1024",
]
arm_board = "-M virt"
mips_board = "-M malta"
kernel_arg = "-kernel {}"
drive_arg_mips = "-drive if=ide,format=raw,file={}"
drive_arg_arm = (
    "-drive if=none,file={},format=raw,id=rootfs -device virtio-blk-device,drive=rootfs"
)
arm_env = {"QEMU_AUDIO_DRV": "none"}

# Needs temp directory plus serial files
logging_args = [
    "-serial file:{}/qemu.initial.serial.log",
    "-serial unix:{}/serial.S1,server,nowait",
    "-monitor unix:{}/monitor,server,nowait",
]
no_display_option = "-display none"

verbose_arg = "-nographic"

mips_network_args = [
    "-net nic,vlan=0",
    "-net socket,vlan=0,listen=:2000",
    "-net nic,vlan=1",
    "-net socket,vlan=0,listen=:2001",
    "-net nic,vlan=2",
    "-net socket,vlan=0,listen=:2002",
    "-net nic,vlan=3",
    "-net socket,vlan=0,listen=:2003",
]
extra_mips_net = [
    "-net nic,vlan=0",
    "-net tap,vlan=0,id=net0,ifname=tap_0,script=no",
]
arm_network_args = [
    "-device virtio-net-device,netdev=net1",
    "-netdev socket,listen=:2000,id=net1",
    "-device virtio-net-device,netdev=net2",
    "-netdev socket,listen=:2001,id=net2",
    "-device virtio-net-device,netdev=net3",
    "-netdev socket,listen=:2002,id=net3",
    "-device virtio-net-device,netdev=net4",
    "-netdev socket,listen=:2003,id=net4",
]

extra_arm_net = [
    "-device virtio-net-device,netdev=net0",
    "-netdev tap,id=net0,ifname=tap_0,script=no",
]

# Expects TAPDEV_I
set_up_tunnel = "sudo tunctl -t {} -u root"

# Expects TAPDEV_I, HOSTNETDEV_I.VLANID, VLANID, HOSTNETDEV_I.VLANID
set_up_vlan = [
    "sudo ip link add link {} name {} type vlan id {}",
    "sudo ip link set {} up",
]

# Expects HOSTNETDEV, HOSTIP, HOSTNETDEV, GUESTIP, GUESTIP,HOSTNETDEV
set_up_ip = [
    "sudo ip link set {} up",
    "sudo ip addr add {}/24 dev {}",
    "sudo ip route add {} via {} dev {}",
]

# Host net dev, tap dev
down_dev = ["sudo ip route flush dev {}", "sudo ip link set {} down"]

# Host net dev
vlan_down = "sudo ip link delete {}"

# tap_dev
del_dev = "sudo tunctl -d {}"


class QemuImage:
    def __init__(self, arch, endianess, image, tmp_dir, debug=False):
        self.arch = arch
        self.endianess = endianess
        self.image = image
        self.kernel = self.get_kernel()
        self.debug = debug
        self.tmp_dir = tmp_dir
        self.serial_file = "{}/qemu.initial.serial.log".format(tmp_dir)
        self.start_net = None
        self.stop_net = None
        self.ips = []

    def start_network(self):

        for ip in self.ips:
            logging.info("Device available on {}".format(ip))

        if self.start_net:
            for net_cmds in self.start_net:
                for cmd in net_cmds:
                    logging.debug(cmd)
                    subprocess.check_call(cmd, shell=True)
        else:
            logging.warning("Can't start network. No network configured")

    def stop_network(self):

        if self.stop_net:
            for net_cmds in self.stop_net:
                for cmd in net_cmds:
                    logging.debug(cmd)
                    subprocess.check_call(cmd, shell=True)
        else:
            logging.warning("Can't stop network. No network configured")

    def setup_network(self, timeout=60):
        logging.debug("Getting network information")

        log = self.get_serial_log(timeout)

        net_info = self.get_network_info(log, self.endianess)
        print(net_info)

        # If we get no network info, than we can't network :(
        if not net_info:
            return False

        for net_dict in net_info:
            self.ips.append(net_dict["ip"])

        self.get_start_network_commands(net_info)
        self.get_stop_network_commands(net_info)

        return True

    def add_net_device(
        self,
        dev_ip,
        host_ip,
        iface_dev,
        vlan=None,
        mac=None,
        tap_dev="tap_0",
        host_net_dev="tap_0",
    ):

        logging.debug("Adding {} {} {}".format(dev_ip, host_ip, iface_dev))
        self.ips.append(dev_ip)
        net_info = {}
        net_info["ip"] = dev_ip
        net_info["host_ip"] = host_ip
        net_info["dev"] = iface_dev
        net_info["vlan"] = vlan
        net_info["mac"] = mac
        net_info["tap_dev"] = tap_dev
        net_info["host_net_dev"] = host_net_dev

        self.get_start_network_commands([net_info])
        self.get_stop_network_commands([net_info])

        return True

    def get_stop_network_commands(self, network_list):

        stop_network_commands = []

        for network_dict in network_list:
            # Setup with tunctl
            net_cmd = [down_dev[0].format(network_dict["host_net_dev"])]
            net_cmd.append(down_dev[1].format(network_dict["tap_dev"]))

            # Setup vlan
            if network_dict["vlan"]:
                net_cmd.append(vlan_down.format(network_dict["host_net_dev"]))

            net_cmd.append(del_dev.format(network_dict["tap_dev"]))
            # Do routing

            stop_network_commands.append(net_cmd)

        self.stop_net = stop_network_commands

        return stop_network_commands

    def get_start_network_commands(self, network_list):

        start_network_commands = []

        for network_dict in network_list:
            # Setup with tunctl
            net_cmd = [set_up_tunnel.format(network_dict["tap_dev"])]

            # Setup vlan
            if network_dict["vlan"]:
                net_cmd.append(
                    set_up_vlan[0].format(
                        network_dict["tap_dev"],
                        network_dict["host_net_dev"],
                        network_dict["vlan"],
                    )
                )
                net_cmd.append(set_up_ip[0].format(network_dict["tap_dev"]))
                net_cmd.append(set_up_vlan[1].format(network_dict["host_net_dev"]))
            else:
                net_cmd.append(set_up_ip[0].format(network_dict["host_net_dev"]))

            # Do routing
            net_cmd.append(
                set_up_ip[1].format(network_dict["host_ip"], network_dict["tap_dev"])
            )
            net_cmd.append(
                set_up_ip[2].format(
                    network_dict["ip"], network_dict["host_ip"], network_dict["tap_dev"]
                )
            )

            start_network_commands.append(net_cmd)

        self.start_net = start_network_commands

        return start_network_commands

    def get_tap_info(self, network_info):
        tap_devs = []
        host_net_devs = []
        network_dicts = []

        for i, (ip, dev, vlan, mac) in enumerate(network_info):
            tap_dev = "tap_{}".format(i)
            host_net_dev = tap_dev
            if vlan:
                host_net_dev += ".{}".format(vlan)

            temp_dict = {
                "ip": ip,
                "host_ip": self.getIP(ip),
                "dev": dev,
                "vlan": vlan,
                "mac": mac,
                "tap_dev": tap_dev,
                "host_net_dev": host_net_dev,
            }
            network_dicts.append(temp_dict)

        return network_dicts

    # I hate this function. This needs to be reworked.
    def get_network_info(self, data, endianness):
        brifs = []
        vlans = []
        network = set()
        success = False

        # find interfaces with non loopback ip addresses
        ifacesWithIps = self.findNonLoInterfaces(data, endianness)

        # find changes of mac addresses for devices
        macChanges = self.findMacChanges(data, endianness)

        deviceHasBridge = False
        for iwi in ifacesWithIps:
            # find all interfaces that are bridged with that interface
            brifs = self.findIfacesForBridge(data, iwi[0])
            for dev in brifs:
                # find vlan_ids for all interfaces in the bridge
                vlans = self.findVlanInfoForDev(data, dev)
                # create a config for each tuple
                network.add((self.buildConfig(iwi, dev, vlans, macChanges)))
                deviceHasBridge = True

            # if there is no bridge just add the interface
            if not brifs and not deviceHasBridge:
                vlans = self.findVlanInfoForDev(data, iwi[0])
                network.add((self.buildConfig(iwi, iwi[0], vlans, macChanges)))

        ips = set()
        pruned_network = []
        for n in network:
            if n[0] not in ips:
                ips.add(n[0])
                pruned_network.append(n)
            else:
                logging.debug("duplicate ip address for interface: {}".format(n))

        return self.get_tap_info(pruned_network)

    def getIP(self, ip):
        tups = [int(x) for x in ip.split(".")]
        if tups[3] != 1:
            tups[3] -= 1
        else:
            tups[3] = 2
        return ".".join([str(x) for x in tups])

    def findMacChanges(self, data, endianness):
        lines = self.stripTimestamps(data)
        candidates = filter(lambda l: l.startswith("ioctl_SIOCSIFHWADDR"), lines)

        result = []
        if endianness == "eb":
            fmt = ">I"
        elif endianness == "el":
            fmt = "<I"
        for c in candidates:
            g = re.match(
                r"^ioctl_SIOCSIFHWADDR\[[^\]]+\]: dev:([^ ]+) mac:0x([0-9a-f]+) 0x([0-9a-f]+)",
                c,
            )
            if g:
                (iface, mac0, mac1) = g.groups()
                m0 = struct.pack(fmt, int(mac0, 16))[2:]
                m1 = struct.pack(fmt, int(mac1, 16))
                mac = "%02x:%02x:%02x:%02x:%02x:%02x" % struct.unpack("BBBBBB", m0 + m1)
                result.append((iface, mac))
        return result

    def findVlanInfoForDev(self, data, dev):
        # lines = data.split("\r\n")
        lines = self.stripTimestamps(data)
        results = []
        candidates = filter(lambda l: l.startswith("register_vlan_dev"), lines)
        for c in candidates:
            g = re.match(
                r"register_vlan_dev\[[^\]]+\]: dev:%s vlan_id:([0-9]+)" % dev, c
            )
            if g:
                results.append(int(g.group(1)))
        return results

    def buildConfig(self, brif, iface, vlans, macs):
        # there should be only one ip
        ip = brif[1]
        br = brif[0]

        # strip vlanid from interface name (e.g., eth2.2 -> eth2)
        dev = iface.split(".")[0]

        # check whether there is a different mac set
        mac = None
        d = dict(macs)
        if br in d:
            mac = d[br]
        elif dev in d:
            mac = d[dev]

        vlan_id = None
        if len(vlans):
            vlan_id = vlans[0]

        return (ip, dev, vlan_id, mac)

    def get_serial_log(self, timeout=60):

        logging.debug("Getting serial from {} second run".format(timeout))

        temp_debug = self.debug

        self.debug = False
        command = self.build_run_command()
        command = " ".join(command)

        self.debug = temp_debug

        command = shlex.split(command)
        logging.debug(command)
        try:
            subprocess.check_output(command, env=arm_env, timeout=timeout)
        except:
            logging.debug("done")

        with open(self.serial_file, "rb") as f:
            return f.read().decode("utf-8", "ignore")

    def run_interactive(self, networked=False):

        if self.start_net:
            self.start_network()

        logging.debug("Press Ctrl+a then x to exit")

        temp_debug = self.debug

        self.debug = True

        command = self.build_run_command()
        # grep_cmd = " | grep -v firmadyne"
        grep_cmd = " "
        command = "sudo QEMU_AUDIO_DRV=none " + " ".join(command) + grep_cmd
        self.debug = temp_debug

        os.environ.update(arm_env)
        logging.debug(command)
        try:
            subprocess.check_call(command, shell=True, env=os.environ)
        except:
            logging.debug("done")

        if self.stop_net:
            self.stop_network()

    def stripTimestamps(self, data):
        lines = data.split("\n")
        # throw out the timestamps
        lines = [re.sub(r"^\[[^\]]*\] firmadyne: ", "", l) for l in lines]
        return lines

    # Get the netwokr interfaces in the router, except 127.0.0.1
    def findNonLoInterfaces(self, data, endianness):
        # lines = data.split("\r\n")
        lines = self.stripTimestamps(data)
        candidates = filter(
            lambda l: l.startswith("__inet_insert_ifa"), lines
        )  # logs for the inconfig process
        result = []
        if endianness == "Iend_BE":
            fmt = ">I"
        elif endianness == "Iend_LE":
            fmt = "<I"
        for c in candidates:
            g = re.match(
                r"^__inet_insert_ifa\[[^\]]+\]: device:([^ ]+) ifa:0x([0-9a-f]+)", c
            )
            if g:
                (iface, addr) = g.groups()
                addr = socket.inet_ntoa(struct.pack(fmt, int(addr, 16)))
                if addr != "127.0.0.1" and addr != "0.0.0.0":
                    result.append((iface, addr))
        return result

    def findIfacesForBridge(self, data, brif):
        # lines = data.split("\r\n")
        lines = self.stripTimestamps(data)
        result = []
        candidates = filter(
            lambda l: l.startswith("br_dev_ioctl") or l.startswith("br_add_if"), lines
        )
        for c in candidates:
            for p in [
                r"^br_dev_ioctl\[[^\]]+\]: br:%s dev:(.*)",
                r"^br_add_if\[[^\]]+\]: br:%s dev:(.*)",
            ]:
                pat = p % brif
                g = re.match(pat, c)
                if g:
                    iface = g.group(1)
                    # we only add it if the interface is not the bridge itself
                    # there are images that call brctl addif br0 br0 (e.g., 5152)
                    if iface != brif:
                        result.append(iface.strip())
        return result

    def build_run_command(self):

        if self.arch not in qemu_commands.keys():
            raise (RuntimeError("{} not in qemu commands".format(self.arch)))

        run_command = [qemu_commands[self.arch]]

        if "mips" in self.arch:
            run_command.append(mips_board)
            if self.start_net:
                run_command.extend(extra_mips_net)
            else:
                run_command.extend(mips_network_args)

        elif "arm" in self.arch:
            run_command.append(arm_board)
            if self.start_net:
                run_command.extend(extra_arm_net)
            else:
                run_command.extend(arm_network_args)

        run_command.append(kernel_arg.format(self.kernel))
        if "mips" in self.arch:
            run_command.append(drive_arg_mips.format(self.image))
        elif "arm" in self.arch:
            run_command.append(drive_arg_arm.format(self.image))

        if self.debug:
            run_command.extend([machine_args[0].format(0), machine_args[1]])
        else:
            run_command.extend([machine_args[0].format(1), machine_args[1]])

        if self.debug:
            run_command.append(verbose_arg)
        else:
            logging_files_arg = [x.format(self.tmp_dir) for x in logging_args]
            run_command.extend(logging_files_arg)
            run_command.append(no_display_option)

        return run_command

    def get_kernel(self):

        if "mips" in self.arch:
            kernel_binary = "vmlinux.{}".format(self.arch)
        else:
            kernel_binary = "zImage.{}".format(self.arch)

        binary_folder = os.path.join(parent_directory, "binaries")

        return os.path.join(binary_folder, kernel_binary)

    def export(self, location, script_name="runner.sh", script_only=False):

        runner_copy = copy.deepcopy(self)

        if not os.path.exists(location):
            os.mkdir(location)

        bash_filename = script_name
        file_path = os.path.join(location, bash_filename)

        if not script_only:
            shutil.copy(self.kernel, location)
            shutil.copy(self.image, location)

        runner_copy.kernel = self.kernel.split("/")[-1]
        runner_copy.image = self.image.split("/")[-1]
        runner_copy.tmp_dir = "."
        runner_copy.debug = True

        bash_file = "#!/bin/bash\n# Networking\n"

        if self.start_net:
            bash_file += "\n".join(["\n".join(net) for net in self.start_net])

        bash_file += "\n# Emulating\n"

        bash_file += "\nset QEMU_AUDIO_DRV=none\n"

        bash_file += "sudo " + " \\\n".join(runner_copy.build_run_command())

        bash_file += "\n# Stop networking\n"

        if self.stop_net:
            bash_file += "\n".join(["\n".join(net) for net in self.stop_net]) + "\n"

        with open(file_path, "w") as f:
            f.write(bash_file)
