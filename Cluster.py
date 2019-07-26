#########################################################
#:Date: 2017/12/13
#:Version: 1
#:Authors:
#    - Elma Huang <huanghuei0206@gmail.com>
#    - LSC <sclee@g.ncu.edu.tw>
#:Python_Version: 2.7
#:Platform: Unix
#:Description:
#	This is a class which maintains cluster data structure.
##########################################################

from ClusterInterface import ClusterInterface
from Response import Response
from Node import Node
from Instance import Instance
from IPMIModule import IPMIManager
import socket
import uuid
import logging
import ConfigParser
import paramiko


class Cluster(ClusterInterface):
    def __init__(self, id, name):
        super(Cluster, self).__init__(id, name)
        self.ipmi = IPMIManager()
        self.config = ConfigParser.RawConfigParser()
        self.config.read('/home/localadmin/HASS/hass.conf')

    def addNode(self, node_name_list, detection_list):
        # create node list
        message = ""
        if node_name_list == []:
            return Response(code="failed",
                            message="not enter any node",
                            data=None)
        try:
            for node_name in node_name_list:
                if self._isInComputePool(node_name):
                #if self._isInComputePool(node_name) and self.ipmi._getIPMIStatus(node_name) == True:
                    # print node_name_list
                    node = Node(name=node_name, cluster_id=self.id, detection_list=detection_list)
                    self.node_list.append(node)
                    node.startDetectionThread()
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(node_name, username='root', password='openstack')
                    client.exec_command('service detectionagent restart')
                    message = "Cluster--The node %s is added to cluster." % self.getAllNodeStr()
                    logging.info(message)
                    # result = {"code": "0","clusterId": self.id,"node":node_name, "message": message}
                    result = Response(code="succeed",
                                      message=message,
                                      data={"clusterId": self.id, "node": self.getAllNodeList(),
                                            "detection": node.getDetectionList()})
                else:
                    node = Node(name=node_name, cluster_id=self.id, detection_list=detection_list)
                    message += "the node %s is illegal. may be without IPMI support or not in the compute pool, please check the configuration.  " % node_name
                    result = Response(code="failed",
                                      message=message,
                                      data={"clusterId": self.id, "node": self.getAllNodeList(),
                                            "detection": node.getDetectionList()})
                    logging.error(message)
        except Exception as e:
            print str(e)
            message = "Cluster-- add node fail , some node maybe overlapping or not in compute pool please check again! The node list is %s." % (
                self.getAllNodeStr())
            logging.error(message)
            # result = {"code": "1", "clusterId": self.id, "message": message}
            result = Response(code="failed",
                              message=message,
                              data={"clusterId": self.id})
        finally:
            return result

    def deleteNode(self, node_name):
        try:
            node = self.getNodeByName(node_name)
            # stop Thread
            node.deleteDetectionThread()
            node.delete_ssh_client()
            self.deleteInstanceByNode(node)
            self.node_list.remove(node)
            # ret = self.getAllNodeInfo()
            for node in self.node_list:
                if node.name == node_name:
                    return Response(code="failed",
                                    message="delete node %s failed" % node_name,
                                    data={"fail_node":node_name})
            message = "Cluster delete node success! node is %s , node list is %s,cluster id is %s." % (
                node_name, self.getAllNodeStr(), self.id)
            logging.info(message)
            # result = {"code": "0","clusterId": self.id, "node":node_name, "message": message}
            result = Response(code="succeed",
                              message=message,
                              data={"clusterId": self.id, "node": node_name})
        except Exception as e:
            logging.error(str(e))
            message = "Cluster delete node fail , node maybe not in the node list please check again! node is %s  The node list is %s." % (
                node_name, self.getAllNodeStr())
            logging.error(message)
            # result = {"code": "1", "node":node_name,"clusterId": self.id, "message": message}
            result = Response(code="failed",
                              message=message,
                              data={"clusterId": self.id, "node": node_name})
        finally:
            return result

    def getAllNodeInfo(self):
        ret = []
        for node in self.node_list:
            ret.append(node.getInfo())
        return ret

    def addInstance(self, instance_id):
        if not self.checkInstanceExist(instance_id):
            return Response(code="failed",
                            message="instance %s doesn't exist" % instance_id,
                            data=None)
        elif not self.checkInstanceBootFromVolume(instance_id):
            return Response(code="failed",
                            message="instance %s doesn't booted from volume" % instance_id,
                            data=None)
        elif not self.checkInstancePowerOn(instance_id):
            return Response(code="failed",
                            message="instance %s is not power on" % instance_id,
                            data=None)
        else:
            try:
                # Live migration VM to cluster node
                final_host = self.checkInstanceHost(instance_id)
                if final_host == None:
                    final_host = self.liveMigrateInstance(instance_id)
                instance = Instance(id=instance_id,
                                    name=self.nova_client.getInstanceName(instance_id),
                                    host=final_host,
                                    status=self.nova_client.getInstanceState(instance_id),
                                    network=self.nova_client.getInstanceNetwork(instance_id))
                self.sendUpdateInstance(final_host)
                self.instance_list.append(instance)
                message = "Cluster--Cluster add instance success ! The instance id is %s." % (instance_id)
                logging.info(message)
                # result = {"code":"0","cluster id":self.id,"node":final_host,"instance id":instance_id,"message":message}
                result = Response(code="succeed",
                                  message=message,
                                  data={"cluster id": self.id, "node": final_host, "instance id": instance_id})
            except Exception as e:
                print str(e)
                message = "Cluster--Cluster add instance fail ,please check again! The instance id is %s." % (instance_id)
                logging.error(message)
                # result = {"code":"1","cluster id":self.id,"instance id":instance_id,"message":message}
                result = Response(code="failed",
                                  message=message,
                                  data={"cluster id": self.id, "instance id": instance_id})
            finally:
                return result

    def deleteInstance(self, instance_id, send_flag=True):
        result = None
        for instance in self.instance_list:
            host = instance.host
            if instance.id == instance_id:
                self.instance_list.remove(instance)
                if send_flag : self.sendUpdateInstance(host)
                message = "Cluster--delete instance success. this instance is deleted (instance_id = %s)" % instance_id
                logging.info(message)
                # result = {"code": "0", "clusterId": self.id, "instance id": instance_id, "message": message}
                result = Response(code="succeed",
                                  message=message,
                                  data={"cluster_id": self.id, "instance_id": instance_id})
        # if instanceid not in self.instacne_list:
        if result == None:
            message = "Cluster--delete instance fail ,please check again! The instance id is %s." % instance_id
            logging.error(message)
            # result = {"code": "1", "cluster id": self.id, "instance id": instance_id, "message": message}
            result = Response(code="failed",
                              message=message,
                              data={"cluster_id": self.id, "instance_id": instance_id})
        return result

    def deleteInstanceByNode(self, node):
        protected_instance_list = self.getProtectedInstanceListByNode(node)
        for instance in protected_instance_list:
            self.deleteInstance(instance.id)

    # list Instance
    def getAllInstanceInfo(self):
        legal_instance = []
        illegal_instance = []
        try:
            for instance in self.instance_list[:]:
                prev_host = instance.host
                check_instance_result = self._checkInstance(instance)
                if check_instance_result == False:
                    illegal_instance.append({'id':instance.id, 'prev_host':prev_host})
                else:
                    info = instance.getInfo()
                    legal_instance.append(info)
        except Exception as e:
            print "cluster--getAllInstanceInfo fail:", str(e)
        finally:
            return legal_instance, illegal_instance

    def _checkInstance(self, instance):
    	try:
            instance_info = instance.getInfo()
            host = instance_info["host"]
            if "SHUTOFF" in instance_info:
                return False
            elif host not in self.getAllNodeStr():
                return False
            else:
                return True
        except Exception as e:
            print "Cluster--_checkInstance-exception--" + str(e)
            return False


    # cluster.addInstance
    def findNodeByInstance(self, instance_id):
        for node in self.node_list:
            if node.containsInstance(instance_id):
                return node
        return None

    def _isInComputePool(self, unchecked_node_name):
        return unchecked_node_name in self.nova_client.getComputePool()

    # be DB called
    def getNodeList(self):
        return self.node_list

    def sendUpdateInstance(self, host_name):
        host = self.getNodeByName(host_name)
        host.sendUpdateInstance()

    # be deleteNode called
    def getNodeByName(self, name):
        # node_list = self.getNodeList()
        for node in self.node_list:
            if node.name == name:
                return node
        return None

    # addNode message
    def getAllNodeStr(self):
        ret = ""
        for node in self.node_list:
            ret += node.name + " "
        return ret

    def getAllNodeList(self):
        ret = []
        for node in self.node_list:
            ret.append(node.name)
        return ret

    # clustermanager.deletecluster call
    def deleteAllNode(self):
        for node in self.node_list[:]:
            self.deleteNode(node.name)
            # print "node list:",self.node_list

    def getInfo(self):
        return {"cluster_id": self.id, "cluster_name": self.name}

    def checkInstanceBootFromVolume(self, instance_id):
        # if specify shared_storage to be true, enable file level HA and volume level HA
        if self.config.getboolean("default", "shared_storage") == True:
            return True
        if not self.nova_client.isInstanceBootFromVolume(instance_id):
            message = "this instance doesn't boot from volume! Instance id is %s " % instance_id
            logging.error(message)
            return False
        return True

    def checkInstancePowerOn(self, instance_id):
        if not self.nova_client.isInstancePowerOn(instance_id):
            message = "this instance is not running! Instance id is %s " % instance_id
            logging.error(message)
            return False
        return True

    def checkInstanceExist(self, instance_id):
        node_list = self.nova_client.getComputePool()
        print "node list of all compute node:", node_list
        instance_list = self.nova_client.getAllInstanceList()
        print instance_list
        for instance in instance_list:
            # print node_list
            if instance.id == instance_id:
                logging.info("Cluster--addInstance-checkInstanceExist success")
                return True
        message = "this instance is not exist. Instance id is %s. " % instance_id
        logging.error(message)
        return False

    def isProtected(self, instance_id):
        for instance in self.instance_list[:]:
            if instance.id == instance_id:
                return True
        message = "this instance is  already in the cluster. Instance id is %s. cluster id is %s .instance list is %s" % (
            instance_id, self.id, self.instance_list)
        logging.error(message)
        return False

    def findTargetHost(self, fail_node):
        import random
        target_list = [node for node in self.node_list if node != fail_node]
        target_host = random.choice(target_list)
        return target_host

    def updateInstance(self):
        for instance in self.instance_list:
            instance.updateInfo()
            instance.host = self.nova_client.getInstanceHost(instance.id)
            print "instance %s update host to %s" % (instance.name, instance.host)
            logging.info("instance %s update host to %s" % (instance.name, instance.host))

    def checkInstanceHost(self, instance_id):
        host = self.nova_client.getInstanceHost(instance_id)
        for node in self.node_list[:]:
            if host == node.name:
                return host
        return None

    def liveMigrateInstance(self, instance_id):
        host = self.nova_client.getInstanceHost(instance_id)
        host = self.getNodeByName(host)
        target_host = self.findTargetHost(host)
        print "start live migrate vm from ", host.name, "to ", target_host.name
        final_host = self.nova_client.liveMigrateVM(instance_id, target_host.name)
        # print final_host
        return final_host

    def evacuate(self, instance, target_host, fail_node):
        self.nova_client.evacuate(instance, target_host, fail_node)

    def getProtectedInstanceList(self):
        return self.instance_list

    def getProtectedInstanceListByNode(self, node):
        ret = []
        protected_instance_list = self.getProtectedInstanceList()
        for instance in protected_instance_list:
            if instance.host == node.name:
                ret.append(instance)
        return ret

if __name__ == "__main__":
    a = Cluster("123", "name")
    a.addNode(["compute1","compute2"])
    a.liveMigrateInstance("02ed0527-84d3-4178-9795-810b7d4e7010")
