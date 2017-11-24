import os, sys
import logging
import subprocess
import shutil

import config

def main():
    all_apps_list = os.listdir(config.APK_REPOSITORY)
    row_apps_list = [x for x in all_apps_list if is_row_app(x)]
    
    if not os.path.exists(config.APKTOOL_RESULTS):
        os.makedirs(config.APKTOOL_RESULTS)
    done_list_path = os.path.join(config.APKTOOL_RESULTS, "done_list.txt")
    ignore_done_list = False
    with open(done_list_path, 'a+') as done_list_file:
        projects_to_process = set(row_apps_list)
        counter = 0
        fail_counter = 0
        if not ignore_done_list:
            done_project_names = get_done_project_names(done_list_file)
            logging.info('================================================================================================================================================')
            logging.info(f'DONE LIST SIZE: {len(done_project_names)}')
            logging.debug(f'DONE LIST CONTENT: {done_project_names}')
            projects_to_process = projects_to_process - set(done_project_names)
            counter = len(done_project_names)
            fail_counter = get_fail_counter(done_list_file)
        for file_name in row_apps_list:
            try:
                result = apktool_unpack(os.path.join(config.APK_REPOSITORY, file_name))
                logging.info(f'{file_name} APKTOOL: {result}')
                result = apktool_pack(file_name)
                logging.info(f'{file_name} APKTOOL: {result}')
                package_name = file_name[:-4]
                logging.info(f'{package_name}: SUCCESS')
                done_list_file.write(f'{package_name}: SUCCESS\n')
                done_list_file.flush()
                #JsonWriter(project_names).save_to_json()
                counter += 1
            except KeyboardInterrupt:
                logging.info('Keyboard interrupt.')
                sys.exit()
            except Exception as e:
                logging.exception(f'{file_name}: FAIL : {e}')
                fail_counter += 1
                done_list_file.write(f'{file_name}: FAIL\n')
                done_list_file.flush()
    
    logging.info(f'{counter}: proccessed from {len(all_apps_list)}. Failed: {fail_counter}.')

    print("Finished.")
    

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
    return not basename.endswith("_instrumented.apk")


def apktool_unpack(apk_path):
    #cmd = ""
    cmd = f"java -jar {config.APKTOOL_PATH} d -o {config.APKTOOL_WD} -f {apk_path}"
    result = request_pipe(cmd)
    return result

def apktool_pack(file_name):
    cmd = f"java -jar {config.APKTOOL_PATH} b -f -o \
{os.path.join(config.APKTOOL_RESULTS, file_name)} {config.APKTOOL_WD}"
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
    done_list_path = os.path.join(config.APKTOOL_RESULTS, "done_list.txt")
    if not os.path.exists(done_list_path):
        logging.info("Done file is empty yet.")
        return
    with open(done_list_path, 'r+') as done_list_file:
        #text = done_list_file.read()
        done_project_names = get_done_project_names(done_list_file)
        fail_counter = get_fail_counter(done_list_file)
        print("DONE FILE STATS:")
        print(f'Whole number of the projects: {len(done_project_names)}. Failed: {fail_counter}')


if __name__ == "__main__":
    done_file_stats()
    main()
