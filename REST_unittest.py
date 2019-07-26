import unittest
import httplib
import urllib
import xmlrpclib
import ConfigParser
import json
import HASS_RESTful
from Hass import Hass


config = ConfigParser.RawConfigParser()
config.read('hass.conf')

REST_host = config.get("RESTful","host")
REST_port = int(config.get("RESTful","port"))

rpc_username = config.get("rpc","rpc_username")
rpc_password = config.get("rpc","rpc_password")
rpc_port = int(config.get("rpc","rpc_bind_port"))

openstack_user_name = config.get("openstack", "openstack_admin_account")
openstack_domain = config.get("openstack", "openstack_user_domain_id")
openstack_password = config.get("openstack", "openstack_admin_password")

keystone_port = int(config.get("keystone_auth","port"))

# get RPC connection to HASS
auth_url = "http://%s:%s@127.0.0.1:%s" % (rpc_username, rpc_password, rpc_port)
server = xmlrpclib.ServerProxy(auth_url)

#get openstack access token
data = '{ "auth": { "identity": { "methods": [ "password" ], "password": { "user": { "name": \"%s\", "domain": { "name": \"%s\" }, "password": \"%s\" } } } } }' % (openstack_user_name, openstack_domain, openstack_password)
headers = {"Content-Type": "application/json"}
http_client = httplib.HTTPConnection(REST_host, keystone_port, timeout=30)
http_client.request("POST", "/v3/auth/tokens", body=data, headers=headers)
token = http_client.getresponse().getheaders()[1][1]

#token = "gAAAAABauLthXBbVmUZsg2ZkaioPdJDmY00s07Esz85chANS9PB8EDOksS2DmNyuGDD6tKfVkN9I6hh7s9pRIfUYM6UTO7LbwwNzWwLcrClPAGbmn2k3gbcuIrMJ3eZLeJQzdbd9djfayS0njFxZQgeRNZMenq6UrQ"

# set up global headers
headers = {'Content-Type' : 'application/json',
		   'X-Auth-Token' : token}

# message declaration
MESSAGE_OK = 'succeed'
MESSAGE_FAIL = 'failed'

app = HASS_RESTful.app.test_client()
HASS = Hass()
HASS_RESTful.RESTfulThread(HASS)

# global function for reset HASS
def HASS_reset():
    cluster_list = HASS.listCluster()
    for cluster in cluster_list:
        HASS.deleteCluster(cluster["cluster_id"])

def convert_res_to_dict(res):
    return res.__dict__

class ClusterTest(unittest.TestCase):
	# set up before every test case runinng.
    def setUp(self):
        self.conn = httplib.HTTPConnection(REST_host, REST_port, timeout=30)
        self.cluster_name = 'test'

    def test_create_cluster(self):
        # perform http request
        data = {"cluster_name": self.cluster_name}
        data = json.dumps(data)
        res = app.post("/HASS/api/cluster", data=data, headers=headers)
        res = json.loads(res.data)
        # assert equal
        self.assertEqual(res["code"], MESSAGE_OK)
        self.assertEqual(len(HASS.listCluster()), 1)
        # clean the data after test case end.

    def tearDown(self):
        HASS_reset()


