from __future__ import print_function

import ConfigParser
import logging
import threading
import time
import xmlrpclib
import re

import State
import FailureType
from Detector import Detector
from BuildTree import BuildTree
from TreeNode import TreeNode
from Diagnoser import Diagnoser


class DetectionThread(threading.Thread):
    def __init__(self, cluster_id, node, detection_list, port, polling_interval):
        threading.Thread.__init__(self)
        self.node = node
        self.cluster_id = cluster_id
        self.detection_list = detection_list
        self.clean_detection_list = self.clean_detection()
        self.ipmi_status = node.ipmi_status
        self.polling_interval = polling_interval
        self.loop_exit = False
        self.config = ConfigParser.RawConfigParser()
        self.config.read('hass.conf')
        self.detector = Detector(node, port)
        self.custom_function_map = self.set_function_map()
        self.function_map = [self.detector.checkPowerStatus, self.detector.checkOSStatus,
                             self.detector.checkNetworkStatus, self.detector.checkServiceStatus]
        self.active_layer = self.set_active_layer()
        self.disable_layer = self.set_disable_layer()
        self.authUrl = "http://" + self.config.get("rpc", "rpc_username") + ":" + self.config.get("rpc",
                                                                                                  "rpc_password") + \
                       "@127.0.0.1:" + self.config.get(
            "rpc", "rpc_bind_port")
        self.server = xmlrpclib.ServerProxy(self.authUrl)

    def clean_detection(self):
        cloned_detection_list = self.detection_list[:]
        cloned_detection_list.sort()
        removed_item = ['5', '6', '7']
        if '4' not in cloned_detection_list:
            cloned_detection_list.append('4')
        for i in removed_item:
            if i in cloned_detection_list:
                cloned_detection_list.remove(i)
        if cloned_detection_list == []:
            cloned_detection_list = ['1', '2', '3', '4']
        print('clean detection: %s' % cloned_detection_list)
        return cloned_detection_list

    def set_function_map(self):
        function_map = []
        detector_list = {
            '1': self.detector.checkPowerStatus,
            '2': self.detector.checkOSStatus,
            '3': self.detector.checkNetworkStatus,
            '4': self.detector.checkServiceStatus
        }
        if self.clean_detection_list != []:
            for i in self.clean_detection_list:
                function_map.append(detector_list[i])
        else:
            for i in detector_list:
                function_map.append(detector_list[i])
        return function_map

    def set_active_layer(self):
        active_layer = self.custom_function_map
        print('active layer: %s' % active_layer)
        return active_layer

    def set_disable_layer(self):
        cloned_function_map = self.function_map[:]
        for a in self.active_layer:
            cloned_function_map.remove(a)
        disable_layer = cloned_function_map
        print('disable layer: %s' % disable_layer)
        return disable_layer

    def run(self):
        while not self.loop_exit:
            state = self.detect()
            print("[" + self.node.name + "] " + state)
            if state != State.HEALTH:
                logging.error("[" + self.node.name + "] " + state)
                try:
                    print("try host recovery by start..")
                    recover_success = self.server.recover(State.POWER_FAIL, self.cluster_id, self.node.name)
                    if recover_success:  # recover success
                        print("recover success")
                        self.detector.connect()
                    else:
                        print("try another host recovery by reboot..")
                        recover_second_chance = self.server.recover(State.OS_FAIL, self.cluster_id, self.node.name)
                        if recover_second_chance:  # recover success
                            print("recover success")
                            self.detector.connect()
                        else:
                            # recover fail(False) or get cluster fail(none)
                            print("recover fail delete node %s from the cluster" % self.node.name)
                            self.server.deleteNode(self.cluster_id, self.node.name)
                            self.stop()
                except Exception as e:
                    print("Exception : " + str(e))
                    self.stop()
                self.server.updateDB()
            time.sleep(self.polling_interval)

    def stop(self):
        self.loop_exit = True

    def detect(self):
        highest_level_check = self.function_map[-1]
        max_waiting_detection_time = 30

        if highest_level_check() != FailureType.HEALTH:
            state = self.verify(highest_level_check)
            if state == FailureType.HEALTH:
                return FailureType.HEALTH
            else:
                if state == FailureType.OS_FAIL or state == FailureType.POWER_FAIL:
                    return state
                elif state == FailureType.NETWORK_FAIL or self.detector.checkNetworkStatus in self.disable_layer:
                    timeout = max_waiting_detection_time  # [seconds]
                    timeout_start = time.time()
                    # print('start: %s' % timeout_start)
                    while time.time() < timeout_start + timeout:
                        service_second_chance = self.function_map[-1]()
                        if service_second_chance == State.HEALTH:
                            return State.HEALTH
                        time.sleep(1)
                return state
        return FailureType.HEALTH

    def verify(self, func):
        cloned_function_map = self.active_layer[:-1]  # clone from function map
        reversed_function_map = self._reverse(cloned_function_map)
        print ('verify layer: %s' % reversed_function_map)
        fail = FailureType.SERVICE_FAIL

        for _ in reversed_function_map:
            state = _()
            print('state= %s' % state)
            if state == FailureType.HEALTH and _ == func:
                return FailureType.HEALTH
            elif state == FailureType.HEALTH:
                return fail
            elif not state == FailureType.HEALTH:
                fail = state
        return fail

    def _reverse(self, list):
        list.reverse()
        return list

if __name__ == "__main__":
    config = ConfigParser.RawConfigParser()
    config.read('hass.conf')
    authUrl = "http://" + config.get("rpc", "rpc_username") + ":" + config.get("rpc",
                                                                               "rpc_password") + "@127.0.0.1:" \
              + config.get(
        "rpc", "rpc_bind_port")
    server = xmlrpclib.ServerProxy(authUrl)
    server.test()
