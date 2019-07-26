#########################################################
#:Date: 2018/2/13
#:Version: 1
#:Authors:
#    - Elma Huang <huanghuei0206@gmail.com>
#    - LSC <sclee@g.ncu.edu.tw>
#:Python_Version: 2.7
#:Platform: Unix
#:Description:
#   This is a static class which maintains all the ha virtual machine data structure.
##########################################################


from __future__ import print_function

import logging
import subprocess

from Instance import Instance
from RESTClient import RESTClient


class HAInstance(object):
    server = RESTClient.getInstance()
    ha_instance_list = None
    instance_list = None
    host = subprocess.check_output(['hostname']).strip()

    @staticmethod
    def init():
        HAInstance.instance_list = []
        HAInstance.ha_instance_list = {}

    @staticmethod
    def get_instance_from_controller():
        try:
            cluster_list = HAInstance.server.list_cluster()["data"]
            print (cluster_list)
            for cluster in cluster_list:
                cluster_uuid = cluster["cluster_id"]
                HAInstance.ha_instance_list[cluster_uuid] = HAInstance._get_ha_instance(cluster_uuid)
            host_instance = HAInstance._get_instance_by_node(HAInstance.ha_instance_list)
            for cluster_id, instance_list in host_instance.iteritems():
                for instance in instance_list:
                    HAInstance.add_instance(cluster_id, instance)
        except Exception as e:
            message = "HAInstance get_instance_from_controller Except:" + str(e)
            logging.error(message)
            print(message)

    @staticmethod
    def _get_ha_instance(cluster_id):
        instance_list = []
        try:
            instance_list = HAInstance.server.list_instance(cluster_id)["data"]["instanceList"]
        except Exception as e:
            message = "_get_ha_instance--get instance list from controller(rpc server) fail" + str(e)
            # instance_list = []
            logging.error(message)
        finally:
            return instance_list

    @staticmethod
    def _get_instance_by_node(instance_lists):
        for id, instance_list in instance_lists.iteritems():
            for instance in instance_list[:]:
                if HAInstance.host not in instance["host"]:
                    instance_list.remove(instance)
        return instance_lists

    @staticmethod
    def add_instance(cluster_id, instance):
        """

        :param cluster_id:
        :param instance:
        """
        print("add vm")
        vm = Instance(cluster_id = cluster_id, ha_instance = instance)
        HAInstance.instance_list.append(vm)

    @staticmethod
    def get_instance_list():
        """

        :return:
        """
        return HAInstance.instance_list

    @staticmethod
    def get_instance(name):
        """

        :param name:
        :return:
        """
        for instance in HAInstance.instance_list:
            if instance.name == name:
                return instance
        return None

    @staticmethod
    def is_HA_instance(name):
        for instance in HAInstance.instance_list:
            if instance.name == name:
                return True
        return False

    @staticmethod
    def get_detection_list():
        detection_list = []
        try:
            cluster_list = HAInstance.server.list_cluster()["data"]
            for cluster in cluster_list:
                cluster_uuid = cluster["cluster_id"]
                detection_list = HAInstance.server.list_node(cluster_uuid)["data"]["nodeList"][1]["detection_list"]
        except Exception as e:
            message = "_get_ha_detection--get detection list from controller(rpc server) fail" + str(e)
            logging.error(message)
        finally:
            detection_list.sort()
            if detection_list == []:
                detection_list = ['5', '6', '7']
            print(detection_list)
            return detection_list


    @staticmethod
    def update_ha_instance():
        HAInstance.init()
        HAInstance.get_instance_from_controller()
        print("update HA Instance finish")