import tempfile
import os
import logging
import shutil
from lib.extractor_techniques.extractor import Extractor

# from extractor_techniques.extractor import Extractor

# returns tar of rootfs
def extract_image(firmware_path, work_dir):

    for technique in technique_list:
        root_fs_tar = technique(firmware_path, work_dir)
        if root_fs_tar:
            return root_fs_tar

    logging.warn("Failed to extract firmware")

    return None


# from sources.extractor.extractor import Extractor
def extractor_firmadyne(firmware_path, work_dir):

    logging.info("Using firmadyne extractor")

    # Create Firmadyne extractor
    firm_extractor = Extractor(firmware_path, work_dir)

    firm_extractor.extract()

    contents = os.listdir(work_dir)

    if len(contents) > 1:
        logging.info("Extractor extracted more than one rootfs... weird")
        file_loc = os.path.join(work_dir, contents[0])
        return file_loc
    elif contents:
        file_loc = os.path.join(work_dir, contents[0])
        return file_loc
    else:
        logging.warn("Firmadyne extractor failed")
        return None


technique_list = [extractor_firmadyne]
