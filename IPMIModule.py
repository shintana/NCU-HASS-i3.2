#!/usr/bin/python
# -*- coding: utf-8 -*-

#########################################################
#:Date: 2017/12/13
#:Version: 1
#:Authors:
#    - Elma Huang <huanghuei0206@gmail.com>
#    - LSC <sclee@g.ncu.edu.tw>
#:Python_Version: 2.7
#:Platform: Unix
#:Description:
#   This is a class maintains IPMI command operation.
##########################################################

import ConfigParser
import json
import logging
import re
import subprocess
import time

import IPMIConf
from Response import Response


class IPMIManager(object):
    def __init__(self):
        self.config = ConfigParser.RawConfigParser()
        self.config.read('/home/localadmin/HASS/hass.conf')
        self.ip_dict = dict(self.config._sections['ipmi'])
        self.user_dict = dict(self.config._sections['ipmi_user'])
        self.vendor = self.config.get("ipmi", "vendor")
        self.TEMP_LOWER_CRITICAL = 10
        self.TEMP_UPPER_CRITICAL = 80

    def rebootNode(self, node_name):
        code = ""
        message = ""
        base = self._baseCMDGenerate(node_name)
        if base is None:
            raise Exception("ipmi node not found , node_name : %s" % node_name)
        try:
            command = base + IPMIConf.REBOOTNODE
            response = subprocess.check_output(command, shell=True)
            if IPMIConf.REBOOTNODE_SUCCESS_MSG in response:
                message = "The Computing Node %s is rebooted." % node_name
                logging.info("IpmiModule rebootNode - The Computing Node %s is rebooted." % node_name)
                # code = "0"
                code = "succeed"
        except Exception as e:
            message = "The Computing Node %s can not be rebooted." % node_name
            logging.error("IpmiModule rebootNode - %s" % e)
            # code = "1"
            code = "failed"
        finally:
            # result = {"code":code, "node":node_name, "message":message}
            result = Response(code=code,
                              message=message,
                              data={"node": node_name})
            return result

    def startNode(self, node_name):
        code = ""
        message = ""
        base = self._baseCMDGenerate(node_name)
        if base is None:
            raise Exception("ipmi node not found , node_name : %s" % node_name)
        try:
            command = base + IPMIConf.STARTNODE
            response = subprocess.check_output(command, shell=True)
            if IPMIConf.STARTNODE_SUCCESS_MSG in response:
                message = "The Computing Node %s is started." % node_name
                logging.info("IpmiModule startNode - The Computing Node %s is started." % node_name)
                # code = "0"
                code = "succeed"
        except Exception as e:
            message = "The Computing Node %s can not be started." % node_name
            logging.error("IpmiModule startNode - %s" % e)
            # code = "1"
            code = "failed"
        finally:
            # result = {"code":code, "node":node_name, "message":message}
            result = Response(code=code,
                              message=message,
                              data={"node": node_name})
            return result

    def shutOffNode(self, node_name):
        code = ""
        message = ""
        base = self._baseCMDGenerate(node_name)
        if base is None:
            raise Exception("ipmi node not found , node_name : %s" % node_name)
        try:
            command = base + IPMIConf.SHUTOFFNODE
            response = subprocess.check_output(command, shell=True)
            if IPMIConf.SHUTOFFNODE_SUCCESS_MSG in response:
                message = "The Computing Node %s is shut down." % node_name
                logging.info("IpmiModule shutOffNode - The Computing Node %s is shut down." % node_name)
                # code = "0"
                code = "succeed"
        except Exception as e:
            message = "The Computing Node %s can not be shut down." % node_name
            logging.error("IpmiModule shutOffNode - %s" % e)
            # code = "1"
            code = "failed"
        finally:
            # result = {"code":code, "node":node_name, "message":message}
            result = Response(code=code,
                              message=message,
                              data={"node": node_name})
            return result

    def getTempInfoByNode(self, node_name, sensor_type):
        code = ""
        message = ""
        dataList = []
        base = self._baseCMDGenerate(node_name)
        if base is None:
            raise Exception("ipmi node not found , node_name : %s" % node_name)
        try:
            command = base + IPMIConf.NODEINFO_BY_TYPE % sensor_type
            p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            response, err = p.communicate()
            response = response.split("\n")
            dataList = self.dataClean(response, "temperature")
            return int(dataList[2])  # temperature
        except Exception as e:
            message = "Error! Unable to get computing node : %s's hardware information." % node_name
            logging.error("IpmiModule getNodeInfo - %s, %s" % (message, e))
            return "Error"

    def dataClean(self, raw_data, type=None):
        if type == "temperature":
            return self._tempDataClean(raw_data)
        sensor_id = raw_data[1].split(":")[1].strip()
        device = raw_data[2].split(":")[1].strip()
        if device == "7.1":
            device = "System Board"
        elif device == "3.1":
            device = "Processor"
        sensor_type = raw_data[3].split(":")[1].strip()
        value = raw_data[4].split(":")[1].strip()
        status = raw_data[5].split(":")[1].strip()
        lower_critical = raw_data[7].split(":")[1].strip()
        lower = raw_data[8].split(":")[1].strip()
        upper = raw_data[9].split(":")[1].strip()
        upper_critical = raw_data[10].split(":")[1].strip()

        return [sensor_id, device, sensor_type, value, status, lower_critical, lower, upper, upper_critical]

    def _tempDataClean(self, raw_data):

        # data format:
        # Locating sensor record...
        # Sensor ID              : 02-CPU 1 (0x4)
        # Entity ID             : 65.1 (Processor)
        # Sensor Type (Threshold)  : Temperature (0x01)
        # Sensor Reading        : 40 (+/- 0) degrees C
        # Status                : ok
        # Positive Hysteresis   : Unspecified
        # Negative Hysteresis   : Unspecified
        # Minimum sensor range  : 110.000
        # Maximum sensor range  : Unspecified
        # Event Message Control : Global Disable Only
        # Readable Thresholds   : ucr 
        # Settable Thresholds   : 
        # Threshold Read Mask   : ucr 
        # Assertions Enabled    : ucr+ 

        sensor_id = raw_data[1].split(":")[1].strip()
        device = raw_data[2].split(":")[1].strip()
        value = raw_data[4].split(":")[1]
        value = re.findall("[0-9]+", value)[0].strip()  # use regular expression to filt
        return [sensor_id, device, value]

    def getNodeInfoByType(self, node_name, sensor_type_list):
        code = ""
        message = ""
        result_list = []
        base = self._baseCMDGenerate(node_name)
        if base is None:
            raise Exception("ipmi node not found , node_name : %s" % node_name)
        for sensor_type in sensor_type_list:
            command = base + IPMIConf.NODEINFO_BY_TYPE % sensor_type
            print command
            try:
                p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                response, err = p.communicate()
                response = response.split("\n")
                # data clean
                sensor_data = self.dataClean(response)
                result_list.append(sensor_data)
                # code = "0"
                code = "succeed"
                message = message + "Successfully get computing node : %s's %s information." % (
                    node_name, sensor_type_list)
                logging.info("IpmiModule getNodeInfo - " + message)
            except Exception as e:
                message = message + "Error! Unable to get computing node : %s's %s information." % (
                    node_name, sensor_type_list)
                logging.error("IpmiModule getNodeInfo - %s" % e)
                # code = "1"
                code = "failed"
        print result_list
        # result = {"code":code, "info":result_list,"message":message}
        result = Response(code=code,
                          message=message,
                          data={"info": result_list})
        return result

    def getAllInfoByNode(self, node_name):
        AllTemp = ["Temp", "Inlet Temp", "Fan1", "Fan2"]
        try:
            result = self.getNodeInfoByType(node_name, AllTemp)
            logging.info("IPMIModule--getAllInfoMoudle finish %s" % result.message)
            return result
        except Exception as e:
            logging.error("IPMIModule--getAllInfoNode fail" + str(e))

    def getOSStatus(self, node_name):
        interval = (IPMIConf.WATCHDOG_THRESHOLD / 2)
        prev_initial = None
        prev_present = None
        for _ in range(3):
            initial = self._getOSValue(node_name, IPMIConf.OS_TYPE_INITIAL)
            present = self._getOSValue(node_name, IPMIConf.OS_TYPE_PRESENT)
            if initial == False or present == False:
                return "Error"
            if (initial - present) > IPMIConf.WATCHDOG_THRESHOLD:
                return "Error"
            if prev_initial != initial:
                prev_initial = initial
                prev_present = present
                time.sleep(float(interval))
                continue
            if (prev_present - present) < interval:
                return "OK"
            prev_present = present
            time.sleep(float(interval))
        return "Error"

    def _getOSValue(self, node_name, value_type):
        base = self._baseCMDGenerate(node_name)
        if base is None:
            raise Exception("ipmi node not found , node_name : %s" % node_name)
        command = base + IPMIConf.GET_OS_STATUS
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        response = p.wait()
        if response != 0:
            raise Exception("Error! The subprocess's command is invalid.")
        while True:
            info = p.stdout.readline()
            if "Stopped" in info:
                return False
            if not info:
                break
            if value_type in info:
                return int(re.findall("[0-9]+", info)[0])  # find value

    def getSensorStatus(self, node_name):
        ipmi_watched_sensor_list = json.loads(self.config.get("ipmi_sensor", "ipmi_watched_sensors"))
        upper_critical = int(self.config.get("ipmi_sensor", "upper_critical"))
        lower_critical = int(self.config.get("ipmi_sensor", "lower_critical"))
        try:
            for sensor in ipmi_watched_sensor_list:
                value = self.getTempInfoByNode(node_name, sensor)
                if value == "Error" and self.getPowerStatus(node_name) != "OK":
                    return "OK"
                if value > upper_critical or value < lower_critical:
                    return "Error"
            return "OK"
        except Exception as e:
            logging.error("IPMIModule-- getSensorStatus fail : %s" % str(e))

    def resetWatchDog(self, node_name):
        status = True
        base = self._baseCMDGenerate(node_name)
        if base is None:
            # result = {"code" : 1}
            result = Response(code="failed")
            return result
        try:
            command = base + IPMIConf.RESET_WATCHDOG
            response = subprocess.check_output(command, shell=True)
            if IPMIConf.WATCHDOG_RESET_SUCEESS_MSG in response:
                logging.info(
                    "IpmiModule resetWatchDog - The Computing Node %s's watchdog timer has been reset." % node_name)
        except Exception as e:
            logging.error("IpmiModule resetWatchDog - %s" % e)
            status = False
        return status

    def getPowerStatus(self, node_name):
        status = "OK"
        base = self._baseCMDGenerate(node_name)
        if base is None:
            raise Exception("node not found , node_name : %s" % node_name)
        try:
            command = base + IPMIConf.POWER_STATUS
            response = subprocess.check_output(command, shell=True)
            if IPMIConf.POWER_STATUS_SUCCESS_MSG not in response:
                status = "Error"
                # return status
        except Exception as e:
            logging.error(
                "IpmiModule getPowerStatus - The Compute Node %s's IPMI session can not be established. %s" % (
                    node_name, e))
            status = "IPMI_disable"
        finally:
            return status

    def _baseCMDGenerate(self, node_name):
        if node_name in self.user_dict:
            user = self.user_dict[node_name].split(",")[0]
            passwd = self.user_dict[node_name].split(",")[1]
            cmd = IPMIConf.BASE_CMD % (self.ip_dict[node_name], user, passwd)
            return cmd
        else:
            return None

    def _getIPMIStatus(self, node_name):
        return node_name in self.ip_dict


if __name__ == "__main__":
    i = IPMIManager()
    # print i.getOSStatus("compute2")
    print i.getSensorStatus("compute1")


    # def getOSStatus(self, node_name):
    #     status = "OK"
    #     time.sleep(float(IPMIConf.WATCHDOG_THRESHOLD)) # wait watchdog countdown
    #     try:
    #         initial = self._getOSValue(node_name, IPMIConf.OS_TYPE_INITIAL)
    #         present = self._getOSValue(node_name, IPMIConf.OS_TYPE_PRESENT)
    #     except Exception as e:
    #         logging.error("IpmiModule detectOSstatus - %s" % e)
    #         status = "IPMI_disable"
    #         return status
    #     if (initial - present) > IPMIConf.WATCHDOG_THRESHOLD:
    #         #print initial - present
    #         status = "Error"
    #         return status
    #     else:
    #         return status
