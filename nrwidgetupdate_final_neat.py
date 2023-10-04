# /usr/bin/python3
"""
Author:         Shivakumar Bommakanti
Date:           13-March-2023
Description:    This script is helpful for creating new dashboards and/or
                updating existing dashboards by taking user input data

Input:          There are few inputs a user has to pass below

                Please enter an action(1/2/3/4):
                1. Create a new dashboard from brp template
                2. Update a dashboard with latest changes from brp
                3. Update a tab with latest brp template
                4. Update widget

                if user chooses 1
                1A. Please enter customer name (eg: Siriusxm Radio Inc.):
                1B. Please enter tenant id (eg: siriusxmradioinc):

                if user chooses 2
                2A. Please enter customer name (eg: Siriusxm Radio Inc.):
                2B. Please enter tenant id (eg: siriusxmradioinc):
                2C. Please enter dashboard name (eg: Siriusxm Radio Inc. - ACMS Dashboard):

                if user chooses 3
                3A. Please enter dashboard name (eg: Siriusxm Radio Inc. - ACMS Dashboard):
                3B. Please enter existing tab name (eg: Siriusxm Radio Inc. - Process Monitor):
                3C. Please enter desired tab name (eg: Siriusxm Radio Inc. - Process Monitor234):

                if user chooses 4
                4A. Please enter dashboard name (eg: Siriusxm Radio Inc. - ACMS Dashboard):
                4B. Please enter tab name (eg: Siriusxm Radio Inc. - Process Monitor):
                4C. Please enter existing widget name (eg: Siriusxm Radio Inc. - Missing Critical Processes):
                4D. Please enter desired widget name (eg: Siriusxm Radio Inc. - Memory):

Output:         Creating/updating dashboard data

Versions:
10-March-2023 -> Script initial creation
04-Oct-2023 -> Update script to perform action referring its own template
"""
# -*- coding: future_fstrings -*-
import requests
import json
import re
from copy import deepcopy
import argparse
import sys
from argparse import RawTextHelpFormatter

# key = "NRAK-NVRU3HTPPBY8RUWDYFCX2PH598W"
key = "NRAK-DATZR69AHO4WU1609UG4HIDHOVR"
url = "https://api.newrelic.com/graphql"
headers = {'Content-Type': 'application/json', 'API-Key': key}


def get_brp_dashboard():
    """Getting brp dashboard json

    Raises:
        Exception: Exception

    Returns:
        dict: dictionary
    """
    print("getting brp dashboard")
    query = {
        'query': '{\n  actor {\n    entity(guid: "MTIwOTMyN3xWSVp8REFTSEJPQVJEfGRhOjc1ODkwOQ") {\n      ... on DashboardEntity {\n        name\n        permissions\n        pages {\n          name\n          widgets {\n            visualization {\n              id\n            }\n            title\n            layout {\n              row\n              width\n              height\n              column\n            }\n            rawConfiguration\n          }\n        }\n      }\n    }\n  }\n}\n',
        'variables': ''
    }
    brpjson = requests.post(url, headers=headers, json=query)

    if brpjson.status_code == 200:
        print(brpjson.status_code, "- Success")
        brpdashboardjson = brpjson.json()
    else:
        raise Exception("Unable to fetch brp dashboard, Nerdgraph query failed with a {}.".format(
            {brpjson.status_code}))

    return brpdashboardjson

def get_dashboard(reqguid):
    """Getting dynamic dashboard json

       Raises:
           Exception: Exception

       Returns:
           dict: dictionary
       """
    print("getting dynamic dashboard")
    finalquery1 = '{\n  actor {\n    entity(guid: "'
    finalquery2 = '") {\n      ... on DashboardEntity {\n        name\n        permissions\n        pages {\n          name\n          widgets {\n            visualization {\n              id\n            }\n            title\n            layout {\n              row\n              width\n              height\n              column\n            }\n            rawConfiguration\n          }\n        }\n      }\n    }\n  }\n}\n'
    finalquery = {
        'query': finalquery1+reqguid+finalquery2,
        'variables': ''
    }
    json = requests.post(url, headers=headers, json=finalquery)

    if json.status_code == 200:
        print(json.status_code, "- Success")
        dashboardjson = json.json()
    else:
        raise Exception(
            "Unable to fetch brp dashboard, Nerdgraph query failed with a {}.".format({json.status_code}))

    return dashboardjson

def update_brp_with_provided_details(brp_dashboard_template, customer_name, tenant_id):
    print("replacing the details")
    return brp_dashboard_template.replace("brp", tenant_id).replace("Bombardier (BRP)", customer_name).replace("BRP", customer_name)


