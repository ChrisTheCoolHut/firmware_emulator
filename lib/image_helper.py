import logging
from contextlib import contextmanager
import tempfile
import tarfile
import os
import subprocess
import shutil
import stat
import magic

image_name = "image.raw"

# Expects full path to image
# make_image_cmd = "qemu-img create -f raw \"{}\" 100M"
make_image_cmd = 'qemu-img create -f raw "{}" 1G'

# TODO: Convert this to pyparted commands
# Expects path to image
fdisk_cmd = '/sbin/fdisk "{}"'
partition_cmd_input = b"o\nn\np\n1\n\n\nw"

# Mount qemu image
# Expects path to image
kpart_cmd = "sudo kpartx -a -s -v {}"
mapper_str = "/dev/mapper/{}"

mount_dir = "file_system"

# Expects device then mount_path
mount_format = 'sudo mount "{}" "{}"'

# Firmadyne paths
base_path = "firmadyne"
nvram_path = "libnvram"
override_path = "libnvram.override"

# Fix image path
fix_image_path = "scripts/fixImage.sh"
# Expects mount_path
fix_image_command = 'sudo chroot "{}" /busybox ash /fixImage.sh'

# Console
console_name = "console.{}"
console_mount_path = "firmadyne/console"

# Nvram
nvram_name = "libnvram.so.{}"
nvram_mount_path = "firmadyne/libnvram.so"

pre_init_name = "scripts/preInit.sh"
pre_init_mount_path = "firmadyne/preInit.sh"

# Expects device
mkfs_cmd = "sudo mkfs.ext2 {}"

# Strings for unmounting

# Expects device
umount_cmd = 'sudo umount "{}"'
# Expects image_name
kpartx_cmd = 'sudo kpartx -d "{}"'
# Expects device
losetup_cmd = 'losetup -d "{}"'
# Expects device in /dev folder
dmsetup_cmd = "sudo dmsetup remove {}"

chown_cmd = "sudo chown -R {}:{} {}"

# Main directory
parent_directory = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def force_networking(work_dir, image_path):

    force_script = "scripts/force_network.sh"
    force_path = os.path.join(parent_directory, force_script)

    run_cmd = "\n/bin/sh /firmadyne/force_network.sh &\n"

    add_file(work_dir, image_path, force_path, "/firmadyne/force_network.sh")

    rcs_file = "rcS"

    with mounted(work_dir, image_path) as fs_path:

        # Append to preInit
        pre_init_mounted = os.path.join(fs_path, pre_init_mount_path)
        os.chmod(pre_init_mounted, 0o777)
        with open(pre_init_mounted, "a") as f:
            f.write(run_cmd)

        # Append to rcS
        for path, subdir, files in os.walk(fs_path):
            for file_name in files:
                if file_name == rcs_file:
                    file_path = os.path.join(path, file_name)
                    if "ASCII text" in magic.from_file(file_path):
                        os.chmod(file_path, stat.S_IWRITE)
                        with open(file_path, "a") as f:
                            f.write(run_cmd)


# Find shadow and passwd files and strip passwords
def remove_root_passwd(work_dir, image_path):

    logging.debug("Removing root passwd from shadow and passwd")
    passwd_files = ["shadow", "passwd"]

    with mounted(work_dir, image_path) as fs_path:
        for path, subdir, files in os.walk(fs_path):
            for file_name in files:
                if any(x in file_name for x in passwd_files):
                    file_path = os.path.join(path, file_name)
                    if magic.from_file(file_path) == "ASCII text":
                        lines = []
                        with open(file_path, "r") as f:
                            lines = f.readlines()
                        os.chmod(file_path, stat.S_IWRITE)
                        with open(file_path, "w") as f:
                            for line in lines:
                                if "root:" in line:
                                    if file_name == "passwd":
                                        f.write("root::0:0:root:/:/bin/sh\n")
                                    else:
                                        f.write("root::::::::\n")
                                else:
                                    f.write(line)


