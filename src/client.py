import struct
import sys
from objs.frame import Frame
from objs.packet import Packet
from socket import *
from typing import List

MAX_PKT_SIZE = 1024
MAX_DATA_SIZE = MAX_PKT_SIZE - 4 * 4

usage = "usage: python " + sys.argv[0] + " [serverIP] " + " [serverPort]"
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(usage)
        exit(1)

serverIP = sys.argv[1]
serverPort = sys.argv[2]

clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((serverIP, int(serverPort)))
frame_no = 0
buffer = ""
frame_to_save = open("./temp/frame_{}.jpeg".format(frame_no), "wb+")
while True:
    frame_no += 1
    msg_from = clientSocket.recv(1024)
    if len(msg_from) == 0:
        break
    t = struct.unpack("!IIII{}s".format(len(msg_from) - 4 * 4), msg_from)
    p: Packet = Packet(t[0], t[1], t[2], t[3], t[4]) # Takes all except for the padding
    frame_to_save.write(t[4])
    if t[1] == t[2]:
        break
frame_to_save.close()
clientSocket.close()