def run_query(query, customer_name):
    print("run query called")
    r = requests.post(url, headers=headers, data=json.dumps(query))
    if r.status_code == 200:
        print(r.status_code, "- Success")
        print(r.json())
        json_response = json.dumps(r.json(), indent=2)
        grab_re_guid = re.search(r"M[A-Za-z0-9]+", json_response)
        guid_id = grab_re_guid.group()
        customer_name_spaces_spaced = customer_name.replace(" ", "%20").lower()
        dashboard_url = "https://one.newrelic.com/dashboards/detail/{}?account=1209327&filters=%28name%20LIKE%20%27{}%27%20OR%20id%20%3D%20%27{}%27%20OR%20domainId%20%3D%20%27{}%27%29&state=edca9851-d3e7-a231-cae0-2e8233adc72d".format(
            guid_id, customer_name_spaces_spaced, customer_name_spaces_spaced, customer_name_spaces_spaced)
        print(
            "Dashboard for {} has been successfully created, click the link below to view the dashboard\n{}".format(
                customer_name, dashboard_url)
        )
    else:
        # raise an error with a HTTP response code
        print("json output {}".format(r.json()))
        raise Exception(
            "Unable to create dashboard, Nerdgraph query failed with a {}".format(r.status_code))


def create_new_dashboard_from_brp(args):
    customer_name = args.get("customer_name", "")
    tenant_id = args.get("tenant_id", "")

    if not customer_name and not tenant_id:
        print("customer name or tenant id is missing")
        exit(1)

    brp_dashboard_json = get_brp_dashboard()
    updated_dashboard_json = update_brp_with_provided_details(
        json.dumps(brp_dashboard_json), customer_name, tenant_id)

    jsonvariables = json.loads(updated_dashboard_json)['data']['actor']
    jsonvariables['dashboard'] = jsonvariables.pop('entity')
    query = {
        'query': 'mutation create($dashboard: DashboardInput!) {\n  dashboardCreate(accountId: 1209327, dashboard: $dashboard) {\n    entityResult {\n      guid\n      name\n    }\n    errors {\n      description\n    }\n  }\n}\n',
        'variables': jsonvariables
    }
    run_query(query, customer_name)


def get_req_dashboard_guid(req_dashboard, nextCursor="null"):
    # Function that retrieves all dashboards and get required guid
    print("calling guid")
    guid = ""
    if nextCursor != "null":
        nextCursor = '"{}"'.format(nextCursor)
    query = """{
  actor {
    entitySearch(queryBuilder: {type: DASHBOARD, tags: {key: "isDashboardPage", value: "false"}}) {
      results(cursor: cursor_string) {
        entities {
          ... on DashboardEntityOutline {
            guid
            name
          }
        }
        nextCursor
      }
    }
  }
}
            """.replace("cursor_string", nextCursor)
    json_data = {
        'query': query,
        'variables': ''}
    req_json = requests.post(url, headers=headers, json=json_data)

    if req_json.status_code == 200:
        print(req_json.status_code, "- Success")
        reqdashboardjson = req_json.json()
    else:
        print("error in fetching guids")

    jsonvariables = reqdashboardjson['data']['actor']['entitySearch']['results']['entities']
    nextCursor = reqdashboardjson['data']['actor']['entitySearch']['results'].get(
        "nextCursor", "")
    for entry in jsonvariables:
        if entry["name"] == req_dashboard:
            guid = entry["guid"]
            return guid

    if not guid:
        if nextCursor:
            guid = get_req_dashboard_guid(req_dashboard, nextCursor=nextCursor)
        else:
            print("no guid found for dashbboard {}".format(req_dashboard))

    return guid


def update_dashboard(args):
    print("update dashboard called")
    customer_name = args.get("customer_name", "")
    tenant_id = args.get("tenant_id", "")
    dashboard_name = args.get("dashboard_name", "")

    if not customer_name and not tenant_id:
        print("customer name or tenant id is missing")
        exit(1)

    if dashboard_name:
        req_guid = get_req_dashboard_guid(dashboard_name)
        dashboard_json = get_dashboard(req_guid)
    else:
        dashboard_json = get_brp_dashboard()

    updated_dashboard_json = update_brp_with_provided_details(
        json.dumps(dashboard_json), customer_name, tenant_id)
    jsonvariables = json.loads(updated_dashboard_json)['data']['actor']
    entity = jsonvariables.pop('entity')
    jsonvariables['dashboard'] = entity

    if args.get("tab_name", {}) and args.get("desired_tab_name", {}):
        jsonvariables = update_tab_info(args["tab_name"], args["desired_tab_name"], jsonvariables,
                                        args["dashboard_name"])

    if args.get("widget_name", {}):
        jsonvariables = update_widget_info(args["tab_name"], args["widget_name"],
                            args["desired_widget_name"], jsonvariables, args["dashboard_name"])

    req_guid = get_req_dashboard_guid(args.get("dashboard_name"))

    finaljsonobject1 = 'mutation update($dashboard: DashboardInput!) {\n  dashboardUpdate(dashboard: $dashboard, guid: "'
    finaljsonobject2 = '") {\n    entityResult {\n      guid\n      name\n    }\n    errors {\n      description\n    }\n  }\n}\n'
    finaljsonquery = finaljsonobject1+req_guid+finaljsonobject2
    finaljsonobject = {'query': finaljsonquery, 'variables': jsonvariables}
    run_query(finaljsonobject, customer_name)

