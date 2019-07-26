#########################################################
#:Date: 2018/2/13
#:Version: 1
#:Authors:
#    - Elma Huang <huanghuei0206@gmail.com>
#    - LSC <sclee@g.ncu.edu.tw>
#:Python_Version: 2.7
#:Platform: Unix
#:Description:
#   This is a class maintains ha instance data structure.
##########################################################


from NovaClient import NovaClient


class Instance(object):
    def __init__(self, cluster_id, ha_instance):
        self.nova_client = NovaClient.get_instance()
        self.cluster_id = cluster_id
        self.id = ha_instance["id"]
        self.name = ha_instance["name"]
        self.host = ha_instance["host"]
        self.status = ha_instance["status"]
        self.network = ha_instance["network"]
        self.network_self = []
        self.network_provider = []
        self.update_network()
        print(
            "cluster_id:", self.cluster_id, "id:", self.id, " name:", self.name, " host:", self.host,
            " status:",
            self.status, " network_s:", self.network_self, "p:", self.network_provider)

    def update_network(self):
        print("update net")
        # {'selfservice':", "['192.168.1.8',", "'192.168.0.212']}
        for router_name, ip_list in self.network.iteritems():
            for ip in ip_list:
                status = self._check_external_network(ip)
                if status:
                    self.network_provider.append(ip)
                else:
                    self.network_self.append(ip)
                    
    def _check_external_network(self, ip):
        ext_ip = self.nova_client.get_instance_external_network(ip)
        if not ext_ip:
            return False
        return True
