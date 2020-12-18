import tempfile
import tarfile
import os
import cle
import logging

root_fs = "root_fs"


def get_arch(file_name):

    with tempfile.TemporaryDirectory() as tmp_dir:

        logging.info("Using {} as scratch directory".format(tmp_dir))

        fs_path = os.path.join(tmp_dir, root_fs)

        os.mkdir(fs_path)

        try:
            tar_rootfs = tarfile.open(file_name)
        except tarfile.ReadError:
            logging.warn("[-] Provided file {} is not a tar".format(file_name))
            exit(1)

        tar_rootfs.extractall(path=fs_path)

        files = get_files(fs_path)

        return get_arch_from_files(files)


def get_arch_from_files(files):

    for file_name in sorted(files):

        try:
            loaded_file = cle.Loader(file_name)
        except:
            continue

        file_arch = loaded_file.main_object.arch

        print(
            "[+] File {} found with arch {}".format(file_name.split("/")[-1], file_arch)
        )

        return file_arch
    return None


def get_files(directory):

    ret_list = []

    for root, dirs, files in os.walk(directory):
        for file_name in files:
            ret_list.append(os.path.join(root, file_name))

    return ret_list
