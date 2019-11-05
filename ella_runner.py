import os
import logging
import subprocess
import math
import argparse
import shutil
from io import open

import config
import sys

ELLA_RESULTS = os.path.join(config.ELLA, "ella-out")

def main():
    all_files = os.listdir(config.APK_REPOSITORY)
    row_apps_pkgs_list = [x[:-4] for x in all_files if is_row_app(x)]
    if not os.path.exists(ELLA_RESULTS):
        os.makedirs(ELLA_RESULTS)
    done_list_path = os.path.join(ELLA_RESULTS, "done_list.txt")
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
                apk_path = os.path.join(config.APK_REPOSITORY, pkg + '.apk')
                ella_out_dir = apk_path.replace("/", "_").replace("\\", "_").replace(":", "_")
                instrumented_apk_path = os.path.join(ELLA_RESULTS, ella_out_dir, "instrumented.apk")
                print(f"{instrumented_apk_path}")
                result = ella_instrument(apk_path)
                check_result(done_list_file, instrumented_apk_path, pkg, result)
                logging.info('{} ELLA: {}'.format(pkg, result))
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


def check_result(done_list_file, out_path, package, result):
    if os.path.exists(out_path):
        logging.info('{}.apk: SUCCESS'.format(package))
        done_list_file.write(u'{}: SUCCESS\n'.format(package))
        done_list_file.flush()
        return True
    else:
        logging.exception('{}: FAIL : {}'.format(package, result))
        done_list_file.write(u'{}: FAIL\n'.format(package))
        done_list_file.flush()
        return False


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

def ella_instrument(apk_path):
    cmd = f"java -ea -classpath {config.ELLA}/bin/ella.instrument.jar com.apposcopy.ella.EllaLauncher i {apk_path}"
    result = request_pipe(cmd)
    return result


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


if __name__ == "__main__":
    logging.basicConfig(filename="log.log", level=logging.DEBUG)
    done_file_stats()
    main()
    done_file_stats()
