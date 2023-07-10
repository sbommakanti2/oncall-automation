#!/usr/bin/python3
"""
Python3 script for fixing sequencegap of user's input
Requirements: subprocess, time, logging
Input: None
Author: Shivakumar Bommakanti
Date: 21-03-2023
"""
import subprocess
import time
import logging
import argparse
from argparse import RawTextHelpFormatter

def run_commands(commands):
    """Runs unix commands using subprocess module

    Args:
        commands (list): list of commands to execute

    Returns:
        stdout: output of the commands
        stderr: standard error if any
    """
    process = subprocess.Popen("/bin/bash", shell=True, universal_newlines=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    for command in commands:
        command += "\n"
        process.stdin.write(command)
    process.stdin.flush()
    stdout, stderr = process.communicate()
    process.stdin.close()
    return stdout, stderr

def _is_is_ACC_or_ACS():
    commands = ["/usr/bin/sudo -u neolane bash -c '. /usr/local/neolane/nl*/env.sh ; nlserver pdump -full web'"]
    stdout, stderr = run_commands(commands)
    return stdout, stderr

def _get_instance_name():
    commands = ["ls /usr/local/neolane/nl*/conf/config*xml | grep -v default |cut -d. -f1 |cut -d'-' -f2"]
    stdout, stderr = run_commands(commands)
    return stdout, stderr

def get_db_name():
    """Gets the database name from predefined commands

    Returns:
        db name: string
    """
    dbname = ""
    stdout, stderr = run_commands(["cat /usr/local/neolane/nl*/conf/config-*.xml | grep db | grep login | awk -F'login=\"' '{print $2}' | awk -F':' '{print $1}'"])
    if stderr:
        print("error in fetching dbname")
        logging.info("error in fetching dbname")
    else:
        dbname = stdout.replace('\n', '').replace('\t', '').replace(' ', '')

    return dbname


def _file_update(file_name, sequence, ulimit):
    f = open(file_name, "r")
    data = f.read().replace("USER_SEQUENCE",sequence)
    data = data.replace("10000000", ulimit)
    nfile = file_name.split(".")[0]+"-test.js"
    print('New file', nfile)
    fw = open(nfile, "w+")
    fw.write(data)
    return nfile

if __name__ == '__main__':
    exe_process = """Please enter sequence example: xtknewid and ignorenegative Filepath optional"""
    parser = argparse.ArgumentParser(
        epilog=exe_process, formatter_class=RawTextHelpFormatter)
    required_parser = parser.add_argument_group('required arguments')
    parser.add_argument("-s", "--sequence", help="Sequence ID")
    parser.add_argument("-fp", "--file_path", help="File Path")
    args_namespace = parser.parse_args()
    args = vars(args_namespace)

    stdout, stderr = _is_is_ACC_or_ACS()
    if stderr:
        print(stderr)
        exit(1)
    logging.info(stdout)
    print(stdout)

    instance, stderr = _get_instance_name()
    if stderr:
        print(stderr)
        logging.info(stderr)
        exit(1)

    instance_name = instance.strip().strip("\n").strip("\t")

    sequence = args.get("sequence", "")
    if sequence == "" :
        logging.info("no sequence, exiting")
        exit(1)
    if "file_path" in args:
        file_path = args.get("file_path", "")

    if "Adobe Campaign Classic" in stdout:
        if file_path == "" or file_path is None:
            file_path = "/usr/local/neolane/acc_sequences_gapFinder.js"
        new_file = _file_update(file_path, sequence, "50000000")
        commands = ["/usr/bin/sudo -u neolane bash -c '. /usr/local/neolane/nl*/env.sh ;  nlserver javascript -instance:"+instance_name+" -file "+new_file+"'"]
    else:
        if file_path == "" or file_path is None:
            file_path = "/usr/local/neolane/acs_sequences_gapFinder.js"
        new_file = _file_update(file_path, sequence, "50000000")
        commands = ["/usr/bin/sudo -u neolane bash -c '. /usr/local/neolane/nl*/env.sh ;  nlserver javascript -instance:"+instance_name+" -file "+new_file+"'"]

    stdout, stderr = run_commands(commands)
    if stderr:
        print(stderr)
        logging.info(stderr)
        exit(1)
    print("stdout",stdout)

    #To test negativity
    #f1 = open('/root/res.out', "r")
    #stdout = f1.read()

    lines = stdout.split("\n")
    high = 0
    index = 0
    ignoreIndex = 10000
    for line in lines:
        if "start" in line or "Result" in line:
            print('ignore ',index)
            ignoreIndex = index
            continue
        if '|' in line:
            if index > ignoreIndex+1 and (int(line.split('|')[1].strip()) < 0 or int(line.split('|')[2].strip()) < 0):
                print('Negative sequence, Get confirmation before reset -- Exiting')
                exit(1)
            else:
                high = max(int(line.split('|')[1].strip()), high)

        index += 1

    print("high value {}".format(high))
    logging.info("high value {}".format(high))
    # dbname = get_db_name()
    # alter_command = "psql -d "+dbname+" -c \"ALTER SEQUENCE {} RESTART WITH {};\"".format(sequence, high)
    # print(alter_command)
    # stdout, stderr = run_commands([alter_command])