def update_tab_info(tab_name, desired_tab_name, jsonvariables, dashboard_name):
    new_page, pages, flag, index = find_required_object(jsonvariables, tab_name)
    if not flag:
        print('came to else')
        req_guid = get_req_dashboard_guid(dashboard_name)
        print(req_guid)
        dashboard_json = get_dashboard(req_guid)
        jsonvariables = json.loads(json.dumps(dashboard_json))['data']['actor']
        entity = jsonvariables.pop('entity')
        jsonvariables['dashboard'] = entity
        new_page, pages, flag, index = find_required_object(jsonvariables, tab_name)
        if not flag:
            print("no page found with this name {}".format(tab_name))
            exit(1)

    new_page["name"] = desired_tab_name
    pages[index] = new_page
    jsonvariables['dashboard']['pages'] = pages

    return jsonvariables

def find_required_object(jsonvariables, need_object_name, option = 0):
    print(option)
    if option:
        objects = jsonvariables
    else:
        objects = jsonvariables['dashboard']['pages']
    new_object = {}
    flag = False
    for i in range(len(objects)):
        object = objects[i]
        if option:
            key = 'title'
        else:
            key = 'name'
        if object[key] == need_object_name:
            new_object = deepcopy(object)
            objects[i] = {}
            flag = True
            break
    return objects, new_object, flag, i

def update_widget_info(tab_name, widget_name, desired_widget_name, jsonvariables,dashboard_name):
    tabs, new_tab, flag, index = find_required_object(jsonvariables, tab_name)
    if not flag:
        print('came to else other tab name than brp')
        req_guid = get_req_dashboard_guid(dashboard_name)
        print(req_guid)
        dashboard_json = get_dashboard(req_guid)
        jsonvariables = json.loads(json.dumps(dashboard_json))['data']['actor']
        entity = jsonvariables.pop('entity')
        jsonvariables['dashboard'] = entity
        tabs, new_tab, flag, index = find_required_object(jsonvariables, tab_name)
        if not flag:
            print("no tab found with this name {}".format(tab_name))
            exit(1)

    widgets, new_widget, flag, index1 = find_required_object(new_tab['widgets'], widget_name, 1)
    if not flag:
        print('came to else other widget than brp 1')
        req_guid = get_req_dashboard_guid(dashboard_name)
        print(req_guid)
        dashboard_json = get_dashboard(req_guid)
        jsonvariables = json.loads(json.dumps(dashboard_json))['data']['actor']
        entity = jsonvariables.pop('entity')
        jsonvariables['dashboard'] = entity
        tabs, new_tab, flag, index = find_required_object(jsonvariables, tab_name)
        if not flag:
            print("no tab found with this name {}".format(tab_name))
            exit(1)

        print('came to else other widget than brp 2')
        widgets, new_widget, flag, index1 = find_required_object(new_tab['widgets'], widget_name, 1)
        if not flag:
            print("no widget found with this name {}".format(widget_name))
            exit(1)

    new_widget["title"] = desired_widget_name
    widgets[index1] = new_widget
    new_tab["widgets"] = widgets
    tabs[index] = new_tab
    jsonvariables['dashboard']['pages'] = tabs

    return jsonvariables

def main():
    exe_process = """Please enter an action(1/2/3/4):
                1. Create a new dashboard from brp template
                2. Update a dashboard with latest changes from brp
                3. Update a tab name
                4. Update widget name

                Required Arguments for each step:
                Action 1 - customer_name, tenant_id
                Action 2 - customer_name, tenant_id, dashboard_name
                Action 3 - customer_name, tenant_id, dashboard_name, tab_name, desired_tab_name
                Action 4 - customer_name, tenant_id, dashboard_name, tab_name, widget_name, desired_widget_name
                """
    parser = argparse.ArgumentParser(
        epilog=exe_process, formatter_class=RawTextHelpFormatter)
    required_parser = parser.add_argument_group('required arguments')
    action = "4"
    required_parser.add_argument(
        "-cn", "--customer_name", help="Customer name")
    required_parser.add_argument("-ti", "--tenant_id", help="Tenant ID")
    parser.add_argument("-dn", "--dashboard_name", help="Dashboard name")
    parser.add_argument("-t", "--tab_name", help="Tab name")
    parser.add_argument("-w", "--widget_name", help="Widget name")
    parser.add_argument("-dw", "--desired_widget_name",
                        help="Desired Widget name")

    args_namespace = parser.parse_args()
    args = vars(args_namespace)

    actions = {
        "1": create_new_dashboard_from_brp,
        "2": update_dashboard,
        "3": update_dashboard,
        "4": update_dashboard
    }
    # action = args.get("action")
    if action in ["1", "2", "3", "4"]:
        return actions[action](args)
    else:
        print("action not supported")
        exit(1)


if __name__ == "__main__":
    main()