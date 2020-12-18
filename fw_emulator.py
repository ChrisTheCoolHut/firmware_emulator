# /usr/bin/env python
from riposte import Riposte
import logging

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("cle").setLevel("WARNING")
import tempfile
import atexit
from lib import extract_helper
from lib import image_helper
from lib import arch_helper
from lib import qemu_runner

BANNER = """
______ _                                      
|  ___(_)                                     
| |_   _ _ __ _ __ _____      ____ _ _ __ ___ 
|  _| | | '__| '_ ` _ \ \ /\ / / _` | '__/ _ \\
| |   | | |  | | | | | \ V  V / (_| | | |  __/
\_|   |_|_|  |_| |_| |_|\_/\_/ \__,_|_|  \___|
                                              
                                              
 _____                _       _               
|  ___|              | |     | |              
| |__ _ __ ___  _   _| | __ _| |_ ___  _ __   
|  __| '_ ` _ \| | | | |/ _` | __/ _ \| '__|  
| |__| | | | | | |_| | | (_| | || (_) | |     
\____/_| |_| |_|\__,_|_|\__,_|\__\___/|_|     

"""

emu = Riposte(prompt="emu:~$ ", banner=BANNER)

tmp_dir = None
fw_tar = None
image = None
arch = None
runner = None
mount_path = None
device = None


def have_image():
    return image is not None


@emu.command("make_image")
def get_image(fw_path):

    global tmp_dir
    global fw_tar
    global image
    global arch
    global runner

    tmp_dir = tempfile.TemporaryDirectory()
    atexit.register(tmp_dir.cleanup)

    try:
        fw_tar = extract_helper.extract_image(fw_path, tmp_dir.name)
    except:
        emu.error("Could not extract image")
        return

    try:
        arch = arch_helper.get_arch(fw_tar)
    except:
        emu.error("Could not get image architecture")
        return

    try:
        if not "image.raw" in fw_path:
            image = image_helper.make_image(fw_tar, arch.qemu_name, tmp_dir.name)
        else:
            image = fw_path
    except Exception as e:
        print(e)
        emu.error("Could not build qemu image")
        return

    runner = qemu_runner.QemuImage(
        arch.qemu_name, arch.memory_endness, image, tmp_dir.name, False
    )

    emu.success("Image created!")


@emu.command("setup_network")
def setup_image_network():

    if not have_image():
        emu.error("No image set")
        return

    if runner.setup_network():
        emu.success("Network is accessible!")
    else:
        emu.error("Network is not accessible")


@emu.command("force_network")
def force_network():

    if not have_image():
        emu.error("No image set")
        return

    image_helper.force_networking(tmp_dir.name, image)

    emu.success("Files changed, ready to setup network")


@emu.command("run")
def run_runner():

    if not have_image():
        emu.error("No image set")
        return

    emu.info("Ctrl A + X to leave")
    runner.run_interactive()
    emu.success("Emulation job finished")


@emu.command("add_file")
def add_file_to_image(local_file, remote_file):

    if not have_image():
        emu.error("No image set")
        return

    try:
        image_helper.add_file(tmp_dir.name, image, local_file, remote_file)
        emu.success("Added file")
    except:  # Could not add file
        emu.error("Could not add file")


@emu.command("del_file")
def del_file_from_image(file_path):

    if not have_image():
        emu.error("No image set")
        return

    try:
        image_helper.del_file(tmp_dir.name, image, file_path)
        emu.success("Removed file")
    except:  # File not found
        emu.error("Could not remove file")


@emu.command("remove_root_passwd")
def remove_root_passwd():

    if not have_image():
        emu.error("No image set")
        return

    try:
        image_helper.remove_root_passwd(tmp_dir.name, image)
        emu.success("Removed root passwd")
    except:
        emu.error("Could not remove root passwd")


@emu.command("force_tty_login")
def force_tty_login():

    if not have_image():
        emu.error("No image set")
        return

    try:
        image_helper.replace_tty_login(tmp_dir.name, image)
        emu.success("Successfully replaced tty login with /bin/sh")
    except:
        emu.error("Could not replace TTY login")


@emu.command("export")
def export_image(location):

    if not runner:
        emu.error("No runner set")
        return

    runner.export(location)


@emu.command("info")
def image_info():

    if not runner:
        emu.error("No runner set")
        return

    emu.success("Image Arch    : {}".format(runner.arch))
    emu.success("Image Endi    : {}".format(runner.endianess))
    emu.success("Image Path    : {}".format(runner.image))
    emu.success("Image IP ADDR : {}".format(runner.ips))
    emu.success("Image Kernel  : {}".format(runner.kernel))


@emu.command("mount")
def mount_image():
    if not have_image():
        emu.error("No image set")
        return

    global mount_path
    global device
    if mount_path is not None:
        emu.error("Already mounted at {}".format(mount_path))

    try:
        device = image_helper.get_mounted_device(image)

        mount_path = image_helper.make_mount_path(tmp_dir.name, device)

        image_helper.fix_permissions(tmp_dir.name)
    except:  # subprocess.CalledProcessError
        emu.error("Unmounting too quickly. Try again in a moment")

    emu.success("Successfully mounted at {}".format(mount_path))


@emu.command("unmount")
def unmount_image():
    if not have_image():
        emu.error("No image set")
        return

    global mount_path
    if mount_path is None:
        emu.error("Nothing mounted. Nothing to do")

    image_helper.cleanup_image_and_device(image, device)

    mount_path = None


@emu.command("add_network")
def add_network_device(dev_ip, host_ip, iface_dev):

    if not have_image():
        emu.error("No image set")
        return

    if not runner:
        emu.error("No runner set")
        return

    if runner.add_net_device(dev_ip, host_ip, iface_dev):
        emu.success("Successfully added network information")
    else:
        emu.error("Failed to add network device")


emu.run()