# Replace tty respawning
def replace_tty_login(work_dir, image_path):

    logging.debug("Replacing default ttyS0 program to /bin/sh")
    init_file = "inittab"

    with mounted(work_dir, image_path) as fs_path:
        for path, subdir, files in os.walk(fs_path):
            for file_name in files:
                if file_name == init_file:
                    file_path = os.path.join(path, file_name)
                    if magic.from_file(file_path) == "ASCII text":
                        lines = []
                        with open(file_path, "r") as f:
                            lines = f.readlines()
                        os.chmod(file_path, stat.S_IWRITE)
                        with open(file_path, "w") as f:
                            for line in lines:
                                if "ttyS0" in line:
                                    f.write("ttyS0::respawn:/bin/sh\n")
                                else:
                                    f.write(line)


@contextmanager
def mounted(work_dir, image_path):

    device = get_mounted_device(image_path)

    mount_path = make_mount_path(work_dir, device)

    fix_permissions(work_dir)

    yield mount_path

    cleanup_image_and_device(image_path, device)


def del_file(work_dir, image_path, file_path):

    logging.debug("Deleting file {}".format(file_path))
    file_path = file_path.lstrip("/")

    with mounted(work_dir, image_path) as fs_path:
        temp_path = os.path.join(fs_path, file_path)
        print(temp_path)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        elif os.path.islink(temp_path):
            os.unlink(temp_path)
        else:
            logging.warning("Can't delete file {}".format(file_path))


def add_file(work_dir, image_path, local_file, result_path):

    result_path = result_path.lstrip("/")

    if not os.path.exists(local_file):
        raise RuntimeError("No local file {}".format(local_file))

    with mounted(work_dir, image_path) as fs_path:
        temp_path = os.path.join(fs_path, result_path)
        if os.path.isdir(local_file):
            shutil.copytree(local_file, temp_path)
        else:
            shutil.copy(local_file, temp_path)


def make_image(root_fs_tar, arch, work_dir):

    if isinstance(root_fs_tar, str):
        logging.info("root_fs_tar was string, converted to tarfile")
        root_fs_tar = tarfile.open(root_fs_tar)

    # work_dir = tempfile.TemporaryDirectory()

    image_path = os.path.join(work_dir, image_name)

    create_image(image_path)

    make_partition_table(image_path)

    device = get_mounted_device(image_path)

    mkfs_device(device)

    mount_path = make_mount_path(work_dir, device)

    fix_permissions(work_dir)

    root_fs_tar.extractall(path=mount_path)

    make_firmadyne_dirs(mount_path)

    patch_filesystem(mount_path)

    setup_firmadyne(mount_path, arch)

    cleanup_image_and_device(image_path, device)

    return image_path


def fix_permissions(mount_path):

    username = os.environ["USER"]

    fix_chown = chown_cmd.format(username, username, mount_path)

    subprocess.call(fix_chown, shell=True)


def mkfs_device(device):

    mkfs_run_cmd = mkfs_cmd.format(device)

    subprocess.check_call(mkfs_run_cmd, shell=True)

    os.sync


def cleanup_image_and_device(image_path, device):

    umount_cmd_cleanup = umount_cmd.format(device)
    kpartx_cmd_cleanup = kpartx_cmd.format(image_path)
    # losetup_cmd_cleanup = losetup_cmd.format(device)

    device_basename = os.path.basename(device)

    # dmsetup_cmd_cleanup = dmsetup_cmd.format(device_basename)

    cleanup_commands = [umount_cmd_cleanup, kpartx_cmd_cleanup]

    for command in cleanup_commands:
        try:
            subprocess.check_call(command, shell=True)
        except subprocess.CalledProcessError as e:
            print(e)


