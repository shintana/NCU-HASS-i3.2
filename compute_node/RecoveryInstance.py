#########################################################
#:Date: 2018/2/12
#:Version: 1
#:Authors:
#    - Elma Huang <huanghuei0206@gmail.com>
#    - LSC <sclee@g.ncu.edu.tw>
#:Python_Version: 2.7
#:Platform: Unix
#:Description:
#   This is a class maintains recovery methods.
##########################################################


from __future__ import print_function

import logging
import subprocess

from enum import Enum

from HAInstance import HAInstance
from NovaClient import NovaClient
from RESTClient import RESTClient

import time

class Failure(Enum):
    OS_CRASH = "Crash"
    OS_HANGED = "Watchdog"
    MIGRATED = "Migration"
    DELETED = "Delete"
    NETWORK_ISOLATION = "Network"


class RecoveryInstance(object):
    def __init__(self):
        self.nova_client = NovaClient.get_instance()
        self.server = RESTClient.getInstance()
        self.vm_name = None
        self.failed_info = None
        self.recovery_type = ""

    def recover_instance(self, fail_vm):
        """

        :param fail_vm: 
        :return: 
        """
        # fail_vm = ['instance-00000344', 'Failed',State]
        self.vm_name = fail_vm[0]
        self.failed_info = fail_vm[1]
        self.recovery_type = fail_vm[2]
        HAInstance.update_ha_instance()
        if not HAInstance.is_HA_instance(self.vm_name):
            print ("Not a HA instance %s, dont need recovery process." % self.vm_name)
            return None
        result = False
        print("start recover:" + self.recovery_type)
        # print Failure.DELETED.value
        if self.recovery_type in Failure.OS_CRASH.value or self.recovery_type in Failure.OS_HANGED.value:
            result = self.hard_reboot_instance(self.vm_name)
        elif self.recovery_type in Failure.MIGRATED.value:
            result = self.recover_migration(self.vm_name)
        elif self.recovery_type in Failure.DELETED.value:
            result = self.recover_delete(self.vm_name)
        elif self.recovery_type in Failure.NETWORK_ISOLATION.value:
            if self.hard_reboot_instance(self.vm_name):
                print("hard reboot successfully")
                result = self.check_network_state(self.failed_info)
                if result:
                    message = "ping vm successfully"
                    print(message)
                    logging.info(message)
                else:
                    message = "ping vm fail"
                    print(message)
                    logging.error(message)
        print("recover %s finish" % self.recovery_type)
        # print result
        return result

    def hard_reboot_instance(self, fail_instance_name):
        """

        :param fail_instance_name: 
        :return: 
        """
        instance = self.get_ha_instance(fail_instance_name)
        self.nova_client.hard_reboot(instance.id)
        return self.check_recover_state(instance.id)

    def soft_reboot_instance(self, fail_instance_name):
        """

        :param fail_instance_name: 
        :return: 
        """
        instance = self.get_ha_instance(fail_instance_name)
        self.nova_client.soft_reboot(instance.id)
        return self.check_recover_state(instance.id)

    def recover_migration(self, fail_instance_name):
        """

        :return: 
        """
        try:
            instance = self.get_ha_instance(fail_instance_name)
            target_host = self.nova_client.get_instance_host(instance.id)
            print (target_host)
            cluster_list = self.server.list_cluster()["data"]
            for cluster in cluster_list:
                if cluster["cluster_id"] == instance.cluster_id:
                    node_list = self.server.list_node(cluster["cluster_id"])["data"]["nodeList"]
                    for node in node_list:
                        if target_host in node["node_name"]:
                            print ("recover %s by update controller's data" % fail_instance_name)
                            self.server.update_all_cluster()
                            return True
            print ("recover %s by delete instance" % fail_instance_name)
            result = self.server.delete_instance(instance.cluster_id, instance.id)
            if result["code"] == "succeed":
                return True
            return False
        except Exception as e:
            print ("RecoveryInstance recover_migration--except:" + str(e))
            logging.error("RecoveryInstance recover_migration--except:" + str(e))
            return False

    def recover_delete(self, fail_instance_name):
        try:
            instance = self.get_ha_instance(fail_instance_name)
            print ("instance %s is deleted, delete controller's instance data" % fail_instance_name)
            result = self.server.delete_instance(instance.cluster_id, instance.id)
            if result["code"] == "succeed":
                return True
            return False
        except Exception as e:
            print ("RecoveryInstance recover_delete--except:" + str(e))
            logging.error("RecoveryInstance recover_delete--except:" + str(e))
            return False


    def check_network_state(self, ip, time_out = 30):
        """

        :param ip: 
        :param time_out: 
        :return: 
        """
        # check network state is up
        while time_out > 0:
            try:
                response = subprocess.check_output(['timeout', '2', 'ping', '-c', '1', ip],
                                                   stderr = subprocess.STDOUT,
                                                   universal_newlines = True)
                logging.info("recover network isolation success")
                return True
            except subprocess.CalledProcessError:
                time_out -= 1
                time.sleep(1)
        logging.error("recover vm network isolation fail")
        return False

    def get_ha_instance(self, name):
        """

        :param name: 
        :return: 
        """
        return HAInstance.get_instance(name)

    def check_recover_state(self, id, check_timeout = 60):
        """

        :param id: 
        :param check_timeout: 
        :return: 
        """
        while check_timeout > 0:
            state = self.nova_client.get_instance_state(id)
            if "ACTIVE" in state:
                return True
            else:
                check_timeout -= 1
            check_timeout -= 1
            time.sleep(1)
        return False


if __name__ == '__main__':
    a = RecoveryInstance()
