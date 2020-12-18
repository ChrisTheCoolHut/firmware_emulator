#!/usr/bin/env python
# wget http://files.dlink.com.au/products/DIR-320/REV_A/Firmware/Firmware_v1.21b03/DIR320A1_FW121WWB03.bin
import logging

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("cle").setLevel("WARNING")
import tempfile
from lib import extract_helper
from lib import image_helper
from lib import arch_helper
from lib import qemu_runner
import argparse
import atexit
import shutil
import os


def do_clean():
    import os, shutil

    tmp_list = os.listdir("/tmp/")
    for dir in tmp_list:
        if "tmp" in dir:
            dir_path = os.path.join("/tmp/", dir)
            try:
                shutil.rmtree(dir_path)
            except:
                pass


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("Firmware")

    print("Cleaning /tmp/")
    do_clean()

    args = parser.parse_args()

    tmp_dir = tempfile.TemporaryDirectory()

    fw = args.Firmware

    fw_tar = extract_helper.extract_image(fw, tmp_dir.name)
    try:
        arch = arch_helper.get_arch(fw_tar)
    except Exception as e:
        print(e)
        tmp_dir.cleanup()
        return

    image = image_helper.make_image(fw_tar, arch.qemu_name, tmp_dir.name)
    runner = qemu_runner.QemuImage(
        arch.qemu_name, arch.memory_endness, image, tmp_dir.name, False
    )

    file_name = os.path.basename(args.Firmware)
    output_folder = os.path.dirname(args.Firmware)
    runner_name = file_name + "_runner_"

    if not runner.setup_network():
        print("Failed initial network emulation. Trying harder")
        image_helper.force_networking(tmp_dir.name, image)
        try:
            image_helper.del_file("/sbin/reboot")
        except:
            pass
        runner_name += "forced_"
        if not runner.setup_network():
            print("Failed network emulation for {}".format(args.Firmware))
            output_location = os.path.join(output_folder, "failed")
            with open(output_location, "w") as f:
                f.write("Failed to emulate")
            tmp_dir.cleanup()
            return

    runner_name += ".sh"

    output_location = os.path.join(output_folder, runner_name)

    runner.export(output_folder, script_name=runner_name, script_only=True)

    tmp_dir.cleanup()


if __name__ == "__main__":
    main()
