import os
import logging
from logging import config
import yaml
import subprocess
import math
import argparse
import shutil
from io import open

import config
import sys

def main():
    all_files = os.listdir(config.APK_REPOSITORY)
    row_apps_pkgs_list = [x[:-4] for x in all_files if is_row_app(x)]
    if not os.path.exists(config.ACVTOOL_RESULTS):
        os.makedirs(config.ACVTOOL_RESULTS)
    done_list_path = os.path.join(config.ACVTOOL_RESULTS, "done_list.txt")
    ignore_done_list = False
    with open(done_list_path, 'a+', encoding='utf-8') as done_list_file:
        projects_to_process = set(row_apps_pkgs_list)
        #print("instrumented: {0}, original: {1}, intersection: {2}".format(len(instrumented_app_pkgs_list), len(row_apps_pkgs_list), len(projects_to_process)))
        counter = 0
        fail_counter = 0
        if not ignore_done_list:
            done_project_names = get_done_project_names(done_list_file)
            logging.info('================================================================================================================================================')
            logging.info("DONE LIST SIZE: {}".format(len(done_project_names)))
            logging.debug('DONE LIST CONTENT: {}'.format(done_project_names))
            projects_to_process = projects_to_process - set(done_project_names)
            counter = len(done_project_names)
            fail_counter = get_fail_counter(done_list_file)
        for pkg in projects_to_process:
            try:
                result = acvtool_instrument(os.path.join(config.APK_REPOSITORY, pkg + '.apk'))
                logging.info('{} ACVTOOL: {}'.format(pkg, result))
                move_files(pkg, done_list_file)
                counter += 1
            except KeyboardInterrupt:
                logging.info('Keyboard interrupt.')
                sys.exit()
            except Exception as e:
                logging.exception('{}: FAIL : {}'.format(pkg, e))
                fail_counter += 1
                done_list_file.write(u'{}: FAIL\n'.format(pkg))
                done_list_file.flush()
    logging.info('{}: proccessed from {}. Failed: {}.'.format(counter, len(all_files), fail_counter))

    logging.info("Finished.")
    

def get_done_project_names(done_list_file):
    done_list_file.seek(0)
    done_project_names = [line.split(': ')[0] for line in done_list_file.readlines()]
    return done_project_names


def get_fail_counter(done_list_file):
    done_list_file.seek(0)
    fail_counter = done_list_file.read().count('FAIL')
    return fail_counter


def is_row_app(path):
    basename = os.path.basename(path)
    return basename.endswith(".apk")


def acvtool_instrument(apk_path):
    cmd = "{0} {1} instrument -f -g {2} --wd {3} {4}".format(config.PYTHON, 
        os.path.join(config.ACVTOOL_PATH, 'acvtool.py'), config.GRANULARITY,
        config.ACVTOOL_WD, apk_path)
    result = request_pipe(cmd)
    return result

def move_files(package_name, done_list_file):
        pickle = os.path.join(config.ACVTOOL_WD, "metadata", package_name + ".pickle")
        instrumented_apk = os.path.join(config.ACVTOOL_WD, "instr_" + package_name + ".apk")
        #android_manifest = os.path.join(config.ACVTOOL_WD, "apktool", "AndroidManifest.xml")
        app_dir = os.path.join(config.ACVTOOL_RESULTS, package_name)
        if os.path.exists(pickle) and os.path.exists(instrumented_apk):
            if not os.path.exists(app_dir):
                os.makedirs(app_dir)
            shutil.move(pickle, os.path.join(app_dir, package_name + ".pickle"))
            shutil.move(instrumented_apk, os.path.join(app_dir, package_name + ".apk"))
            #shutil.move(android_manifest, os.path.join(config.ACVTOOL_RESULTS, package_name + ".xml"))
            original_apk_at_wd = os.path.join(config.ACVTOOL_WD, package_name + ".apk")
            if os.path.exists(original_apk_at_wd):
                os.remove(original_apk_at_wd)
            logging.info('{}.apk: SUCCESS'.format(package_name))
            done_list_file.write(u'{}: SUCCESS\n'.format(package_name))
            done_list_file.flush()
        else:
            raise Exception("ACVTOOL FAILED")
        
def request_pipe(cmd):
    pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = pipe.communicate()
    res = out
    if not out:
        res = err
    if pipe.returncode > 0:
        print("return_code: {0}".format(pipe.returncode))
    return res

def done_file_stats():
    done_list_path = os.path.join(config.ACVTOOL_RESULTS, "done_list.txt")
    if os.path.exists(done_list_path):
        with open(done_list_path, 'r') as done_list_file:
            #text = done_list_file.read()
            done_project_names = get_done_project_names(done_list_file)
            fail_counter = get_fail_counter(done_list_file)
            logging.info("DONE FILE STATS:")
            logging.info('Whole number of the projects: {}. Failed: {}'.format(len(done_project_names), fail_counter))
    else:
        logging.info("Processing was started from scratch.")

def setup_logging():
    with open('logging.yaml') as f:
        logging.config.dictConfig(yaml.safe_load(f.read()))

if __name__ == "__main__":
    setup_logging()
    done_file_stats()
    main()
    done_file_stats()