class NodeTest(unittest.TestCase):
    # set up before every test case runinng.
    def setUp(self):
        self.conn = httplib.HTTPConnection(REST_host, REST_port, timeout=30)
        self.cluster_name = 'test'

    def test_add_node_default_detection(self):
        response = HASS.createCluster(self.cluster_name)
        cluster_id = convert_res_to_dict(response)["data"]["clusterId"]
        node_list = ["compute1", "compute2"]
        detection_list = []
        # perform http request
        data = {"cluster_id": cluster_id, "node_list": node_list, "detection_list": detection_list}
        data = json.dumps(data)
        res = app.post("/HASS/api/node", data=data, headers=headers)
        res = json.loads(res.data)
        print res
        nodeList = res["data"]["node"]
        detectionList = res["data"]["detection"]
        # assert equal
        self.assertEqual(res["code"], MESSAGE_OK)
        self.assertEqual(len(nodeList), 2)
        self.assertEqual(len(detectionList), 6)
    #
    def test_add_node_custom_host_detection(self):
        response = HASS.createCluster(self.cluster_name)
        cluster_id = convert_res_to_dict(response)["data"]["clusterId"]
        node_list = ["compute1", "compute2"]
        detection_list = ["1", "3"]
        # perform http request
        data = {"cluster_id": cluster_id, "node_list": node_list, "detection_list": detection_list}
        data = json.dumps(data)
        res = app.post("/HASS/api/node", data=data, headers=headers)
        res = json.loads(res.data)
        print res
        nodeList = res["data"]["node"]
        detectionList = res["data"]["detection"]
        # assert equal
        self.assertEqual(res["code"], MESSAGE_OK)
        self.assertEqual(len(nodeList), 2)
        self.assertEqual(len(detectionList), 2)

    def test_add_node_custom_vm_detection(self):
        response = HASS.createCluster(self.cluster_name)
        cluster_id = convert_res_to_dict(response)["data"]["clusterId"]
        node_list = ["compute1", "compute2"]
        detection_list = ["5", "6"]
        # perform http request
        data = {"cluster_id": cluster_id, "node_list": node_list, "detection_list": detection_list}
        data = json.dumps(data)
        res = app.post("/HASS/api/node", data=data, headers=headers)
        res = json.loads(res.data)
        print res
        nodeList = res["data"]["node"]
        detectionList = res["data"]["detection"]
        # assert equal
        self.assertEqual(res["code"], MESSAGE_OK)
        self.assertEqual(len(nodeList), 2)
        self.assertEqual(len(detectionList), 2)
    #
    def test_add_node_custom_host_vm_detection(self):
        response = HASS.createCluster(self.cluster_name)
        cluster_id = convert_res_to_dict(response)["data"]["clusterId"]
        node_list = ["compute1", "compute2"]
        detection_list = ["1","3","5","6"]
        # perform http request
        data = {"cluster_id": cluster_id, "node_list": node_list, "detection_list": detection_list}
        data = json.dumps(data)
        res = app.post("/HASS/api/node", data=data, headers=headers)
        res = json.loads(res.data)
        print res
        nodeList = res["data"]["node"]
        detectionList = res["data"]["detection"]
        # assert equal
        self.assertEqual(res["code"], MESSAGE_OK)
        self.assertEqual(len(nodeList), 2)
        self.assertEqual(len(detectionList), 4)
    #
    def test_list_node_default_detection(self):
        node_list = ["compute1", "compute2"]
        detection_list = []
        response = HASS.createCluster(self.cluster_name)
        cluster_id = convert_res_to_dict(response)["data"]["clusterId"]
        HASS.addNode(cluster_id, node_list, detection_list)
        # perform http request
        data = {"cluster_id": cluster_id}
        data = json.dumps(data)
        endpoint = "/HASS/api/nodes/%s" % cluster_id
        res = app.get(endpoint, data=data, headers=headers)
        res = json.loads(res.data)
        print res
        detectionList = res["data"]["nodeList"][1]["detection_list"]
        for nodelist in res["data"]["nodeList"]:
            n = nodelist["node_name"].split()
            return n
        # assert equal
        self.assertEqual(res["code"], MESSAGE_OK)
        self.assertEqual(len(n),2)
        self.assertEqual(len(detectionList), 6)

    def test_list_node_custom_host_detection(self):
        node_list = ["compute1", "compute2"]
        detection_list = ["1","3"]
        response = HASS.createCluster(self.cluster_name)
        cluster_id = convert_res_to_dict(response)["data"]["clusterId"]
        HASS.addNode(cluster_id, node_list, detection_list)
        # perform http request
        data = {"cluster_id": cluster_id}
        data = json.dumps(data)
        endpoint = "/HASS/api/nodes/%s" % cluster_id
        res = app.get(endpoint, data=data, headers=headers)
        res = json.loads(res.data)
        print res
        detectionList = res["data"]["nodeList"][1]["detection_list"]
        for nodelist in res["data"]["nodeList"]:
            n = nodelist["node_name"].split()
            return n
        # assert equal
        self.assertEqual(res["code"], MESSAGE_OK)
        self.assertEqual(len(n),2)
        self.assertEqual(len(detectionList), 2)

    def test_list_node_custom_vm_detection(self):
        node_list = ["compute1", "compute2"]
        detection_list = ["5","6"]
        response = HASS.createCluster(self.cluster_name)
        cluster_id = convert_res_to_dict(response)["data"]["clusterId"]
        HASS.addNode(cluster_id, node_list, detection_list)
        # perform http request
        data = {"cluster_id": cluster_id}
        data = json.dumps(data)
        endpoint = "/HASS/api/nodes/%s" % cluster_id
        res = app.get(endpoint, data=data, headers=headers)
        res = json.loads(res.data)
        print res
        detectionList = res["data"]["nodeList"][1]["detection_list"]
        for nodelist in res["data"]["nodeList"]:
            n = nodelist["node_name"].split()
            return n
        # assert equal
        self.assertEqual(res["code"], MESSAGE_OK)
        self.assertEqual(len(n),2)
        self.assertEqual(len(detectionList), 2)

    def test_list_node_custom_host_vm_detection(self):
        node_list = ["compute1", "compute2"]
        detection_list = ["1","3","5","6"]
        response = HASS.createCluster(self.cluster_name)
        cluster_id = convert_res_to_dict(response)["data"]["clusterId"]
        HASS.addNode(cluster_id, node_list, detection_list)
        # perform http request
        data = {"cluster_id": cluster_id}
        data = json.dumps(data)
        endpoint = "/HASS/api/nodes/%s" % cluster_id
        res = app.get(endpoint, data=data, headers=headers)
        res = json.loads(res.data)
        print res
        detectionList = res["data"]["nodeList"][1]["detection_list"]
        for nodelist in res["data"]["nodeList"]:
            n = nodelist["node_name"].split()
            return n
        # assert equal
        self.assertEqual(res["code"], MESSAGE_OK)
        self.assertEqual(len(n),2)
        self.assertEqual(len(detectionList), 4)

    def tearDown(self):
        self.conn.close()
        HASS_reset()

if __name__ == '__main__':
	unittest.main()

