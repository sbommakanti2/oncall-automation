#!/usr/bin/python3
"""
Python3 script for eliminating inmail issues
Requirements: subprocess, in_place, time, sys
Input: None
Author: Shivakumar Bommakanti
Date: 05-11-2023
"""
import subprocess
import argparse
from argparse import RawTextHelpFormatter
import logging

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

def get_db_name():
    """Gets the database name from predefined commands

    Returns:
        db name: string
    """
    dbname = ""
    stdout, stderr = run_commands(
        ["cat /usr/local/neolane/nl*/conf/config-*.xml | grep db | grep login | awk -F'login=\"' '{print $2}' | awk -F':' '{print $1}'"])
    if stderr:
        logger.exception("error in fetching dbname")
    else:
        dbname = stdout.replace('\n', '').replace('\t', '').replace(' ', '')

    return dbname

def count_idle_queries(days):
    dbname = get_db_name()
    sql_retrieve_command = "psql -d " + dbname + \
                           " -c \"select count(*) from pg_stat_activity where state = 'idle' and query_start < now() - INTERVAL '{} DAY';\" | awk 'NR==1 { print $1}'".format(days)
    logger.info(sql_retrieve_command)
    print(sql_retrieve_command)
    stdout, stderr = run_commands([sql_retrieve_command])
    if stderr:
        logger.exception("Error in counting idle queries older than 3 days", stderr)
        print("Error in counting idle queries older than 3 days", stderr)
        exit(1)
    else:
        print('Count of idle queries',stdout)
        logger.info('Count of idle queries', stdout)
    return stdout

def get_list_of_idle_PIDS(days):
    dbname = get_db_name()
    sql_retrieve_command = "psql -d " + dbname + \
                           " -c \"select pid, application_name,client_addr, datname, query_start, now()-query_start as hhmm_running, substring(query from 1 for 100) as truncatedquery," \
                           "wait_event,wait_event_type,state  from pg_stat_activity where ((state LIKE '%idle in transaction%') and query_start < now() - INTERVAL '{} DAY') order by hhmm_running DESC;" \
                           "\" | awk 'NR>1 { print $1}'".format(days)
    logger.info(sql_retrieve_command)
    print(sql_retrieve_command)
    stdout, stderr = run_commands([sql_retrieve_command])
    if stderr:
        logger.exception("Error in getting pids of idle queries older than 3 days", stderr)
        print("Error in getting pids of idle queries older than 3 days", stderr)
        exit(1)
    else:
        print('PIDs of idle queries', stdout)
        logger.info('PIDs of idle queries', stdout)
    return stdout.split('\n')

def cancel_query(pid):
    dbname = get_db_name()
    sql_retrieve_command = "psql -d " + dbname + \
                           " -c \"select pg_cancel_backend({});'".format(pid)
    logger.info(sql_retrieve_command)
    print("cancel",sql_retrieve_command)
    stdout, stderr = run_commands([sql_retrieve_command])
    if stderr:
        logger.exception("Error in cancelling query pid -"+pid+"with error "+stderr)
        print("Error in cancelling query pid -" + pid + "with error " + stderr)
    else:
        print('PIDs of idle queries', stdout)
        logger.info('PIDs of idle queries', stdout)
    return stdout.split('\n')

def terminate_query(pid):
    dbname = get_db_name()
    sql_retrieve_command = "psql -d " + dbname + \
                           " -c \"select pg_terminate_backend({});'".format(pid)
    logger.info(sql_retrieve_command)
    print("terminate", sql_retrieve_command)
    stdout, stderr = run_commands([sql_retrieve_command])
    if stderr:
        logger.exception("Error in terminating query pid -"+pid+"with error "+stderr)
        print("Error in terminating query pid -" + pid + "with error " + stderr)
    else:
        print('PIDs of idle queries', stdout)
        logger.info('PIDs of idle queries', stdout)
    return stdout.split('\n')

if __name__ == '__main__':
    try:
        global logger
        logger = logging.getLogger('Idle_queries')
    except Exception as e:
        raise e

    exe_process = """Please enter an optional argument :
                    days = No. of older days idle queries to kill Default 3
                    """
    parser = argparse.ArgumentParser(
        epilog=exe_process, formatter_class=RawTextHelpFormatter)
    parser.add_argument("-days", "--days_older", default='3', help="No. of days older")

    args_namespace = parser.parse_args()
    args = vars(args_namespace)

    days = args.get('days_older')

    count = count_idle_queries(days)
    if count > 0:
        pids = get_list_of_idle_PIDS(days)
        for pid in pids:
            cancel_query(pid)

        pids1 = get_list_of_idle_PIDS(days)
        print('Following pids didnt get cancelled will apply terminate')
        for pid1 in pids1:
            terminate_query(pid1)
        print('Successfully cancelled/terminated idle queries older than 3 days')
    else:
        print('No idle queries older than '+days+' days. exiting script')