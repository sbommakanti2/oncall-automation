#!/usr/bin/python3
"""
Python3 script for Start, stop, restart process that are missing
Requirements: subprocess, time, sys, argparse
Input: None
Author: Shivakumar Bommakanti
ver 1 : Created - 04-04-2023
ver 2 : Added possible values to Process argument - 18-12-2023
"""
import subprocess
import sys
import time
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
    process = subprocess.Popen("/bin/bash", shell=True, universal_newlines=True,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    for command in commands:
        command += "\n"
        process.stdin.write(command)
    process.stdin.flush()
    stdout, stderr = process.communicate()
    process.stdin.close()
    return stdout, stderr

def run_action_command(action, process, no_console=True):
    """
    Runs commond in neolane user for given action and process
    :return: output
    """
    if no_console:
        end = " -noconsole' > /dev/null &"
    else:
        end = "'"
    commands = [
        "nohup /usr/bin/sudo -u neolane bash -c '. /usr/local/neolane/nl*/env.sh ; nlserver " + action + " " +process+end+""
    ]
    print(commands)
    try:
        result = subprocess.check_output(
            commands[0], shell=True, universal_newlines=True, timeout=15)
    except subprocess.TimeoutExpired:
        print("timed out")
        sys.exit(0)
    return result

def get_hostname_new():
    """Gets the hostname from predefined commands new/updated

    Returns:
        hostname: string
    """
    hostname = ""
    stdout, stderr = run_commands(
        ["ls /usr/local/neolane/nl*/conf/config*xml | grep -v default | cut -d. -f1 | cut -d'-' -f2"])
    if stderr:
        print("error in fetching hostname")
    else:
        hostname = stdout.replace('\n', '').replace('\t', '').replace(' ', '')

    return hostname

def get_process_hostname():
    """Gets the hostname from predefined commands new/updated

    Returns:
        hostname: string
    """
    hostname = []
    stdout = run_action_command('monitor', '-missing', False)

    lineno = 0
    lines = stdout.split("\n")
    for line in lines:
        if lineno > 0:
            hostname.append(line)
        lineno +=1
    
    print("here is hostname in non-stop")
    print(hostname)
    return hostname

def action_process(process, action):
    """Perform given action the inmail nlserver

    Returns:
        None
    """

    if action == 'stop':
        hostname = get_hostname_new()
        print("its in stop - here is hostname " + hostname)
        time.sleep(5)
        commands = [
            "nohup /usr/bin/sudo -u neolane bash -c '. /usr/local/neolane/nl*/env.sh ; nlserver " + action + " " + process + "@" +
            hostname + " -noconsole' > /dev/null &"
        ]
        print(commands)
        try:
            result = subprocess.check_output(
                commands[0], shell=True, universal_newlines=True, timeout=15)
            print(result)
            print('Successfull performed ' + action + ' on ' + process)
        except subprocess.TimeoutExpired:
            print("timed out")
            sys.exit(0)

        time.sleep(5)
    else:
        hostname = get_process_hostname()

        if len(hostname) > 0:
            for proc in hostname:
                if proc.startswith(process):
                    result = run_action_command(action, proc)
                    print(result)
                    print('Successfull performed ' + action + ' on ' + proc)
                    break;
            else:
                print('Didnt perform action as their is a process missing but not matching with given input')
                sys.exit(0)
        else:
            print('Skipped action given as their is no missing process')

if __name__ == '__main__':

    exe_process = """ 
                        Required Arguments for each step:
                        Action, 
                        Process_name from [inmail, mta, pipelined, syslogd, trackinglogd, web, wfserver]
                        Choose Action from [start, stop, restart]
                  """
    parser = argparse.ArgumentParser(
        epilog=exe_process, formatter_class=RawTextHelpFormatter)
    required_parser = parser.add_argument_group('required arguments')
    required_parser.add_argument("-a", "--action", help="Action")
    required_parser.add_argument("-p", "--process_name", help="Process Name",
                                 choice = ["inmail", "mta", "pipelined", "syslogd", "trackinglogd", "web", "wfserver"])

    args_namespace = parser.parse_args()
    args = vars(args_namespace)

    action = args.get('action')
    process_name = args.get('process_name')

    action_process(process_name, action)
