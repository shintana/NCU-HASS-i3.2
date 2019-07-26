#########################################################
#:Date: 2017/12/13
#:Version: 1
#:Authors:
#    - Elma Huang <huanghuei0206@gmail.com>
#    - LSC <sclee@g.ncu.edu.tw>
#:Python_Version: 2.7
#:Platform: Unix
#:Description:
#   This is a class which maintains database for both hass/iii.
##########################################################


import logging
import ConfigParser
import MySQLdb, MySQLdb.cursors
import sys


class DatabaseManager(object):
    def __init__(self):
        self.config = ConfigParser.RawConfigParser()
        self.config.read('/home/localadmin/HASS/hass.conf')
        self.db_conn = None
        self.db = None
        try:
            self.connect()
        except MySQLdb.Error, e:
            logging.error("Hass AccessDB - connect to database failed (MySQL Error: %s)", str(e))
            print "MySQL Error: %s" % str(e)
            sys.exit(1)

    def connect(self):
        self.db_conn = MySQLdb.connect(host=self.config.get("mysql", "mysql_ip"),
                                       user=self.config.get("mysql", "mysql_username"),
                                       passwd=self.config.get("mysql", "mysql_password"),
                                       db=self.config.get("mysql", "mysql_db"),
                                       )
        self.db = self.db_conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)

    def checkDB(self):
        try:
            self.db_conn.ping()
        except Exception as e:
            logging.info("MYSQL CONNECTION REESTABLISHED!")
            self.connect()

    def createTable(self):
        self.checkDB()
        try:
            self.db.execute("SET sql_notes = 0;")
            self.db.execute("""
                            CREATE TABLE IF NOT EXISTS ha_cluster 
                            (
                            cluster_uuid char(36),
                            cluster_name char(18),
                            PRIMARY KEY(cluster_uuid)
                            );
                            """)
            self.db.execute("""
                            CREATE TABLE IF NOT EXISTS ha_node 
                            (
                            node_name char(18),
                            below_cluster char(36),
                            detection_list varchar(50),
                            PRIMARY KEY(node_name),
                            FOREIGN KEY(below_cluster)
                            REFERENCES ha_cluster(cluster_uuid)
                            ON DELETE CASCADE
                            );
                            """)
            self.db.execute("""
                            CREATE TABLE IF NOT EXISTS ha_instance 
                            (
                            instance_id char(36),
                            below_cluster char(36),
                            host          char(18),
                            status        char(18),
                            network       char(36),
                            PRIMARY KEY(instance_id),
                            FOREIGN KEY(below_cluster)
                            REFERENCES ha_cluster(cluster_uuid)
                            ON DELETE CASCADE
                            );
                            """)
        except MySQLdb.Error, e:
            self.closeDB()
            logging.error("Hass AccessDB - Create Table failed (MySQL Error: %s)", str(e))
            print "MySQL Error: %s" % str(e)
            sys.exit(1)

    def syncFromDB(self):
        self.checkDB()
        try:
            self.db.execute("SELECT * FROM ha_cluster;")
            ha_cluster_date = self.db.fetchall()
            exist_cluster = []
            for cluster in ha_cluster_date:
                node_list = []
                instance_list = []
                self.db.execute("SELECT * FROM ha_node WHERE below_cluster = '%s'" % cluster["cluster_uuid"])
                ha_node_date = self.db.fetchall()
                self.db.execute("SELECT * FROM ha_instance WHERE below_cluster = '%s'" % cluster["cluster_uuid"])
                ha_instance_date = self.db.fetchall()

                for node in ha_node_date:
                    node_list.append(node["node_name"])
                for instance in ha_instance_date:
                    instance_list.append(instance["instance_id"])
                # cluster_id = cluster["cluster_uuid"][:8]+"-"+cluster["cluster_uuid"][8:12]+"-"+cluster["cluster_uuid"][12:16]+"-"+cluster["cluster_uuid"][16:20]+"-"+cluster["cluster_uuid"][20:]
                cluster_id = cluster["cluster_uuid"]
                cluster_name = cluster["cluster_name"]
                exist_cluster.append({"cluster_id": cluster_id, "cluster_name": cluster_name, "node_list": node_list,
                                      "instance_list": instance_list})
                # cluster_manager.createCluster(cluster_name = name , cluster_id = cluster_id)
                # cluster_manager.addNode(cluster_id, node_list)
            logging.info("Hass AccessDB - Read data success")
            return exist_cluster

        except MySQLdb.Error, e:
            self.closeDB()
            logging.error("Hass AccessDB - Read data failed (MySQL Error: %s)", str(e))
            print "MySQL Error: %s" % str(e)
            sys.exit(1)

    def syncToDB(self, cluster_list):
        self.checkDB()
        self.resetAll()
        try:
            # cluster_list = cluster_manager.getClusterList()
            for cluster_id, cluster in cluster_list.items():
                # sync cluster
                data = {"cluster_uuid": cluster_id, "cluster_name": cluster.name}
                self.writeDB("ha_cluster", data)
                # sync node
                node_list = cluster.getNodeList()
                for node in node_list:
                    data = {"node_name": node.name, "below_cluster": node.cluster_id, "detection_list": node.getAllDetectionStr()}
                    self.writeDB("ha_node", data)
                # sync instance
                instance_list = cluster.getProtectedInstanceList()
                for instance in instance_list:
                    data = {"instance_id": instance.id, "below_cluster": cluster_id, "host": instance.host,
                            "status": instance.status, "network": str(instance.network)}
                    self.writeDB("ha_instance", data)

        except MySQLdb.Error, e:
            self.closeDB()
            logging.error("Hass database manager - sync data failed (MySQL Error: %s)", str(e))
            print "MySQL Error: %s" % str(e)
            sys.exit(1)

    def writeDB(self, dbName, data):
        self.checkDB()
        if dbName == "ha_cluster":
            format = "INSERT INTO ha_cluster (cluster_uuid,cluster_name) VALUES (%(cluster_uuid)s, %(cluster_name)s);"
        elif dbName == "ha_node":
            format = "INSERT INTO ha_node (node_name,below_cluster,detection_list) VALUES (%(node_name)s, %(below_cluster)s, %(detection_list)s);"
        elif dbName == "ha_instance":
            format = "INSERT INTO ha_instance (instance_id, below_cluster, host, status, network) VALUES (%(instance_id)s, %(below_cluster)s, %(host)s, %(status)s, %(network)s);"
        try:
            self.db.execute(format, data)
            self.db_conn.commit()
        except Exception as e:
            logging.error("Hass AccessDB - write data to DB Failed (MySQL Error: %s)", str(e))
            print "MySQL Error: %s" % str(e)
            raise

    def _getAllTable(self):
        self.checkDB()
        table_list = []
        cmd = "show tables"
        self.db.execute(cmd)
        res = self.db.fetchall()  # ({'Tables_in_hass': 'talbe1'}, {'Tables_in_hass': 'table2'})
        index = "Tables_in_%s" % self.config.get("mysql", "mysql_db")
        for table in res:
            table_list.append(table[index])
        return table_list

    def resetAll(self):
        self.checkDB()
        table_list = self._getAllTable()
        for table in table_list:
            self._resetTable(table)

    def _resetTable(self, table_name):
        self.checkDB()
        cmd = " DELETE FROM  `%s` WHERE true" % table_name
        self.db.execute(cmd)
        self.db_conn.commit()

    def closeDB(self):
        self.checkDB()
        self.db.close()
        self.db_conn.close()


