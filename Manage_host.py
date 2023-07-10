"""
Python wrapper to Manage hosts value in etc/hosts
Requirements: subprocess,os
Input: Host name
Author: Shivakumar Bommakanti
Date: 22-06-2023
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

def search_file_return_value(file_name, search_string, delimiter):
    """
    Searches in given file_name for given search_string and if found splits with delimiter
    Returns:
        Value:string
    """
    result = None
    file = open(file_name, "r")
    data = file.readlines()
    for line in data:
        if search_string in line:
            parts = line.split(delimiter) #splitting by delimiter
            print('parts-->', parts)
            for ind in range(len(parts)-1):
                if search_string in parts[ind]:
                    result = parts[ind+1]
                    print('value -->', result)

    file.close()
    return result

def change_content_in_files(filename, find_text, replace_text, flag=0):
    """
    Updates given filename searching for find_text and update replace_text.
    """
    with fileinput.FileInput(filename, inplace=True) as f1:
        for line in f1:
            if flag == 1:
                if line.startswith(find_text):
                    print(replace_text, end='\n')
                else:
                    print(line, end='')
            else:
                if find_text in line:
                    print(line.replace(find_text,
                                       replace_text), end='')
                else:
                    print(line, end='')

def retrieve_spare_servers():
    """
    Retrieves all the spare servers for the logged in host
    returns : list of all spare servers
    """

    stdout, stderr = run_commands(['grep spareS /usr/local/neolane/nl*/conf/serverConf.xml'])

    spare_servers = []
    if stderr:
        print("error in fetching spare servers")
    else:
        lines = stdout.splitlines()
        for line in lines:
            data = stdout.split('url=')
            if len(data) == 2:
                server = data[1].replace('"', '').replace('http://', '').replace('/>', '')
                spare_servers.append(server)

    print('spare servers -->', spare_servers)
    return spare_servers

def get_private_IP(spare_servers):
    """
    Retrieves private IP for given servers using aws
    returns : Dict of spare server and its private IP
    """

    servers_IP = {}
    region = ''
    for server in spare_servers:
        stdout, stderr = run_commands(['nslookup {}'.format(server)])
        if stderr:
            print("error while running nslookup for spare server", server)
        else:
            lines = stdout.splitlines()
            lines = [line for line in lines if line] #To remove empty strings
            address = lines[-1].split(':')[1].strip()
            stdout1, stderr1 = run_commands(['nslookup {}'.format(address)])
            if stderr1:
                print("error while running nslookup for address", address)
            else:
                lines = stdout1.splitlines()
                lines = [line for line in lines if line]  # To remove empty strings
                for line in lines:
                    if 'name =' in line:
                        data = line.split('name =')[1].strip()
                        region = data.split('.')[1]
                        break

            if region:
                stdout2, stderr2 = run_commands(['aws ec2 describe-instances --filters "Name=tag:Name,Values=cerebro-stage1-1" '
                                             '--query "Reservations[].Instances[].PrivateIpAddress" '
                                             '--region {} --output text'.format(region)])
                if stderr2:
                    print("error while running aws query for region", region)
                else:
                    private_ip = stdout2.strip()
                    servers_IP[server] = private_ip
            else:
                print('Issue in retrieving region for server', server)

    return servers_IP

def update_file_using_dict(filename, servers_IP_dict):
    """
    Updates given file with data in dictionary
    """

    file = open(filename, 'a')
    file.write('\n') #added a new line

    servers = servers_IP_dict.keys()
    for server in servers:
        line = servers_IP_dict[server]+' '+server+' '+server.split('.')[0]+'\n'
        print(line)
        file.write(line)

    print('Updated servers with ip in ',filename)


if __name__ == '__main__':

    #verifying manage_etc_hosts value
    value = search_file_return_value('/etc/cloud/cloud.cfg.d/01_debian_cloud.cfg', 'manage_etc_hosts', '=')
    if value != None and value == 'true':
        print('manage host value found is', value, 'performing required steps')

        spare_servers = retrieve_spare_servers()
        servers_privateIP = get_private_IP(spare_servers)

        change_content_in_files('/etc/cloud/cloud.cfg.d/01_debian_cloud.cfg', 'manage_etc_hosts=true',
                                'manage_etc_hosts=false')

        update_file_using_dict('/etc/hosts', servers_privateIP)
        print('Activity completed successfully')
    else:
        print('manage host value is', value,'no update required')
