
import socket
import ConfigParser
import subprocess
import libvirt
import socket
import threading



class HostFailures(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        config = ConfigParser.RawConfigParser()
        config.read('/home/localadmin/HASS/compute_node/hass_node.conf')
        self.host = None
        self.port = int(config.get("polling", "listen_port"))
        self.version = int(config.get("ubuntu_os_version", "version"))
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(('', self.port))
        self.libvirt_uri = "qemu:///system"
        print "host failure port:", self.port

    def run(self):
        while True:
            data, addr = self.s.recvfrom(1024)
            print(data)
            if "polling request" in data:
                check_result = self.check_services()
                if check_result == "":
                    self.s.sendto("OK", addr)
                else:
                    check_result = "error:" + check_result
                    self.s.sendto(check_result, addr)
            if "undefine" in data:
                self.handle_undefine_instance(data, addr)

    def check_services(self):
        message = ""
        # check libvirt
        if not self._checkLibvirt():
            message = "libvirt;"
        # check nova-compute
        if not self._checkNovaCompute():
            message += "nova;"
        if not self._checkQEMUKVM():
            message += "qemukvm;"
        return message

    def _checkLibvirt(self):
        try:
            conn = libvirt.open(self.libvirt_uri)
            if not conn:
                return False
        except Exception as e:
            print str(e)
            return False
        return True

    def _checkNovaCompute(self):
        try:
            output = subprocess.check_output(['ps', '-A'])
            if "nova-compute" not in output:
                return False
        except:
            return False
        return True

    def _checkQEMUKVM(self):
        try:
            output = subprocess.check_output(['service', 'qemu-kvm', 'status'])
            if self.version == 14:
                if "start/running" not in output:
                    return False
            elif self.version == 16:
                if "active" not in output:
                    return False
        except Exception as e:
            print str(e)
            return False
        return True

    def handle_undefine_instance(self, data, addr):
        instance_name = data.split(' ')[1]
        if self.libvirt_contain_instance(instance_name):
            self.undefine_instance(instance_name)
        if not self.libvirt_contain_instance(instance_name):
            self.s.sendto("OK", addr)
        else:
            self.s.sendto("error:undefine %s" % instance_name, addr)

    def libvirt_contain_instance(self, instance_name):
        res = subprocess.check_output(['virsh', 'list', '--all'])
        return (instance_name in res)

    def undefine_instance(self, instance_name):
        res = subprocess.check_output(['virsh', 'destroy', instance_name])
        print res
        res = subprocess.check_output(['virsh', 'undefine', instance_name])
        print res
