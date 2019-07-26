import os
import sys
import time


def main():
    print "reboot after 200 seconds"
    time.sleep(float(200))
    os.system("sudo reboot")


if __name__ == "__main__":
    main()
