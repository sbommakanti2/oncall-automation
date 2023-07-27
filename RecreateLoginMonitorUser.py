"""
Python script to check not allowed ip addresses from
 host production, public access and adobe production
Requirements: subprocess, fileinput
Author: Shivakumar Bommakanti
Date: 25-07-2023
"""
import subprocess
import fileinput

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

def is_ACC_or_ACS():
    commands = ["/usr/bin/sudo -u neolane bash -c '. /usr/local/neolane/nl*/env.sh ; nlserver pdump -full web'"]
    stdout, stderr = run_commands(commands)
    if stderr:
        print(stderr)
        exit(1)
    return stdout

def check_apache_status():
    commands = ["cd /var/db/newrelic-infra/custom-integrations; /etc/init.d/apache2 status"]
    stdout, stderr = run_commands(commands)
    if stderr:
        print(stderr)
        exit(1)
    print('check apache ', stdout)

    for line in stdout.split("\n"):
        if line.strip():
            if "Active:" in line:
                line = line.lstrip()
                if len(line.split()) > 1 \
                        and "running" in line.split()[1]:
                    return True
                else:
                    return False


def check_web_status():
    commands = ["/usr/bin/sudo -u neolane bash -c '. /usr/local/neolane/nl*/env.sh ; nlserver pdump'"]
    stdout, stderr = run_commands(commands)
    if stderr:
        print(stderr)
        exit(1)
    print('check web ', stdout)

    for line in stdout.split("\n"):
        if line.strip():
            if "web@" in line:
                return True
            else:
                return False

def restart_apache():
    commands = ["cd /var/db/newrelic-infra/custom-integrations; /etc/init.d/apache2 restart"]
    stdout, stderr = run_commands(commands)
    if stderr:
        print(stderr)
        exit(1)
    print('restart apache ', stdout)

def restart_web():
    commands = ["/usr/bin/sudo -u neolane bash -c '. /usr/local/neolane/nl*/env.sh ; nlserver restart web'"]
    stdout, stderr = run_commands(commands)
    if stderr:
        print(stderr)
        exit(1)
    print('restart web ', stdout)

def restart_nr():
    commands = ["/usr/bin/sudo systemctl restart newrelic-infra.service"]
    stdout, stderr = run_commands(commands)
    if stderr:
        print(stderr)
        exit(1)
    print('restart web ', stdout)

def checkBinary_healthy(type):
    proceed  = True
    commands = ["cd /var/db/newrelic-infra/custom-integrations; /etc/newrelic-infra/custom-integrations/bin/campaign-loginmonitor {}"
                .format(type)]
    stdout, stderr = run_commands(commands)
    if stderr:
        print(stderr)
        exit(1)
    print('Binary check '+stdout)
    if len(stdout.strip()) == 0:
        print('ERROR New Relic binary not found, Please check with hyperion team on this.')
        exit(1)
    #Checking for result pass of event xtklayermonitor sample
    for k, v in stdout.items():
        print('key-', k, 'value-', v)
        if "metrics" == k:
            for ind in range(0, len(v)):
                if "XtklayerMonitorSample" in v[ind]:
                    for k1, v1 in v[ind].items():
                        if "result" == k1 and "PASS" == v1:
                            proceed = False

    return proceed

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

def checkInDB(db_table):

    dbname = get_db_name()
    sql_retrieve_command = "psql -d " + dbname + \
                           " -c \"select sname,idisable,tslastmodified from {} where sname=''campaign-loginmonitor';\"".format(db_table)
    print(sql_retrieve_command)
    stdout, stderr = run_commands([sql_retrieve_command])
    print(stderr)

    for line in stdout.split("\n"):
        line = line.strip()
        if line:
            parts = line.split('|')
            if "idisable" in parts[0]:
                return parts[1].strip()

    return stdout, stderr

def updateInDB(db_table):
    dbname = get_db_name()
    sql_retrieve_command = "psql -d " + dbname + \
                           " -c \"update {} r set idisable=0 where sname='campaign-loginmonitor';\"".format(
                               db_table)
    print(sql_retrieve_command)
    stdout, stderr = run_commands([sql_retrieve_command])
    print(stderr)
    print(stdout)

def set_neolane_env():
    commands = ['source /usr/local/neolane/nl*/env.sh']
    stdout, stderr = run_commands(commands)
    if stderr:
        print(stderr)
        exit(1)
    return stdout

def _get_instance_name():
    commands = ["ls /usr/local/neolane/nl*/conf/config*xml | grep -v default |cut -d. -f1 |cut -d'-' -f2"]
    stdout, stderr = run_commands(commands)
    if stderr:
        print(stderr)
        exit(1)
    return stdout

def update_folder_settings(instance_id):
    print("here is the instance id")
    print(instance_id)
    run_workflow_command = "nlserver javascript -instance:{} -file " \
                           "/etc/newrelic-infra/custom-integrations/loginmonitor/update_folder_settings.js"\
                            .format(instance_id)
    commands = [run_workflow_command]
    stdout, stderr = run_commands(commands)
    if stderr:
        print(stderr)
        exit(1)
    return stdout

def create_credentials(instance_id, pwd):
    print("here is the instance id")
    print(instance_id)
    run_workflow_command = "/usr/local/neolane/nlserver javascript -instance:{} -file " \
                           "/etc/newrelic-infra/custom-integrations/loginmonitor/create_credentials.js -arg:{}}'"\
                            .format(instance_id,pwd)
    commands = [run_workflow_command]
    stdout, stderr = run_commands(commands)
    if stderr:
        print(stderr)
        exit(1)
    return stdout

def update_file(file_path, pwd):
    with fileinput.FileInput(file_path, inplace=True) as f:
        for line in f:
            if 'password:' in line:
                print('password: {}\n'.format(pwd), end='')
            else:
                print(line, end='')
    #os.chown(file_path, neolane_uid, neolane_gid)
    return

if __name__ == '__main__':

    stdout = is_ACC_or_ACS()
    print('type '+stdout)

    if "Adobe Campaign Classic" in stdout:
        proceed = checkBinary_healthy('acc')
        db_table = 'xtkoperator'
    else:
        proceed = checkBinary_healthy('acs')
        db_table = 'xtkuser'

    #If binary found and not healty status then check apache and web
    if proceed:
        status_good = check_apache_status()
        if not status_good:
            restart_apache()

        web_status = check_web_status()
        if not web_status:
            restart_web()

    isDisabled = checkInDB(db_table)
    if isDisabled:
        updateInDB(db_table)
        isDisabled = checkInDB(db_table)
        print('After update ', isDisabled)
        restart_nr()
        restart_apache()
        restart_web()
    else:
        process = subprocess.Popen(['openssl', 'rand', '-base64', '15'], universal_newlines=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pwd, stderr = process.communicate()

        print("password created", pwd)

        stdout, stderr = set_neolane_env()
        print("Neolane env set", stdout)

        stdout= _get_instance_name()

        instance_name = stdout.strip().strip("\n").strip("\t")
        print("instance name", instance_name)

        stdout= update_folder_settings(instance_name)
        print('Update folder settings', stdout)

        stdout= create_credentials(instance_name, pwd)
        print('create credentials', stdout)
        update_file("/var/db/newrelic-infra/custom-integrations/.loginmonitor.yml", pwd)

        print('Last action restarting nr and web')
        restart_nr()
        restart_web()

