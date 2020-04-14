import logging
import math
import os
import sys
import threading
import time

from objs.frame import Frame
from objs.metadata import Metadata
from objs.packet import Packet
from objs.ack import Ack
from delta_list.delta_list import DeltaList

from socket import *
from typing import List

MAX_PKT_SIZE = 1024
MAX_DATA_SIZE = MAX_PKT_SIZE - 4 * 4
SLEEP_TIME = .016  # equivalent to 60 fps
PATH_TO_FRAMES = "./assets/road480p/"
RETR_TIME = 5
RETR_INTERVAL = 1


def create_packets(frame_no: int, data_arr: List[str]) -> List[Packet]:
    packet_no = 0
    packets: List[Packet] = []
    for data in data_arr:
        packets.append(Packet(frame_no, packet_no, len(data_arr), len(data), data))
        packet_no += 1
    return packets


def to_data_arr(frame: Frame, max_data_size: int) -> List[str]:
    data = frame.data
    number_of_packets = math.ceil(len(data) / max_data_size)
    packet_data = [None] * number_of_packets
    for i in range(0, number_of_packets):
        if (i + 1) * max_data_size < len(data):
            packet_data[i] = data[i * max_data_size: (i + 1) * max_data_size]
        else:
            packet_data[i] = data[i * max_data_size:]
    return packet_data


# def send_frame(frame: Frame, frame_no: int, con_socket):
#     data_arr: List[str] = to_data_arr(frame, MAX_DATA_SIZE)
#     packets: List[Packet] = create_packets(frame_no, data_arr)
#     for p in packets:
#         data = p.pack()
#         con_socket.send(data)


def server_handler(con_socket, ad, path_to_frames, starting_frame, total_frames):
    logging.info("Handler Started")
    frame_no = starting_frame
    meta_data = Metadata(file_name=path_to_frames, number_of_frames=total_frames)
    frames = {}
    critical_frame_acks = {}
    frame_retr_times: DeltaList[int] = DeltaList()

    def reader() -> None:
        while True:
            msg_from = con_socket.recv(1024)
            if len(msg_from) == 0:
                continue
            a: Ack = Ack.unpack(msg_from)
            critical_frame_acks[a.frame_no] = True
            logging.info("ACK {}".format(a.frame_no))
        logging.info("Reader Finished")

    def retransmitter() -> None:
        logging.info("Reader Started")
        while True:
            frame_retr_times.decrement_key()
            ready_frames: List[int] = frame_retr_times.remove_all_ready()
            for i in ready_frames:
                logging.info("Retransmitting frame {}".format(i))
                # change to method later
                arr: List[str] = to_data_arr(frames[i], MAX_DATA_SIZE)
                pkts: List[Packet] = create_packets(i, arr)
                for pa in pkts:
                    dt = p.pack()
                    if pa in critical_frame_acks and critical_frame_acks[pa] is False:
                        con_socket.send(dt)

            time.sleep(RETR_INTERVAL)
        logging.info("Retransmitter Finished")

    reader_thread = threading.Thread(target=reader, args=())
    retransmitter_thread = threading.Thread(target=retransmitter, args=())
    reader_thread.start()
    retransmitter_thread.start()

    con_socket.send(meta_data.pack())
    time.sleep(SLEEP_TIME)
    while frame_no < total_frames:  # 1 for now, change to frames later
        frame_no += 1
        f = open("{}{}.h264".format(path_to_frames, frame_no), "rb")

        frame = Frame(f.read())
        frames[frame_no] = frame
        if frame.priority == Frame.Priority.CRITICAL: # add support for >= later
            critical_frame_acks[frame_no] = False
            frame_retr_times.insert(k=RETR_TIME, e=frame_no)

        # send_frame(frame, frame_no, con_socket)
        data_arr: List[str] = to_data_arr(frame, MAX_DATA_SIZE)
        packets: List[Packet] = create_packets(frame_no, data_arr)
        for p in packets:
            data = p.pack()
            con_socket.send(data)

        time.sleep(SLEEP_TIME)  # sleep
        logging.info("Sent Frame #: {}".format(frame_no))
    con_socket.close()
    logging.info("Handler Finished")
    reader_thread.join()
    retransmitter_thread.join()


usage = "usage: python " + sys.argv[0] + " [portno]"


def main():
    server_port = sys.argv[1]
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server_socket.bind(('', int(server_port)))
    server_socket.listen(8)
    path = "./assets/road480p/"
    number_of_frames = len(os.listdir(path)) - 1 # - 1 needed?
    while True:
        connection_socket, addr = server_socket.accept()
        threading.Thread(target=server_handler, args=(connection_socket, addr, path, 0, number_of_frames)).start()
    server_socket.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(usage)
        exit(1)
    logging.basicConfig(filename='server.log', level=logging.INFO)
    main()