def setup_firmadyne(mount_path, arch):

    # Paths on local disk
    console_path = get_console(arch)
    nvram_path = get_nvram(arch)
    pre_init_path = get_preinit()

    # Paths on mounted device
    mounted_console = os.path.join(mount_path, console_mount_path)
    mounted_nvram = os.path.join(mount_path, nvram_mount_path)
    mounted_preinit = os.path.join(mount_path, pre_init_mount_path)

    # Copy files
    shutil.copyfile(console_path, mounted_console)
    shutil.copyfile(nvram_path, mounted_nvram)
    shutil.copyfile(pre_init_path, mounted_preinit)

    # chmod a+x
    all_exec = stat.S_IXGRP | stat.S_IXOTH | stat.S_IXUSR

    os.chmod(mounted_console, all_exec)
    os.chmod(mounted_nvram, all_exec)
    os.chmod(mounted_preinit, all_exec)

    # Force all copies and writes to finish
    os.sync()


def get_preinit():

    return os.path.join(parent_directory, pre_init_name)


# Get console binary given arch
def get_console(arch):

    console_arch = console_name.format(arch)

    binary_folder = os.path.join(parent_directory, "binaries")

    return os.path.join(binary_folder, console_arch)


# Get libnvram library given arch
def get_nvram(arch):

    nvram_arch = nvram_name.format(arch)

    binary_folder = os.path.join(parent_directory, "binaries")

    return os.path.join(binary_folder, nvram_arch)


def patch_filesystem(mount_path):

    busybox_path = shutil.which("busybox")

    # Stage files for patch
    busybox_mount_path = os.path.join(mount_path, "busybox")
    fix_image_mount_path = os.path.join(mount_path, "fixImage.sh")

    shutil.copyfile(busybox_path, busybox_mount_path)

    shutil.copyfile(fix_image_path, fix_image_mount_path)

    # chmod a+x
    all_exec = stat.S_IXGRP | stat.S_IXOTH | stat.S_IXUSR

    os.chmod(busybox_mount_path, all_exec)
    os.chmod(fix_image_mount_path, all_exec)

    fix_image_cmd = fix_image_command.format(mount_path)

    subprocess.check_call(fix_image_cmd, shell=True)

    # Cleanup patch
    os.remove(busybox_mount_path)
    os.remove(fix_image_mount_path)


def make_firmadyne_dirs(mount_path):

    firmadyne_path = os.path.join(mount_path, base_path)

    try:
        os.mkdir(firmadyne_path)
    except FileExistsError:
        pass

    firmadyne_nvram_path = os.path.join(firmadyne_path, nvram_path)

    try:
        os.mkdir(firmadyne_nvram_path)
    except FileExistsError:
        pass

    firmadyne_override_path = os.path.join(firmadyne_path, override_path)

    try:
        os.mkdir(firmadyne_override_path)
    except FileExistsError:
        pass


def make_mount_path(work_dir, device):

    mount_path = os.path.join(work_dir, mount_dir)

    if not os.path.exists(mount_path):
        os.mkdir(mount_path)

    mount_cmd = mount_format.format(device, mount_path)

    subprocess.check_call(mount_cmd, shell=True)

    return mount_path


def get_mounted_device(image_path):

    mount_cmd = kpart_cmd.format(image_path)

    proc_output = subprocess.check_output(mount_cmd, shell=True)

    loop_device = proc_output.decode("UTF-8").split()[2]

    device = mapper_str.format(loop_device)

    print("[+] loop device at {}".format(device))

    return device


def create_image(image_path):

    image_cmd = make_image_cmd.format(image_path)

    subprocess.check_call(image_cmd, shell=True)


def make_partition_table(image_path):

    partition_table_cmd = fdisk_cmd.format(image_path)

    proc = subprocess.Popen(partition_table_cmd, stdin=subprocess.PIPE, shell=True)

    proc.communicate(partition_cmd_input)

    if proc.returncode != 0:
        raise (RuntimeError("Make partition table failed"))
