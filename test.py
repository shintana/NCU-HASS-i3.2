#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################
#:Date: 2017/12/13
#:Version: 1
#:Authors:
#    - Elma Huang <huanghuei0206@gmail.com>
#    - LSC <sclee@g.ncu.edu.tw>
#:Python_Version: 2.7
#:Platform: Unix
#:Description:
#   This is a class maintains Openstack-Nova command operation
##############################################################

from keystoneauth1.identity import v3
from keystoneauth1 import session
from novaclient import client
import ConfigParser
import time
import logging

class NovaClient(object):
    _instance = None  # class reference
    _helper = None  # novaclient reference
    openstack_version = "queens"

    def __init__(self):
        if NovaClient._instance != None:
            raise Exception("This class is a singleton! , cannot initialize twice")
        else:
            self.initializeHelper()
            NovaClient._instance = self

    @staticmethod
    def getInstance():
        if not NovaClient._instance:
            NovaClient()
        if not NovaClient._helper:
            NovaClient._instance.initializeHelper()
        return NovaClient._instance

    def initializeHelper(self):
        NovaClient._helper = self.getHelper()

    def getHelper(self):
        auth = v3.Password(auth_url='http://192.168.4.12:5000/v3',
                           username='admin',
                           password='openstack123!',
                           project_name='Admin',
                           user_domain_name='default',
                           project_domain_name='Admin')
        sess = session.Session(auth=auth)
        if self.openstack_version == "mitaka":
            novaClient = client.Client(2.25, session=sess)
        else:
            novaClient = client.Client(2.29, session=sess, interface='Public')
        return novaClient

    def novaServiceUp(self, node):
        return NovaClient._helper.services.force_down('compute1', "nova-compute", False)

    def novaServiceDown(self, node):
        return NovaClient._helper.services.force_down('compute1', "nova-compute", True)

    def evacuate(self, instance, target_host, fail_node):
        self.novaServiceDown(fail_node)
        openstack_instance = self.getVM(instance.id)
        if self.openstack_version == "mitaka":
            NovaClient._helper.servers.evacuate(openstack_instance, target_host.name)
        else:
            NovaClient._helper.servers.evacuate(openstack_instance, target_host.name, force=True)
        self.novaServiceUp(fail_node)

def main():
	obj = NovaClient()
	obj.novaServiceDown('compute1')
    	print 'service down'

if __name__ == "__main__":
    main()
