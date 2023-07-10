"""
Python wrapper to check if login user exist or recreating password and restarting servers
Requirements: subprocess,os
Input: Tenant id
Author: Shivakumar Bommakanti
Date: 25-04-2023
"""

import subprocess
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

def get_db_name():
    """Gets the database name from predefined commands

    Returns:
        db name: string
    """
    dbname = ""
    stdout, stderr = run_commands(
        ["cat /usr/local/neolane/nl*/conf/config-*.xml | grep db | grep login | awk -F'login=\"' '{print $2}' | awk -F':' '{print $1}'"])
    if stderr:
        print("error in fetching dbname")
    else:
        dbname = stdout.replace('\n', '').replace('\t', '').replace(' ', '')

    return dbname

def _is_is_ACC_or_ACS():
    commands = ["/usr/bin/sudo -u neolane bash -c '. /usr/local/neolane/nl*/env.sh ; nlserver pdump -full web'"]
    stdout, stderr = run_commands(commands)
    return stdout, stderr

def set_neolane_env():
    commands = ['source /usr/local/neolane/nl*/env.sh']
    stdout, stderr = run_commands(commands)
    return stdout, stderr

def _get_instance_name():
    commands = ["ls /usr/local/neolane/nl*/conf/config*xml | grep -v default |cut -d. -f1 |cut -d'-' -f2"]
    stdout, stderr = run_commands(commands)
    return stdout, stderr

def update_folder_settings(instance_id):
    print("here is the instance id")
    print(instance_id)
    run_workflow_command = "/usr/local/neolane ; nlserver javascript -instance:{} -file " \
                           "/etc/newrelic-infra/custom-integrations/loginmonitor/update_folder_settings.js'"\
                            .format(instance_id)
    commands = [run_workflow_command]
    stdout, stderr = run_commands(commands)
    return stdout, stderr

def create_credentials(instance_id):
    print("here is the instance id")
    print(instance_id)
    run_workflow_command = "/usr/local/neolane ; nlserver javascript -instance:{} -file " \
                           "/etc/newrelic-infra/custom-integrations/loginmonitor/create_credentials.js -arg:{}}'"\
                            .format(instance_id,pwd)
    commands = [run_workflow_command]
    stdout, stderr = run_commands(commands)
    return stdout, stderr

def create_file(file_path, data):
    with open(file_path, 'w+') as fp:
        fp.write(data)

        fp.close()
    #os.chown(file_path, neolane_uid, neolane_gid)
    return

def check_for_failed_login(query_param,param2):
    """This will return all critical failed workflows for you.

    Args: None

    Return output which contains status and error if any
    :rtype: Std output and error
    """
    dbname = get_db_name()
    sql_retrieve_command = "psql -d " + dbname + \
                           " -c \"select * from {} where sname like '{}';\"".format(query_param, param2);
    print(sql_retrieve_command)
    stdout, stderr = run_commands([sql_retrieve_command])
    print(stderr)
    return stdout, stderr

if __name__ == '__main__':

    exe_process = """
                        Required Arguments for each step:
                        tenant_id
                        """
    parser = argparse.ArgumentParser(
        epilog=exe_process, formatter_class=RawTextHelpFormatter)
    required_parser = parser.add_argument_group('required arguments')
    required_parser.add_argument("-ti", "--tenant_id", help="Tenant ID")

    args_namespace = parser.parse_args()
    args = vars(args_namespace)

    tenant_id = args.get('tenant_id')

    stdout, stderr = _is_is_ACC_or_ACS()
    if stderr:
        print(stderr)
        exit(1)
    print(stdout)

    query_param = None
    isAcc = False
    if "Adobe Campaign Classic" in stdout:
        query_param = "xtkoperator"
        isAcc = True
    else:
        query_param = "xtkuser"
        isAcc = False

    param2 = 'campaign-loginmonitor'

    stdout, stderr = check_for_failed_login(query_param, param2)
    if stderr:
        print(stderr)
        exit(1)
    print("stdout " + stdout)
    if param2 not in stdout:
        #random password generation
        process = subprocess.Popen(['openssl', 'rand', '-base64', '15'], shell=True, universal_newlines=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pwd, stderr = process.communicate()

        print("password created", pwd)

        stdout, stderr = set_neolane_env()
        if stderr:
            print(stderr)
            exit(1)
        print("Neolane env set", stdout)

        stdout, stderr = _get_instance_name()
        if stderr:
            print(stderr)
            exit(1)
        instance_name = stdout.strip().strip("\n").strip("\t")
        print("instance name", instance_name)

        if isAcc :
            stdout, stderr = update_folder_settings(instance_name)
            if stderr:
                print(stderr)
                exit(1)
            print('Update folder settings', stdout)

            stdout, stderr = create_credentials(instance_name)
            if stderr:
                print(stderr)
                exit(1)
            print('create credentials', stdout)
            create_file("/tmp/new_password", pwd)
    else:
        print("No need to update login monitor")