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

    def __init__(self):
        self.config = ConfigParser.RawConfigParser()
        self.config.read('/home/localadmin/HASS/hass.conf')
        self.openstack_version = self.config.get("openstack_version", "version")
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
        auth = v3.Password(auth_url='http://%s:%s/v3' % (self.config.get("keystone_auth","url"), self.config.get("keystone_auth","port")),
                           username=self.config.get("openstack", "openstack_admin_account"),
                           password=self.config.get("openstack", "openstack_admin_password"),
                           project_name=self.config.get("openstack", "openstack_project_name"),
                           user_domain_name=self.config.get("openstack", "openstack_user_domain_id"),
                           project_domain_name=self.config.get("openstack", "openstack_project_domain_id"))
        sess = session.Session(auth=auth)
        if self.openstack_version == "mitaka":
            novaClient = client.Client(2.25, session=sess)
        else:
            novaClient = client.Client(2.29, session=sess)
        return novaClient

    def getComputePool(self):
        computePool = []
        hypervisorList = self._getHostList()
        for hypervisor in hypervisorList:
            computePool.append(str(hypervisor.hypervisor_hostname))
        return computePool

    def _getHostList(self):
        return NovaClient._helper.hypervisors.list()

    def getVM(self, id):
        return NovaClient._helper.servers.get(id)

    def getInstanceListByNode(self, node_name):
        ret = []
        instance_list = self.getAllInstanceList()
        for instance in instance_list:
            name = getattr(instance, "OS-EXT-SRV-ATTR:hypervisor_hostname")
            if name == node_name:
                ret.append(instance)
        return ret

    def getInstanceState(self, instance_id):
        instance = self.getVM(instance_id)
        return getattr(instance, "status")

    def getAllInstanceList(self):
        return NovaClient._helper.servers.list(search_opts={'all_tenants': 1})

    def getInstanceName(self, instance_id):
        instance = self.getVM(instance_id)
        return getattr(instance, "OS-EXT-SRV-ATTR:instance_name")

    def getInstanceHost(self, instance_id, check_timeout=120):
        status = None
        while status != "ACTIVE" and check_timeout > 0:
            instance = self.getVM(instance_id)
            status = self.getInstanceState(instance_id)
            if status == "SHUTOFF": break
            print "getInstanceHost in nova-client : %s , %s" % (status, getattr(instance, "name"))
            check_timeout -= 1
            time.sleep(1)
        if status != "ACTIVE" and status != "SHUTOFF":
            logging.error("NovaClient getInstanceHost fail,time out and state is not ACTIVE or SHUTOFF")
            print "NovaClient getInstanceHost fail,time out and state is not ACTIVE or SHUTOFF"
        return getattr(self.getVM(instance_id), "OS-EXT-SRV-ATTR:host")

    def getInstanceNetwork(self, instance_id):
        instance = self.getVM(instance_id)
        network = getattr(instance, "networks")
        return network

    def isInstanceExist(self, instance_id):
        try:
            NovaClient._helper.servers.get(instance_id)
        except:
            return False
        return True

    def isInstancePowerOn(self, id):
        vm = self.getVM(id)
        power_state = getattr(vm, "OS-EXT-STS:power_state")
        if power_state != 1:
            return False
        return True

    def getVolumes(self, id):
        return NovaClient._helper.volumes.get_server_volumes(id)

    def isInstanceBootFromVolume(self, id):
        volume = self.getVolumes(id)
        image = self.getImage(id)
        if volume == [] or image != '':
            return False
        return True

    def getImage(self, id):
        vm = self.getVM(id)
        return getattr(vm, "image")

    def novaServiceUp(self, node):
        return NovaClient._helper.services.force_down(node.name, "nova-compute", False)

    def novaServiceDown(self, node):
        return NovaClient._helper.services.force_down(node.name, "nova-compute", True)

    def liveMigrateVM(self, instance_id, target_host, check_timeout=60):
        instance = self.getVM(instance_id)
        instance.live_migrate(host=target_host)
        return self.getInstanceHost(instance_id)

    def evacuate(self, instance, target_host, fail_node):
        self.novaServiceDown(fail_node)
	print "service down"
        openstack_instance = self.getVM(instance.id)
        if self.openstack_version == "mitaka":
            NovaClient._helper.servers.evacuate(openstack_instance, target_host.name, force=True)
	    print "mitaka evacuate instance"
        else:
            NovaClient._helper.servers.evacuate(openstack_instance, target_host.name)
	    print "queens evacuate instance"
        self.novaServiceUp(fail_node)
	print "service up"


if __name__ == "__main__":
    a = NovaClient.getInstance()
