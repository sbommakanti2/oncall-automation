"""
Python wrapper to start/restart rteventprocessing workflow based on Campaign
Requirements: subprocess,os
Input: Tenant id, workflow name
Author: Shivakumar Bommakanti
Date: 20-06-2023
"""
import subprocess
import os
from pwd import getpwnam
import argparse
from argparse import RawTextHelpFormatter
import fileinput

neolane_uid = getpwnam('neolane').pw_uid
neolane_gid = getpwnam('neolane').pw_gid

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

def create_file(file_path, data):
    with open(file_path, 'w+') as fp:
        fp.write(data)

        fp.close()
    #os.chown(file_path, neolane_uid, neolane_gid)
    return

def run_workflow(instance_id):
    print("here is the instance id")
    print(instance_id)
    run_workflow_command = "/usr/bin/sudo -u neolane bash -c '. /usr/local/neolane/nl*/env.sh ; nlserver javascript -instance:{} -file /tmp/start_workflow.js'".format(instance_id)
    commands = [run_workflow_command]
    stdout, stderr = run_commands(commands)
    return stdout, stderr

def _get_instance_name():
    commands = ["ls /usr/local/neolane/nl*/conf/config*xml | grep -v default |cut -d. -f1 |cut -d'-' -f2"]
    stdout, stderr = run_commands(commands)
    return stdout, stderr

def check_ulimit_files():
    update_count = 0
    count = 0
    command = ['ls /usr/local/neolane/nl*/test.sh ']
    stdout, stderr = run_commands(command)

    for file in stdout.split("\n"):
        print(file)
        if file:
            with fileinput.FileInput(file,inplace=True) as f:
                for line in f:
                    count += 1
                    if count == 106 and not line.startswith('#'):
                        print('#ulimit -c 1000000\n',
                              end='')
                        update_count += 1
                    else:
                        print(line, end ='')

    with fileinput.FileInput('/usr/local/neolane/zerocrash/ulimit-hook-old', inplace=True,backup='.bak') as f1:
        for line in f1:
            if not line.startswith('#'):
                print('#'+line,end='')
                update_count += 1
            else:
                print(line, end ='')
    if update_count > 0:
        return True, update_count
    else:
        return False, update_count

def check_for_failed_workflows(query_param, workflow_name):
    """This will return all critical failed workflows for you.

    Args: None

    Return output which contains status and error if any
    :rtype: Std output and error
    """
    dbname = get_db_name()
    sql_retrieve_command = "psql -d " + dbname + \
                           " -c \"select istatus, ifailed from xtkworkflow where {}='{}';\"".format(query_param, workflow_name);
    print(sql_retrieve_command)
    stdout, stderr = run_commands([sql_retrieve_command])
    print(stderr)
    return stdout, stderr

def uncoditional_stop(instance_id):
    run_workflow_command = "/usr/bin/sudo -u neolane bash -c '. /usr/local/neolane/nl*/env.sh ; nlserver javascript -instance:{} -file /tmp/stop_workflow.js'".format(instance_id)
    commands = [run_workflow_command]
    stdout, stderr = run_commands(commands)
    return stdout, stderr

if __name__ == '__main__':

    exe_process = """
                        Required Arguments for each step:
                        tenant_id, workflow name
                        """
    parser = argparse.ArgumentParser(
        epilog=exe_process, formatter_class=RawTextHelpFormatter)
    required_parser = parser.add_argument_group('required arguments')
    #required_parser.add_argument("-ti", "--tenant_id", help="Tenant ID")
    required_parser.add_argument("-wn", "--workflow_name", help="Workflow Name")

    args_namespace = parser.parse_args()
    args = vars(args_namespace)

    # check, count = check_ulimit_files()
    #
    # if(check):
    #     print('commented ulimit file successfully in total lines ',count)
    # else:
    #     print('Not commented ulimit in any file')

    workflow_name = args.get('workflow_name')

    stdout, stderr = _is_is_ACC_or_ACS()
    # if stderr:
    #     print(stderr)
        # exit(1)
    print(stdout)

    query_param = None
    if "Adobe Campaign Version" in stdout or "Adobe Campaign Standard" in stdout:
        query_param = "snamesinternalname"
    else:
        query_param = "sinternalname"

    stdout, stderr = check_for_failed_workflows(query_param, workflow_name)
    # if stderr:
    #     print(stderr)
    #     exit(1)
    print("stdout " + stdout)
    output = stdout.splitlines()
    if len(output):
        output = int(output[-3].strip().split('|')[0].strip())
        print('filtered istatus', output)
        if output != 1 and output != 5:
            data = """var a = ["""+workflow_name+""""]
            a.forEach(function(entry) {
                countWkf=sqlGetInt("Select count(*) from xtkworkflow where """ + query_param + """='" + entry + "' and ifailed=1")
                if (countWkf != 0){
                    xtk.workflow.Start(entry)
                }
            });"""

            create_file("/usr/local/neolane/start_workflow.js", data)
            os.chmod("/usr/local/neolane/start_workflow.js", 0o777)
            print("workflow file created")

            stdout, stderr = _get_instance_name()
            # if stderr:
            #     print(stderr)
            #     exit(1)
            instance_name = stdout.strip().strip("\n").strip("\t")

            stdout, stderr = run_workflow(instance_name)
            # if stderr:
            #     print(stderr)
            #     exit(1)
            print(stdout)

            stdout, stderr = check_for_failed_workflows(query_param, workflow_name)
            print(stdout)
            # if stderr:
            #     print(stderr)
            #     exit(1)
            print("stdout " + stdout)
            output = stdout.splitlines()
            if len(output):
                output = int(output[-3].strip().split('|')[0].strip())
                print('filtered istatus', output)
                if output != 1 and output != 5:
                    unconditional_data = """var a = ["""+workflow_name+"""]
                                    a.forEach(function(entry) {
                                        countWkf=sqlGetInt("Select count(*) from xtkworkflow where """ + query_param + """='" + entry + "' and ifailed=1")
                                        if (countWkf != 0){
                                            xtk.workflow.Kill(entry)
                                        }
                                    });"""
                    create_file("/usr/local/neolane/stop_workflow.js", unconditional_data)
                    os.chmod("/usr/local/neolane/stop_workflow.js", 0o777)
                    print("workflow file stop created")
                    stdout, stderr = uncoditional_stop(instance_name)
                    print(stdout)
                    # if stderr:
                    #     print(stderr)
                    #     exit(1)

                    stdout, stderr = check_for_failed_workflows(query_param, workflow_name)
                    print(stdout)
                    # if stderr:
                    #     print(stderr)
                    #     exit(1)
        else:
            print("Status 1")