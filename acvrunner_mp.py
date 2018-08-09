#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
This script runs 

Author:       Yury Zhauniarovich
Date created: 07/08/2018
'''


import os
import json
import config
import shutil
import signal
import logging
import logging.config
import subprocess
import multiprocessing as mp

from io import open

IGNORE_PROCESSED = False

MULTIPROCESSING = True
# NUM_OF_PROC = 3
NUM_OF_PROC = mp.cpu_count() + 2



# logging setup
def setup_logging(
    default_path='logging.json',
    default_level=logging.DEBUG,
    env_key='LOG_CFG'
):
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'r') as f:
            config = json.load(f)
            logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)

setup_logging()
logger = logging.getLogger(__name__)
# logger = multiprocessing.get_logger()
# endof logging setup


def acvtool_instrument(apk_path):
    cmd = "{0} {1} instrument -f -g {2} --wd {3} {4}".format(config.ACVTOOL_PYTHON, 
        os.path.join(config.ACVTOOL_PATH, 'acvtool.py'), config.GRANULARITY,
        config.ACVTOOL_WD, apk_path)
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


def get_pkgs_data(done_list_path):
    success_pkgs = set()
    failed_pkgs = set()
    if not os.path.exists(done_list_path):
        return success_pkgs, failed_pkgs 
    with open(done_list_path, "r", encoding="utf-8") as res_fd:
        for indx, line in enumerate(res_fd):
            (pkg, status) = line.split(':')
            pkg = pkg.strip()
            status = status.strip()
            if status == "SUCCESS":
                success_pkgs.add(pkg)
            elif status == "FAIL":
                failed_pkgs.add(pkg)
            else:
                logger.error("Strange line: {}".format(line))
    return success_pkgs, failed_pkgs
    

def remove_file(f):
    if os.path.exists(f):
        os.remove(f)


def process_pkg(pkg, res_queue):
# def process_pkg(pkg, res_fd):
    logger.info("Processing: {}".format(pkg))
    result = acvtool_instrument(os.path.join(config.APK_REPOSITORY, pkg + '.apk'))
    logger.info('{} ACVTOOL: {}'.format(pkg, result))
    
    pickle = os.path.join(config.ACVTOOL_WD, "metadata", pkg + ".pickle")
    instrumented_apk = os.path.join(config.ACVTOOL_WD, "instr_" + pkg + ".apk")

    if os.path.exists(pickle) and os.path.exists(instrumented_apk):
        app_dir = os.path.join(config.ACVTOOL_RESULTS, pkg)
        if not os.path.exists(app_dir):
            os.makedirs(app_dir)
        shutil.move(pickle, os.path.join(app_dir, pkg + ".pickle"))
        shutil.move(instrumented_apk, os.path.join(app_dir, pkg + ".apk"))
        logger.info('{}.apk: SUCCESS'.format(pkg))
        process_result = (pkg, "SUCCESS")
    else:
        logger.info('{}.apk: FAIL'.format(pkg))
        process_result = (pkg, "FAIL")

    original_apk_at_wd = os.path.join(config.ACVTOOL_WD, pkg + ".apk")
    remove_file(original_apk_at_wd)
    remove_file(instrumented_apk)
    remove_file(pickle)

    res_queue.put(process_result)
    return process_result


def listener(q, fn):
    '''listens for messages on the q, writes to file. '''
    f = open(fn, 'a', encoding='utf-8')
    while 1:
        m = q.get()
        if m == 'kill':
            logger.info("Received kill signal. Stop writing...")
            break
        f.write(u'{} : {}\n'.format(m[0], m[1]))
        f.flush()
    f.close()    


def main():
    if not os.path.exists(config.ACVTOOL_RESULTS):
        os.makedirs(config.ACVTOOL_RESULTS)
    all_apk_files = [f for f in os.listdir(config.APK_REPOSITORY) if f.endswith(".apk")]
    all_pkgs = [x[:-4] for x in all_apk_files]
    
    done_list_path = os.path.join(config.ACVTOOL_RESULTS, "done_list.txt")
    success_pkgs, failed_pkgs = get_pkgs_data(done_list_path)
    
    logger.info("="*80)
    pkgs_to_process = set(all_pkgs)
    if not IGNORE_PROCESSED:
        logger.info("Counting already processed packages.")
        pkgs_to_process = pkgs_to_process.difference(success_pkgs)
        pkgs_to_process = pkgs_to_process.difference(failed_pkgs)
    else:
        logging.info("Ignoring already processed packages.")
        remove_file(done_list_path)

    logger.info("Need to process: {}".format(len(pkgs_to_process)))
    logger.info("="*80)


    manager = mp.Manager()
    q = manager.Queue()
    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    pool = mp.Pool(NUM_OF_PROC)
    signal.signal(signal.SIGINT, original_sigint_handler)
    #put listener to work first
    watcher = pool.apply_async(listener, (q, done_list_path))
    try:
        proc_results = [pool.apply_async(func=process_pkg, args=(pkg, q)) for pkg in pkgs_to_process]
        results = [res.get() for res in proc_results]
    except KeyboardInterrupt:
        logging.info("Keyboard Interrupt. Stop processing.")
        # q.put('kill')
        pool.terminate()
    else:
        q.put('kill')
        pool.close()
    pool.join()



if __name__ == '__main__':
    main()