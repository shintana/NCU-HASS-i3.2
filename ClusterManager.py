#########################################################
#:Date: 2017/12/13
#:Version: 1
#:Authors:
#    - Elma Huang <huanghuei0206@gmail.com>
#    - LSC <sclee@g.ncu.edu.tw>
#:Python_Version: 2.7
#:Platform: Unix
#:Description:
#	This is a static class which maintains all the data structure.
##########################################################

from Cluster import Cluster
from Node import Node
from DatabaseManager import DatabaseManager
from Response import Response
import uuid
import logging
import paramiko


class ClusterManager():
    _cluster_dict = None
    _db = None
    _RESET_DB = False

    @staticmethod
    def init():
        ClusterManager._cluster_dict = {}
        ClusterManager._db = DatabaseManager()
        ClusterManager._db.createTable()
        ClusterManager.syncFromDatabase()

    @staticmethod
    def createCluster(cluster_name, cluster_id=None, write_DB=True):
        if ClusterManager._isNameOverLapping(cluster_name):
            message = "ClusterManager - cluster name overlapping"
            # result = {"code": "1","clusterId":cluster_id, "message": message}
            result = Response(code="failed",
                              message=message,
                              data={"clusterId": cluster_id})
            return result
        else:
            logging.info("ClusterManager - cluster name is not overlapping")
            result = ClusterManager._addToClusterList(cluster_name, cluster_id)

            if result.code == "succeed" and write_DB:
                ClusterManager.syncToDatabase()
            return result

    @staticmethod
    def deleteCluster(cluster_id, write_DB=True):
        cluster = ClusterManager.getCluster(cluster_id)
        if not cluster:
            message = "delete cluster fail. The cluster is not found. (cluster_id = %s)" % cluster_id
            # result = {"code": "1", "clusterId":cluster_id, "message":message}
            result = Response(code="failed",
                              message=message,
                              data={"clusterId": cluster_id})
            return result
        else:
            result = None
            try:
                cluster.deleteAllNode()
                # check delete all nodes of cluster
                if cluster.node_list == []:
                    del ClusterManager._cluster_dict[cluster_id]
                else:
                    message = "delete all nodes of cluster fail"
                    logging.error(message)
                    result = Response(code="failed",
                                      message=message,
                                      data={"clusterId": cluster_id})
                # check del cluster
                for cluster in ClusterManager._cluster_dict:
                    if cluster == cluster_id:
                        message = "delete cluster fail"
                        logging.error(message)
                        result = Response(code="failed",
                                          message=message,
                                          data={"clusterId": cluster_id})
                if result == None:
                    message = "delete cluster success. The cluster is deleted. (cluster_id = %s)" % cluster_id
                    logging.info(message)
                    # result = {"code": "0", "clusterId": cluster_id, "message": message}
                    result = Response(code="succeed",
                                      message=message,
                                      data={"clusterId": cluster_id})
                if write_DB:
                    ClusterManager.syncToDatabase()
                return result
            except Exception as e:
                message = "deleteCluster fail" + str(e)
                logging.error(message)
                result = Response(code="failed",
                                  message=message,
                                  data={"clusterId": cluster_id})
                return result

    @staticmethod
    def getClusterList():
        return ClusterManager._cluster_dict

    @staticmethod
    def listCluster():
        res = []
        for id, cluster in ClusterManager._cluster_dict.iteritems():
            res.append((cluster.getInfo()))
        return res

    @staticmethod
    def addNode(cluster_id, node_name_list, detection_list, write_DB=True):
        message = ""
        tmp = list(set(node_name_list)) # remove duplicate
        tmp_detection = list(set(detection_list))
        if detection_list == []:
            tmp_detection = ['1','2','3','4','5','6','7']
        for node_name in tmp[:]:
            if not ClusterManager._checkNodeOverlappingForAllCluster(node_name):
                print "%s is already in a HA cluster. " % node_name
                message += "%s is overlapping node" % node_name
                tmp.remove(node_name)
        if tmp == []:
            return Response(code="failed",
                            message="node overlapping %s" % (str(node_name_list)),
                            data={"overlapping_node":node_name_list})
        cluster = ClusterManager.getCluster(cluster_id)
        if not cluster:
            message += "ClusterManager--Add the node to cluster failed. The cluster is not found. (cluster_id = %s)" % cluster_id
            # result = {"code": "1", "clusterId":cluster_id, "message":message}
            result = Response(code="failed",
                              message=message,
                              data={"clusterId": cluster_id})
            return result
        else:
            try:
                result = cluster.addNode(tmp, tmp_detection)
                logging.info("ClusterManager--add node success.cluster id is %s ,node is %s, active detection id is %s " % (cluster_id, tmp, tmp_detection))
                if result.code == "succeed" and write_DB:
                    ClusterManager.syncToDatabase()
                return result
            except Exception as e:
                message += "add node fail. node not found. (node_name = %s)"  % tmp +str(e)
                logging.error(message)
                # result = {"code": "1", "clusterId": cluster_id, "message": message}
                result = Response(code="failed",
                                  message=message,
                                  data={"clusterId": cluster_id})
                return result

    @staticmethod
    def deleteNode(cluster_id, node_name, write_DB=True):
        cluster = ClusterManager.getCluster(cluster_id)
        if not cluster:
            message = "delete the node failed. The cluster is not found. (cluster_id = %s)" % cluster_id
            # result = {"code": "1", "clusterId":cluster_id, "message":message}
            result = Response(code="failed",
                              message=message,
                              data={"clusterId": cluster_id})
            return result
        else:
            try:
                result = cluster.deleteNode(node_name)
                logging.info(
                    "ClusterManager-- delete node success ,cluster id is %s node is %s" % (cluster_id, node_name))
                if write_DB:
                    ClusterManager.syncToDatabase()
                return result
            except Exception as e:
                # code = "1"
                message = "delete node fail. node not found. (node_name = %s)" % node_name + str(e)
                logging.error(message)
                # result = {"code": "1", "clusterId":cluster_id, "message":message}
                result = Response(code="failed",
                                  message=message,
                                  data={"clusterId": cluster_id})
                return result

    @staticmethod
    def listNode(cluster_id):
        try:
            cluster = ClusterManager.getCluster(cluster_id)
            if not cluster:
                message = "list the node failed. The cluster is not found. (cluster_id = %s)" % cluster_id
                # result = {"code": "1", "clusterId":cluster_id, "message":message}
                result = Response(code="failed",
                                  message=message,
                                  data={"clusterId": cluster_id})
                return result
            nodelist = cluster.getAllNodeInfo()
            message = "ClusterManager-listNode--get all node info finish"
            logging.info(message)
            result = Response(code="succeed",
                              message=message,
                              data={"clusterId": cluster_id, "nodeList": nodelist})
            return result
        except Exception as e:
            message = "ClusterManager--listNode-- get all node info fail" + str(e)
            logging.error(message)
            result = Response(code="failed",
                              message=message,
                              data={"clusterId": cluster_id})
            return result

    @staticmethod
    def addInstance(cluster_id, instance_id, write_DB=True):
        cluster = ClusterManager.getCluster(cluster_id)
        message = ""
        if not cluster:
            message = "ClusterManager--Add the instance to cluster failed. The cluster is not found. (cluster_id = %s)" % cluster_id
            # result = {"code": "1", "clusterId":cluster_id, "message":message}
            result = Response(code="failed",
                              message=message,
                              data={"clusterId": cluster_id})
            return result
        else:
            try:
                if not ClusterManager._checkInstanceNOTOverlappingForAllCluster(instance_id):
                    return Response(code="failed",
                                    message="instance %s is already being protected" % instance_id,
                                    data={"instance": instance_id})
                result = cluster.addInstance(instance_id)
                if write_DB:
                    ClusterManager.syncToDatabase()
                logging.info(
                    "ClusterManager--Add instance success , instance_id : %s , cluster_id : %s" % (
                    instance_id, cluster_id))
                return result
            except Exception as e:
                print str(e)
                message = "ClusterManager --add the instacne fail.instance_id : %s , cluster_id : %s"  % (
                    instance_id, cluster_id) + str(e)
                logging.error(message)
                # result = {"code": "1", "clusterId": cluster_id, "message": message}
                result = Response(code="failed",
                                  message=message,
                                  data={"clusterId": cluster_id})
                return result

    @staticmethod
    def deleteInstance(cluster_id, instance_id, send_flag=True, write_DB=True):
        cluster = ClusterManager.getCluster(cluster_id)
        if not cluster:
            message = "delete the instance to cluster failed. The cluster is not found. (cluster_id = %s)" % cluster_id
            # result = {"code": "1", "clusterId": cluster_id, "instance id ": instance_id, "message": message}
            result = Response(code="failed",
                              message=message,
                              data={"clusterId": cluster_id, "instance id": instance_id})
            return result
        else:
            try:
                result = cluster.deleteInstance(instance_id, send_flag)
                if write_DB:
                    ClusterManager.syncToDatabase()
                logging.info("ClusterManager--delete instance success")
                return result
            except Exception as e:
                #logging.error(str(e))
                print str(e)
                message = "ClusterManager--delete instance failed. this instance is not being protected (instance_id = %s)" % instance_id +str(e)
                logging.error(message)
                # result = {"code": "1", "clusterId":cluster_id, "message":message}
                result = Response(code="failed",
                                  message=message,
                                  data={"clusterId": cluster_id})
                return result

    @staticmethod
    def listInstance(cluster_id, send_flag=True):
        cluster = ClusterManager.getCluster(cluster_id)
        if not cluster:
            message = "ClusterManager--list the instance failed. The cluster is not found. (cluster_id = %s)" % cluster_id
            return Response(code="failed",
                            message=message,
                            data={"cluster_id": cluster_id})
        try:
            instance_list, illegal_instance = cluster.getAllInstanceInfo()
            if illegal_instance != []:
            	ClusterManager.deleteInstance(cluster_id, instance["id"], False)
            if send_flag == True:
            	for instance in instance_list[:]:
                    cluster.sendUpdateInstance(instance["host"])  # info[2]
                for instance in illegal_instance[:]:
                    cluster.sendUpdateInstance(instance["prev_host"])  # prev_host
            logging.info("ClusterManager--listInstance,getInstanceList success,instanceList is %s" % instance_list)
            result = Response(code="succeed",
                              message=None,
                              data={"instanceList": instance_list})
            return result
        except:
            logging.error("ClusterManager--listInstance,getInstanceList fail")

    @staticmethod
    def _addToClusterList(cluster_name, cluster_id=None):
        try:
            # result = None
            if cluster_id:
                cluster = Cluster(id=cluster_id, name=cluster_name)
                ClusterManager._cluster_dict[cluster_id] = cluster
                message = "ClusterManager -syncofromDB-- createCluster._addToCluster success,cluster id = %s" % cluster_id
                logging.info(message)
                # result = {"code": "0", "clusterId":cluster_id,"message": message}
                result = Response(code="succeed",
                                  message=message,
                                  data={"clusterId": cluster_id})
                return result
            else:
                # start add to cluster list
                cluster_id = str(uuid.uuid4())
                cluster = Cluster(id=cluster_id, name=cluster_name)
                ClusterManager._cluster_dict[cluster_id] = cluster
                message = "ClusterManager - createCluster._addToClusterList success,cluster id = %s" % cluster_id
                logging.info(message)
                # result = {"code": "0","clusterId":cluster_id, "message":message}
                result = Response(code="succeed",
                                  message=message,
                                  data={"clusterId": cluster_id})
                return result
        except Exception as e:
            message = "ClusterManager - createCluster._addToCluster fail,cluster id : %s" % cluster_id + str(e)
            logging.error(message)
            # result = {"code": "1","clusterId":cluster_id, "message": message}
            result = Response(code="failed",
                              message=message,
                              data={"clusterId": cluster_id})
            return result

    @staticmethod
    def _checkNodeOverlappingForAllCluster(node_name):
        for id, cluster in ClusterManager._cluster_dict.items():
            for node in cluster.node_list[:]:
                if node_name == node.name:
                    logging.error("%s already be add into cluster %s" % (node_name, id))
                    return False
        return True

    @staticmethod
    def _checkInstanceNOTOverlappingForAllCluster(instance_id):
        for id, cluster in ClusterManager._cluster_dict.items():
            for instance in cluster.instance_list:
                if instance_id == instance.id:
                    return False
        return True

    @staticmethod
    def getCluster(cluster_id):
        if not ClusterManager._isCluster(cluster_id):
            logging.error("cluster not found id %s" % cluster_id)
            return None
        return ClusterManager._cluster_dict[cluster_id]

    @staticmethod
    def _isNameOverLapping(name):
        for cluster_id, cluster in ClusterManager._cluster_dict.items():
            if cluster.name == name:
                return True
        return False

    @staticmethod
    def _isCluster(cluster_id):
        if cluster_id in ClusterManager._cluster_dict:
            return True
        return False

    @staticmethod
    def reset():
        if ClusterManager._RESET_DB:
            ClusterManager._db.resetAll()
        ClusterManager._cluster_dict = {}
        logging.info("ClusterManager--reset DB ,reset_DB = %s" % ClusterManager._RESET_DB)

    @staticmethod
    def syncFromDatabase():
        ClusterManager.reset()
        try:
            exist_cluster = ClusterManager._db.syncFromDB()
            for cluster in exist_cluster:
                ClusterManager.createCluster(cluster["cluster_name"], cluster["cluster_id"], False)
                if cluster["node_list"] != []:
                    ClusterManager.addNode(cluster["cluster_id"], cluster["node_list"], False)
                for instance in cluster["instance_list"]:
                    ClusterManager.addInstance(cluster["cluster_id"], instance)
            logging.info("ClusterManager--synco from DB finish")
        except Exception as e:
            print str(e)
            logging.error("ClusterManagwer--synco from DB fail")

    @staticmethod
    def syncToDatabase():
        cluster_list = ClusterManager._cluster_dict
        ClusterManager._db.syncToDB(cluster_list)


if __name__ == "__main__":
    ClusterManager.init()
    ClusterManager.deleteCluster("8c46ecee-9bd6-4c82-b7c8-6b6d20dc09d7")
