import threading
import socket

class recvIPThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.s = socket.socket(socket.AF_INET , socket.SOCK_STREAM)
        self.s.bind(('192.168.0.115',5001))
        self.s.listen(5)

    def run(self):
        while True:
            cs,addr = self.s.accept()
            print "addr:", addr
            #cs.send("fuck")
            d = cs.recv(1024)
            print d
