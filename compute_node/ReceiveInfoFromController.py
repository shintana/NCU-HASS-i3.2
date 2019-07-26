import threading
import socket
import xmlrpclib
import subprocess
import ConfigParser
from Instance import Instance
from HAInstance import HAInstance


class ReceiveInfoFromController(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind(('', 5001))
        self.s.listen(5)
        self.config = ConfigParser.RawConfigParser()
        self.config.read('/home/localadmin/HASS/compute_node/hass_node.conf')
        self.authUrl = "http://" + self.config.get("rpc", "rpc_username") + ":" + self.config.get("rpc",
                                                                                                  "rpc_password") + "@" + self.config.get(
            "rpc", "rpc_controller") + ":" + self.config.get("rpc", "rpc_bind_port")
        # self.authUrl = "http://user:0928759204@192.168.0.112:61209"
        self.server = xmlrpclib.ServerProxy(self.authUrl)
        self.host = subprocess.check_output(['hostname']).strip()
        self.ha_instance_list = []

    def run(self):
        while True:
            cs, addr = self.s.accept()
            print "addr:", addr
            d = cs.recv(1024)
            print d
            if d == "update instance":
                self.updateHAInstance()

    def getInstanceFromController(self):
        host_instance = []
        cluster_list = self.server.listCluster()
        for cluster in cluster_list:
            clusterId = cluster["cluster_id"]
            instance_list = self._getHAInstance(clusterId)
            print "HA instacne list:", instance_list
            host_instance = self._getInstanceByNode(instance_list)
        return host_instance

    def _getHAInstance(self, clusterId):
        try:
            instance_list = self.server.listInstance(clusterId, False)["data"]["instanceList"]
        except Exception as e:
            print "get ha instance fail" + str(e)
            instance_list = []
        finally:
            return instance_list

    def _getInstanceByNode(self, instance_list):
        host_instance = []
        for instance in instance_list:
            if self.host in instance["host"]:
                host_instance.append(instance)
        return host_instance

    def updateHAInstance(self):
        # self.clearlog()
        instance_list = self.getInstanceFromController()
        HAInstance.init()
        for instance in instance_list[:]:
            # [self.id, self.name, self.host, self.status, self.network]
            vm = Instance(ha_instance=instance)
            HAInstance.addInstance(vm)
            # self.writelog(ha_vm)

    '''
    def clearlog(self):
        with open('./HAInstance.py', 'w'): pass
        #with open('./log/sucess.log', 'w'): pass

    def writelog(self,str):
        with open('./HAInstance.py', 'a') as f:
            f.write(str)
            f.close()
    '''
