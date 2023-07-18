"""
Python script to check not allowed ip addresses from
 host production, public access and adobe production
Requirements: boto3, json
Author: Shivakumar Bommakanti
Date: 15-07-2023
"""

import boto3
import json

def get_the_allowed_ips():
    allowed_ips = []
    f = open("security_json.json") #security json file path
    allowed_json = json.load(f)
    for network in allowed_json['networks']:
        allowed_ips.append(network['address'])

    return allowed_ips

def get_security_group_rules(client, group_id):
    paginator = client.get_paginator('describe_security_group_rules')
    response_page = paginator.paginate(Filters=[{
            'Name': 'group-id',
            'Values': [group_id]
        }])

    return response_page

def handle_security_group_rule(grp_name, grp_id, rules_page, allowed_ips, instance_id):
    result = []
    if grp_name == "public-web-access":
        for page in rules_page:
            for rule in page['SecurityGroupRules']:
                description = rule['Description']
                if len(description.strip()) == 0 or 'CPGNREQ' in description.upper() or 'SFTP' in description.upper():
                    print("malicious pwa")
                    malicious_dict = {"sg_name" : grp_name, "sg_id" : grp_id, "sq rule id" : rule['SecurityGroupRuleId'],
                                      "IpProtocol" : rule['IpProtocol'], "FromPort" : rule['FromPort'],
                                      "ToPort" : rule['ToPort'], "Ipv4" : rule['CidrIpv4'], "Ipv6" : rule['CidrIpv6']}

                result.append(malicious_dict)
                print("{},{}".format(instance_id, malicious_dict['desc']))

    else :
        for page in rules_page:
            for rule in page['SecurityGroupRules']:
                description = rule['Description']
                ip = rule['CidrIpv4']
                if ((len(description.strip()) == 0 or 'CPGNREQ' in description.upper() or \
                        'SFTP' in description.upper()) and ip not in allowed_ips):
                    print("malicious others")
                    malicious_dict = {"sg_name": grp_name, "sg_id": grp_id, "sq rule id": rule['SecurityGroupRuleId'],
                                      "IpProtocol": rule['IpProtocol'], "FromPort": rule['FromPort'],
                                      "ToPort": rule['ToPort'], "Ipv4": rule['CidrIpv4'], "Ipv6": rule['CidrIpv6']}

                result.append(malicious_dict)
                print("{},{}".format(instance_id, malicious_dict['desc']))

    return result




allowed_ips = get_the_allowed_ips()

check_groups = ['public-web-access', 'production']

session = boto3.Session()
available_regions = session.get_available_regions('ec2')
sno=1
for region in available_regions:
    ec2 = session.client('ec2', region_name=region)
    try:
        paginator = ec2.get_paginator('describe_instances').paginate()
        for page in paginator:
            for reservation in page['Reservations']:
                for instance in reservation['Instances']:
                    print("instance ID " + instance['InstanceId'])
                    for securityGroup in instance['SecurityGroups']:
                        sno += 1
                        security_group_name = securityGroup['GroupName']
                        print('sg name ', security_group_name)
                        security_group_id = securityGroup['GroupId']
                        instance_name = ''
                        if 'Tags' in instance:
                            for tag in instance['Tags']:
                                if tag['Key'] == 'Name':
                                    instance_name = tag['Value']
                                    check_groups.append(instance_name+'-production')

                        if security_group_name in check_groups:
                            response_page = get_security_group_rules(ec2 , security_group_id)

                            print("{},{},{},{},{}".format(sno, region, instance['InstanceId'], instance_name,
                                                          security_group_name))

                            malicious_output = handle_security_group_rule(security_group_name, security_group_id, response_page,
                                                                          allowed_ips, instance['InstanceId'])

    except Exception as e:
        print("client exception {}".format(e))
        continue