class IIIDatabaseManager(object):
    def __init__(self):
        self.config = ConfigParser.RawConfigParser()
        self.config.read('/home/localadmin/HASS/hass.conf')
        self.db_conn = None
        self.db = None
        try:
            self.connect()
        except MySQLdb.Error, e:
            logging.error("Hass AccessDB(III) - connect to database failed (MySQL Error: %s)", str(e))
            print "MySQL Error: %s" % str(e)
            sys.exit(1)

    def connect(self):
        self.db_conn = MySQLdb.connect(host=self.config.get("iii", "mysql_ip"),
                                       user=self.config.get("iii", "mysql_username"),
                                       passwd=self.config.get("iii", "mysql_password"),
                                       db=self.config.get("iii", "mysql_db"),
                                       )
        self.db = self.db_conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)

    def updateInstance(self, instance_id, node, prev_node):
        self.checkDB()
        prev_compute_num = self._getComputeNum(prev_node)
        compute_num = self._getComputeNum(node)
        instance_resource_id = self.getInstanceResourceID(instance_id)

        if not instance_resource_id:
            print "%s not a iii VM, don't need to modify the database!" % instance_id
            logging.info("%s not a iii VM, don't need to modify the database!" % instance_id)
            return

        self.db.execute("""
            UPDATE `Resource_Relationship`
            SET `parent` =%s
            WHERE `child`=%s
            AND `parent`= %s
            """, (compute_num, instance_resource_id, prev_compute_num))
        self.db_conn.commit()

    def getInstanceResourceID(self, instance_id):
        self.checkDB()
        self.db.execute("SELECT * FROM `Resource` WHERE `OID`= '%s' AND `type`=1" % instance_id)
        data = self.db.fetchall()
        if len(data) == 0: return None
        return str(data[0]["id"])

    def _getComputeNum(self, node):
        self.db.execute("SELECT * FROM `Resource` WHERE `name`= '%s'" % node)
        data = self.db.fetchall()
        return str(data[0]["id"])

    def checkDB(self):
        try:
            self.db_conn.ping()
        except Exception as e:
            logging.info("MYSQL CONNECTION REESTABLISHED!")
            self.connect()


if __name__ == "__main__":
    a = IIIDatabaseManager()
    print a.getInstanceResourceID("806df263-a6e6-4e44-a8b6-79c5548ce33c")
