import sys
import xmlrpclib
import time
from HostFailures import HostFailures
from InstanceFailures import InstanceFailure


class DetectionAgent():
    def __init__(self):
        pass

def main():
    host_detection = HostFailures()
    host_detection.daemon = True
    host_detection.start()
    instance_detection = InstanceFailure()
    instance_detection.daemon = True
    instance_detection.start()
    try:
        while True:
            pass
    except:
        sys.exit(1)


if __name__ == "__main__":
    main()
