import argparse
import select
import socket
import typing
import sys
import platform

# === Do Not Modify ===

# SELECT_TIMEOUT indicates how many seconds the select call will block in the
# event that no packets are received.  The smaller the number, the more likely
# our code is to give up and assume a router won't respond even when a packet
# is coming.  The larger the number, the slower our code will be when probing
# unresponsive routers.  In practice, 2 seconds acheives reasonable results.
# The tests don't depend on this number being anything in particular. It only
# impacts real runs.
SELECT_TIMEOUT = 2

IPPROTO_ICMP = socket.IPPROTO_ICMP

IPPROTO_UDP = socket.IPPROTO_UDP


def ntohl(x):
    return socket.ntohl(x)


def htonl(x):
    return socket.htonl(x)


def htons(x):
    return socket.htons(x)


def ntohs(x):
    return socket.ntohs(x)


def inet_aton(x):
    return socket.inet_aton(x)


def inet_ntoa(x):
    return socket.inet_ntoa(x)


def inet_pton(x, y):
    return socket.inet_pton(x, y)


def inet_ntop(x, y):
    return socket.inet_ntop(x, y)


def gethostbyname(host: str):
    return socket.gethostbyname(host)


class Socket:
    __sock: socket.socket

    # Creates a UDP socket used for sending traceroute probes.  The starter
    # code calls this for you.
    @classmethod
    def make_udp(cls):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
                             socket.IPPROTO_UDP)
        return cls(sock)

    # Creates an ICMP socket used for receiving ICMP responses. The starter
    # code calls this for you.
    @classmethod
    def make_icmp(cls):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                                 socket.IPPROTO_ICMP)
        except PermissionError:
            if platform.system() != "Darwin":
                print("PermissionError: please run as root.")
                sys.exit(1)

            # On MacOS, you can create a non-privileged ICMP socket.  The raw
            # socket is preferable as it's less fragile and cross platform, but
            # since that failed, may as well try it.
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
                                 socket.IPPROTO_ICMP)
        return cls(sock)

    def __init__(self, sock: socket.socket):
        self.__sock = sock

    # Only called on the UDP socket.  Changes the TTL on all future packets
    # sent on this socket to the provided value.
    def set_ttl(self, ttl: int):
        """
        Args:
            ttl: time to live, num of hops
        Returns:
        """

        # setsockopt(level, optname, value)
        """
        level: Where are you making changes?
         1. socket.IPPROTO_IP, which means you are making changes specifically to each IP packets
         2. soclet.SOL_SOCKET, which means you are making changes to socket interface itself  like a global setting       
        
        optname: What feature are you changing?
         1. socket.SO_REUSEADDR: 用于热部署, used to reduce downtime.
         2. socket.IP_TTL: Straightforward, time to live for each IP packets.
        
        value: How are you setting it up?
        """
        return self.__sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)

    # Only called on the UDP socket.  Sends a UDP packet to `address`.
    # `address` is a tuple containing a string representation of an IPv4
    # address, and the destination port.   The UDP packet payload is `b`.  The
    # UDP packet header is created by the `sendto` function based on the
    # provided information.
    #
    # See: https://docs.python.org/3/library/socket.html#socket.socket.sendto
    def sendto(self, b: bytes, address: typing.Tuple[str, int]) -> int:
        """
        Args:
            b: payload data to be sent to the end server
            address:  (ip address, port num)
        Returns:
            The number of bytes that are actually sent to the destination address

        """
        return self.__sock.sendto(b, address)

    # Only called on the ICMP socket.  Recieves a packet from the socket.
    # Returns a `bytes` object containing the entirity of the packet
    # (including the IP headers).   Additionally returns the address of the
    # packet's sender.
    #
    # See: https://docs.python.org/3/library/socket.html#socket.socket.recvfrom
    def recvfrom(self) -> typing.Tuple[bytes, typing.Tuple[str, int]]:
        """
        Returns: (bytes, address) where address is (ip, port)
        """
        return self.__sock.recvfrom(4096)

    # Only called on the ICMP socket.  Blocks until this socket has a packet
    # ready to be received by `recvfrom()`, or `SELECT_TIMEOUT` expires.
    # Returns true if packets are available for `recvfrom()`.
    #
    # See: https://docs.python.org/3/library/select.html#select.select
    def recv_select(self) -> bool:
        # 用于查看当前线程的哪一个文件描述符是可以读取的
        rlist, _, _ = select.select([self.__sock], [], [], SELECT_TIMEOUT)
        return rlist != []


def print_result(routers: list[str], ttl: int):
    if len(routers) == 0:
        print(f"{ttl: >2}: *")
        return

    for i, router in enumerate(routers):
        if i == 0:
            preamble = f"{ttl: >2}:"
        else:
            preamble = "   "

        try:
            hostname, _, _ = socket.gethostbyaddr(router)
            print(f"{preamble} {hostname} ({router})")
        except socket.herror:
            print(f"{preamble} {router}")


def parse_args():
    parser = argparse.ArgumentParser(prog='cs168 Traceroute')
    parser.add_argument('host')
    return parser.parse_args()
