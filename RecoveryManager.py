#########################################################
#:Date: 2017/12/13
#:Version: 1
#:Authors:
#    - Elma Huang <huanghuei0206@gmail.com>
#    - LSC <sclee@g.ncu.edu.tw>
#:Python_Version: 2.7
#:Platform: Unix
#:Description:
#   This is a class maintains recovery methods.
##########################################################

from ClusterManager import ClusterManager
from NovaClient import NovaClient
from Detector import Detector
from DatabaseManager import IIIDatabaseManager
from Response import Response
import State
import logging
import ConfigParser
import time
import subprocess


class RecoveryManager(object):
    def __init__(self):
        self.nova_client = NovaClient.getInstance()
        self.config = ConfigParser.RawConfigParser()
        self.config.read('/home/localadmin/HASS/hass.conf')
        self.recover_function = {State.NETWORK_FAIL: self.recoverNetworkIsolation,
                                 State.SERVICE_FAIL: self.recoverServiceFail,
                                 State.POWER_FAIL: self.recoverPowerOff,
                                 State.SENSOR_FAIL: self.recoverSensorCritical,
                                 State.OS_FAIL: self.recoverOSHanged}

        self.iii_support = self.config.getboolean("iii", "iii_support")
        self.iii_database = None

    def recover(self, fail_type, cluster_id, fail_node_name):
        return self.recover_function[fail_type](cluster_id, fail_node_name)

    def recoverOSHanged(self, cluster_id, fail_node_name):
        cluster = ClusterManager.getCluster(cluster_id)
        if not cluster:
            logging.error("RecoverManager : cluster not found")
            return
        fail_node = cluster.getNodeByName(fail_node_name)
        print "fail node is %s" % fail_node.name
        print "start recovery vm"
        self.recoverVM(cluster, fail_node)
        print "end recovery vm"
        return self.recoverNodeByReboot(fail_node)

    def recoverPowerOff(self, cluster_id, fail_node_name):
        cluster = ClusterManager.getCluster(cluster_id)
        if not cluster:
            logging.error("RecoverManager : cluster not found")
            return
        fail_node = cluster.getNodeByName(fail_node_name)
        print "fail node is %s" % fail_node.name
        print "start recovery vm"
        self.recoverVM(cluster, fail_node)
        print "end recovery vm"
        return self.recoverNodeByStart(fail_node)

    def recoverNodeCrash(self, cluster_id, fail_node_name):
        cluster = ClusterManager.getCluster(cluster_id)
        if not cluster:
            logging.error("RecoverManager : cluster not found")
            return
        fail_node = cluster.getNodeByName(fail_node_name)
        print "fail node is %s" % fail_node.name
        print "start recovery vm"
        self.recoverVM(cluster, fail_node)
        print "end recovery vm"
        return self.recoverNodeByShutoff(fail_node)

    def recoverNetworkIsolation(self, cluster_id, fail_node_name):
        cluster = ClusterManager.getCluster(cluster_id)
        if not cluster:
            logging.error("RecoverManager : cluster not found")
            return
        fail_node = cluster.getNodeByName(fail_node_name)
        #
        # network_transient_time = int(self.config.get("default", "network_transient_time"))
        # second_chance = State.HEALTH
        # try:
        #     print "start second_chance..."
        #     print "wait %s seconds and check again" % network_transient_time
        #     time.sleep(network_transient_time)  # sleep certain transient seconds and ping host again
        #     response = subprocess.check_output(['timeout', '0.2', 'ping', '-c', '1', fail_node.name],
        #                                        stderr=subprocess.STDOUT, universal_newlines=True)
        # except subprocess.CalledProcessError:
        #     print "After 30 senconds, the network status of %s is still unreachable" % fail_node.name
        #     second_chance = State.NETWORK_FAIL
        #
        # if second_chance == State.HEALTH:
        #     print "The network status of %s return to health" % fail_node.name
        #     return True
        # else:
        #     print "fail node is %s" % fail_node.name
        #     print "start recovery vm"
        self.recoverVM(cluster, fail_node)
        print "end recovery vm"
        return self.recoverNodeByReboot(fail_node)

    def recoverSensorCritical(self, cluster_id, fail_node_name):
        cluster = ClusterManager.getCluster(cluster_id)
        if not cluster:
            logging.error("RecoverManager : cluster not found")
            return
        fail_node = cluster.getNodeByName(fail_node_name)
        print "fail node is %s" % fail_node.name
        print "start recovery vm"
        self.recoverVM(cluster, fail_node)
        print "end recovery vm"
        return self.recoverNodeByShutoff(fail_node)

    def recoverServiceFail(self, cluster_id, fail_node_name):
        cluster = ClusterManager.getCluster(cluster_id)
        if not cluster:
            logging.error("RecoverManager : cluster not found")
            return
        fail_node = cluster.getNodeByName(fail_node_name)

        port = int(self.config.get("detection", "polling_port"))
        #version = self.config.get("openstack_version", "version")
        detector = Detector(fail_node, port)
        fail_services = detector.getFailServices()

        if fail_services == None:
            logging.info("get fail service equals to None, abort recover service fail")
            return True

        status = True
        if "agents" in fail_services:
            status = self.restartDetectionService(fail_node)
        else:
            status = self.restartServices(fail_node, fail_services, version)


        if not status:  # restart service fail
            print "start recovery"
            print "fail node is %s" % fail_node.name
            print "start recovery vm"
            self.recoverVM(cluster, fail_node)
            print "end recovery vm"
            return self.recoverNodeByReboot(fail_node)
        else:
            return status  # restart service success

    def recoverVM(self, cluster, fail_node):
        if len(cluster.getNodeList()) < 2:
            logging.error("RecoverManager : evacuate fail, cluster only one node")
            return
        if not fail_node:
            logging.error("RecoverManager : not found the fail node")
            return
        target_host = cluster.findTargetHost(fail_node)
        print "target_host : %s" % target_host.name
        if not target_host:
            logging.error("RecoverManager : not found the target_host %s" % target_host)

        protected_instance_list = cluster.getProtectedInstanceListByNode(fail_node)
        print "protected list : %s" % protected_instance_list
        for instance in protected_instance_list:
            try:
                if target_host.instanceOverlappingInLibvirt(instance):
                    logging.info("instance %s overlapping in %s" % (instance.name, target_host.name))
                    logging.info("start undefine instance in %s" % target_host.name)
                    print "instance %s overlapping in %s" % (instance.name, target_host.name)
                    print "start undefine instance in %s" % target_host.name
                    target_host.undefineInstance(instance)
                    print "end undefine instance"
            except Exception as e:
                logging.error("instance overlapping in libvirt exception")
                logging.error(str(e))
                logging.info("undefineInstance second chance via socket")
                try:
                    target_host.undefine_instance_via_socket(instance)
                except Exception as e:
                    logging.error("undefine instance sencond chance fail %s" % str(e))
                    pass
            try:
                print "start evacuate"
                logging.info("start evacuate")
                cluster.evacuate(instance, target_host, fail_node)
            except Exception as e:
                print str(e)
                logging.error(str(e))
                logging.error("RecoverManager - The instance %s evacuate failed" % instance.id)

        # print "check instance status"
        # status = self.checkInstanceNetworkStatus(fail_node, cluster)
        # if status == False:
        #     logging.error("RecoverManager : check vm status false")

        print "update instance"
        logging.info("update instance")
        cluster.updateInstance()

        if self.iii_support:
            self.iii_database = IIIDatabaseManager()
            logging.info("start modify iii database")
            print "start modify iii database"
            for instance in protected_instance_list:
                try:
                    self.iii_database.updateInstance(instance.id, target_host.name, fail_node.name)
                except Exception as e:
                    print str(e)
                    logging.error("%s" % str(e))
            print "end modify iii database"
            logging.info("end modify iii database")

    def recoverNodeByReboot(self, fail_node):
        print "start recover node by reboot"
        result = fail_node.reboot()
        print "boot node result : %s" % result.message
        message = "RecoveryManager recover "
        if result.code == "succeed":
            logging.info(message + result.message)
            boot_up = self.checkNodeBootSuccess(fail_node)
            if boot_up:
                print "Node %s recovery finished." % fail_node.name
                return True
            else:
                logging.error(message + "Can not reboot node %s successfully", fail_node.name)
                return False
        else:
            logging.error(message + result.message)
            return False

    def recoverNodeByShutoff(self, fail_node):
        print "start recover node by shutoff"
        result = fail_node.shutoff()
        if result.code == "succeed":
            return False  # shutoff need to remove from cluster, so return False
        else:
            logging.error(result.message)
            print result.message

    def recoverNodeByStart(self, fail_node):
        print "start recover node by start"
        result = fail_node.start()
        print "boot node result : %s" % result.message
        message = "RecoveryManager recover"
        if result.code == "succeed":
            logging.info(message + result.message)
            boot_up = self.checkNodeBootSuccess(fail_node)
            if boot_up:
                print "Node %s recovery finished." % fail_node.name
                return True
            else:
                logging.error(message + "Can not start node %s successfully", fail_node.name)
                return False
        else:
            logging.error(message + result.message)
            return False

    def restartDetectionService(self, fail_node):
        print "Start service failure recovery by starting Detection Agent"
        agent_path = self.config.get("path", "agent_path")
        cmd = "service detectionagent restart"
        print cmd
        try:
            fail_node.remote_exec(cmd)  # restart DetectionAgent service
            time.sleep(5)

            cmd = "ps aux | grep '[D]etectionAgent.py'"
            stdin, stdout, stderr = fail_node.remote_exec(cmd)
            service = stdout.read()
            print service
            if "python DetectionAgent.py" in service:  # check DetectionAgent
                return True
            return False
        except Exception as e:
            print str(e)
            return False

    def restartServices(self, fail_node, fail_services, version, check_timeout=60):
        service_mapping = {"libvirt": "libvirt-bin", "nova": "nova-compute", "qemukvm": "qemu-kvm"}
        fail_service_list = fail_services.split(":")[-1].split(";")[0:-1]

        try:
            for fail_service in fail_service_list:
                fail_service = service_mapping[fail_service]
                if version == "mitaka":
                    cmd = "sudo service %s restart" % fail_service
                else:
                    cmd = "systemctl restart %s" % fail_service
                print cmd
                stdin, stdout, stderr = fail_node.remote_exec(cmd)  # restart service

                while check_timeout > 0:
                    if version == "mitaka":
                        cmd = "service %s status" % fail_service
                    else:
                        cmd = "systemctl status %s | grep active" % fail_service
                    stdin, stdout, stderr = fail_node.remote_exec(cmd)  # check service active or not

                    if not stdout.read():
                        print "The node %s service %s still doesn't work" % (fail_node.name, fail_service)
                    else:
                        print "The node %s service %s successfully restart" % (fail_node.name, fail_service)
                        return True  # recover all the fail service
                    time.sleep(1)
                    check_timeout -= 1
                return False
        except Exception as e:
            print str(e)
            return False

    def checkInstanceNetworkStatus(self, fail_node, cluster, check_timeout=60):
        status = False
        fail = False
        protected_instance_list = cluster.getProtectedInstanceListByNode(fail_node)
        for instance in protected_instance_list:
            try:
                status = self._pingInstance(instance.getIP("ext-net"), check_timeout)
            except Exception as e:
                print "vm : %s has no floating network, abort ping process!" % instance.name
                continue
            if not status:
                fail = True
                logging.error("vm %s cannot ping %s" % (instance.name, instance.getIP("ext-net")))
        return fail

    def _pingInstance(self, ip, check_timeout):
        status = False
        time.sleep(5)
        while check_timeout > 0:
            try:
                print "check vm %s" % ip
                response = subprocess.check_output(['timeout', '0.2', 'ping', '-c', '1', ip], stderr=subprocess.STDOUT,
                                                   universal_newlines=True)
                status = True
                break
            except subprocess.CalledProcessError:
                status = False
            finally:
                time.sleep(1)
                check_timeout -= 1
        return status

    def checkNodeBootSuccess(self, node, check_timeout=300):
        port = int(self.config.get("detection", "polling_port"))
        detector = Detector(node, port)
        print "waiting node to reboot"
        time.sleep(5)
        print "start check node booting"
        while check_timeout > 0:
            try:
                if detector.checkServiceStatus() == State.HEALTH:
                    return True
            except Exception as e:
                print str(e)
            finally:
                time.sleep(1)
                check_timeout -= 1
        return False


if __name__ == "__main__":
    pass
    # r = RecoveryManager()
    # l = r.remote_exec("compute3","virsh list --all")
