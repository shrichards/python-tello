import multiprocessing
import threading
import socket
import sys

from rx import Observer, Observable
from rx.concurrency import ThreadPoolScheduler

TELLO_COMMAND_PORT = 8889
TELLO_STATUS_PORT = 8890

TELLO_IP = "192.168.10.1"


class DroneStatus:
    """
    Creates a connection to the Tello drone, and exposes methods
    for observing status updates and stopping updates
    """

    def __init__(self):
        self._stopper = threading.Event()
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listen_socket.bind(("", TELLO_STATUS_PORT))

        # create a socket over which we can send the command
        # that triggers the drone to start generating status messages
        command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        command_socket.bind(("", TELLO_COMMAND_PORT))
        command_socket.sendto(bytes("command", "utf-8"), (TELLO_IP, TELLO_COMMAND_PORT))

    def observe(self, observer):

        while not self._stopper.is_set():
            data, _ = self.listen_socket.recvfrom(4096)
            status = status_to_dict(data.decode("utf-8"))
            observer.on_next(status)

        observer.on_completed()

    def stop(self):
        self._stopper.set()
        pass


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

    drone_status = DroneStatus()

    source = (
        Observable.create(drone_status.observe)
        .subscribe_on(pool_scheduler)
        .subscribe(
            on_next=lambda i: print(f"Status: {i}"),
            on_error=lambda e: print(f"ERROR: {e}"),
            on_completed=lambda: print("DONE!"),
        )
    )
    input("press any key to Stop\n")
    drone_status.stop()


if __name__ == "__main__":
    listen()

