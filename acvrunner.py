import os
import logging
import subprocess
import math
import argparse
import shutil

import config

def main():
    all_apps_list = os.listdir(config.APK_REPOSITORY)
    row_apps_list = [x for x in all_apps_list if is_row_app(x)]
    
    [process_apk(x) for x in row_apps_list]

    print("main")
    

def is_row_app(path):
    basename = os.path.basename(path)
    return not basename.endswith("_instrumented.apk")

def acvtool_instrument(apk_path):
    cmd = "{0} {1} instrument -r {2} -o {3}".format(config.PYTHON, 
        os.path.join(config.ACVTOOL_PATH, 'smiler', 'acvtool.py'),
        apk_path, config.ACVTOOL_WD)
    result = request_pipe(cmd)
    return result

def process_apk(apk_path):
    acvtool_instrument(apk_path)
    
    package_name = os.path.basename(apk_path)[:-4]
    pickle = os.path.join(config.ACVTOOL_WD, "metadata", package_name + ".pickle")
    instrumented_apk = os.path.join(config.ACVTOOL_WD, , "instr_" + package_name + ".apk")
    android_manifest = os.path.join(config.ACVTOOL_WD, "apktool", "AndroidManifest.xml")
    
    shutil.copy(pickle, os.path.join(config.ACVTOOL_RESULTS, package_name + ".pickle")
    shutil.copy(instrumented_apk, os.path.join(config.ACVTOOL_RESULTS, package_name + ".apk"))
    shutil.copy(android_manifest, os.path.join(config.ACVTOOL_RESULTS, package_name + ".xml"))

if __name__ == "__main__":
    parser = get_parser()
    #args = parser.parse_args()
    #args = parser.parse_args([r"C:\apks\originalapk\FDroid.apk"])
    #print(args.apk_path)
    #run_actions(args)
    main()

