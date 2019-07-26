#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################
#:Date: 2018/2/13
#:Version: 1
#:Authors:
#    - Elma Huang <huanghuei0206@gmail.com>
#    - LSC <sclee@g.ncu.edu.tw>
#:Python_Version: 2.7
#:Platform: Unix
#:Description:
#   This is a class maintains OpenStack-Nova command operation in computing node
##############################################################


import ConfigParser
import logging
import time

from keystoneauth1 import session
from keystoneauth1.identity import v3
from novaclient import client


class NovaClient(object):
    _instance = None  # class reference
    _helper = None  # novaclient reference

    def __init__(self):
        self.config = ConfigParser.RawConfigParser()
        self.config.read('/home/localadmin/HASS/compute_node/hass_node.conf')
        if NovaClient._instance is not None:
            raise Exception("This class is a singleton! , cannot initialize twice")
        else:
            self.initialize_helper()
            NovaClient._instance = self

    @staticmethod
    def get_instance():
        """

        :return: 
        """
        if not NovaClient._instance:
            NovaClient()
        if not NovaClient._helper:
            NovaClient._instance.initialize_helper()
        return NovaClient._instance

    def initialize_helper(self):
        """

        """
        NovaClient._helper = self.get_helper()

    def get_helper(self):
        """

        :return: 
        """
        auth = v3.Password(auth_url = 'http://%s:%s/v3' %(self.config.get("keystone_auth","url"), self.config.get("keystone_auth","port")),
                           username = self.config.get("openstack", "openstack_admin_account"),
                           password = self.config.get("openstack", "openstack_admin_password"),
                           project_name = self.config.get("openstack", "openstack_project_name"),
                           user_domain_name = self.config.get("openstack", "openstack_user_domain_id"),
                           project_domain_name = self.config.get("openstack", "openstack_project_domain_id"))
        sess = session.Session(auth = auth)
        novaClient = client.Client(2.25, session = sess)
        return novaClient

    def get_vm(self, id):
        """

        :param id: 
        :return: 
        """
        return NovaClient._helper.servers.get(id)

    def get_all_instance_list(self):
        """

        :return: 
        """
        return NovaClient._helper.servers.list(search_opts = {'all_tenants': 1})

    def get_instance_list_by_node(self, node):
        ret = []
        instance_list = self.get_all_instance_list()
        for instance in instance_list:
            name = getattr(instance, "OS-EXT-SRV-ATTR:hypervisor_hostname")
            if name == node:
                ret.append(instance)
        return ret

    def get_vm_by_name(self, name):
        instance_list = self.get_all_instance_list()
        for instance in instance_list:
            if getattr(instance, "OS-EXT-SRV-ATTR:instance_name") == name:
                return instance
        return None

    def get_instance_state(self, instance_id):
        """

        :param instance_id: 
        :return: 
        """
        try:
            instance = self.get_vm(instance_id)
            return getattr(instance, "status")
        except Exception as e:
            return None

    def get_instance_host(self, instance_id, check_timeout=30):
        status = False
        while check_timeout > 0 and status != "ACTIVE":
            status = self.get_instance_state(instance_id)
            print status
            check_timeout -= 1
            time.sleep(1)
        time.sleep(2)
        return getattr(self.get_vm(instance_id), "OS-EXT-SRV-ATTR:host")


    def hard_reboot(self, id):
        """

        :param id: 
        """
        try:
            instance = self.get_vm(id)
            NovaClient._helper.servers.reboot(instance, reboot_type = 'HARD')
            logging.info("hard reboot success--vm id = %s" % id)
        except Exception as e:
            logging.error(str(e))

    def soft_reboot(self, id):
        """

        :param id: 
        """
        try:
            instance = self.get_vm(id)
            NovaClient._helper.servers.reboot(instance, reboot_type = 'SOFT')
            logging.info("soft reboot success--vm id = %s" % id)
        except Exception as e:
            logging.error(str(e))

    def get_instance_external_network(self, ip):
        """

        :param ip: 
        :return: 
        """
        ext_ip = self.config.get("openstack", "openstack_external_network_gateway_ip").split(".")
        ext_ip = ext_ip[0:-1]
        check_ip = ip.split(".")
        if all(x in check_ip for x in ext_ip):
            return ip
        return None

    def get_external_ip_from_instance(self, instance):
        for router_name, ip_list in instance.networks.iteritems():
            for ip in ip_list:
                if self.get_instance_external_network(ip) != None:
                    return ip
        return None




if __name__ == "__main__":
    pass
    # a = NovaClient.get_instance()
    # a.hard_reboot("21ffc94c-343e-4813-96b6-5d7d593a6449")
