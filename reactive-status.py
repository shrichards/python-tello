import multiprocessing
import threading
import socket
import sys
import time

from rx import Observer, Observable
from rx.concurrency import ThreadPoolScheduler

TELLO_COMMAND_PORT = 8889
TELLO_STATUS_PORT = 8890

TELLO_IP = "192.168.10.1"


class Drone:
    """
    Creates a connection to the Tello drone, and exposes methods
    for observing status updates and stopping updates
    """

    def __init__(self, ip_address, command_port, status_port):
        self._ip_address = ip_address
        self._command_port = command_port
        self._status_port = status_port

        self._command_address = (self._ip_address, self._command_port)

        self._stopper = threading.Event()

        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listen_socket.bind(("", self._status_port))

        # create a socket over which we can send the command
        # that triggers the drone to start generating status messages
        self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.command_socket.bind(("", self._command_port))

    def start(self):
        # the 'command' command causes the tello to start broadcasting its
        # status, and allows it to accept control commands
        self.send_command("command")

    def observe(self, observer):

        while not self._stopper.is_set():
            data, _ = self.listen_socket.recvfrom(4096)
            status = status_to_dict(data.decode("utf-8"))
            observer.on_next(status)

        observer.on_completed()

    def send_command(self, command):
        self.command_socket.sendto(command.encode("utf-8"), self._command_address)

    def stop(self):
        self._stopper.set()
        self.listen_socket.close()
        self.command_socket.close()


def status_to_dict(status_str):
    """
    Helper that converts the semicolon delimited status values to
    a dict
    """
    status = {}
    params = [param.strip() for param in status_str.split(";") if param.strip()]
    for param in params:
        (key, val) = param.split(":")
        status[key] = val
    return status


def listen():
    optimal_thread_count = multiprocessing.cpu_count()
    pool_scheduler = ThreadPoolScheduler(optimal_thread_count)

    drone = Drone(TELLO_IP, TELLO_COMMAND_PORT, TELLO_STATUS_PORT)

    input("press any key to start\n")
    drone.start()
    time.sleep(5.0)
    drone.send_command("takeoff")
    time.sleep(7.0)
    drone.send_command("land")
    input("press any key to stop\n")
    drone.stop()


if __name__ == "__main__":
    listen()

