import util

# Your program should send TTLs in the range [1, TRACEROUTE_MAX_TTL] inclusive.
# Technically IPv4 supports TTLs up to 255, but in practice this is excessive.
# Most traceroute implementations cap at approximately 30.  The unit tests
# assume you don't change this number.
TRACEROUTE_MAX_TTL = 30

# Cisco seems to have standardized on UDP ports [33434, 33464] for traceroute.
# While not a formal standard, it appears that some routers on the internet
# will only respond with time exceeeded ICMP messages to UDP packets send to
# those ports.  Ultimately, you can choose whatever port you like, but that
# range seems to give more interesting results.
TRACEROUTE_PORT_NUMBER = 33434  # Cisco traceroute port number.

# Sometimes packets on the internet get dropped.  PROBE_ATTEMPT_COUNT is the
# maximum number of times your traceroute function should attempt to probe a
# single router before giving up and moving on.
PROBE_ATTEMPT_COUNT = 3


class IPv4:
    # Each member below is a field from the IPv4 packet header.  They are
    # listed below in the order they appear in the packet.  All fields should
    # be stored in host byte order.
    #
    # You should only modify the __init__() method of this class.
    version: int
    header_len: int  # Note length in bytes, not the value in the packet.
    tos: int  # Also called DSCP and ECN bits (i.e. on wikipedia).
    length: int  # Total length of the packet.
    id: int
    flags: int
    frag_offset: int
    ttl: int
    proto: int
    cksum: int
    src: str
    dst: str

    def __init__(self, buffer: bytes):
        first_byte = format(buffer[0], '08b')
        self.version = int(first_byte[:4], 2)
        self.header_len = int(first_byte[4: 8], 2) * 4
        self.tos = int((format(buffer[1], '08b')), 2)
        self.length = int(''.join(format(byte, '08b') for byte in buffer[2:4]), 2)
        self.id = int(''.join(format(byte, '08b') for byte in buffer[4:6]), 2)
        seventh_byte = format(buffer[6], '08b')
        self.flags = int(seventh_byte[0:3], 2)
        self.frag_offset = int(seventh_byte[3:16], 2)
        self.ttl = int(format(buffer[8], '08b'), 2)
        self.proto = int(format(buffer[9], '08b'), 2)
        self.cksum = int(''.join(format(byte, '08b') for byte in buffer[10: 12]), 2)
        self.src = '.'.join(str(byte) for byte in buffer[12: 16])
        self.dst = '.'.join(str(byte) for byte in buffer[16: 20])

    def __str__(self) -> str:
        return f"IPv{self.version} (tos 0x{self.tos:x}, ttl {self.ttl}, " + \
            f"id {self.id}, flags 0x{self.flags:x}, " + \
            f"offset {self.frag_offset}, " + \
            f"proto {self.proto}, header_len {self.header_len}, " + \
            f"len {self.length}, cksum 0x{self.cksum:x}) " + \
            f"{self.src} > {self.dst}"


class ICMP:
    # Each member below is a field from the ICMP header.  They are listed below
    # in the order they appear in the packet.  All fields should be stored in
    # host byte order.
    #
    # You should only modify the __init__() function of this class.
    type: int # 0 for ping response, 11 for traceroute
    code: int # together with type, show additional information, 0 means TTL expired in transit
    cksum: int

    def __init__(self, buffer: bytes):
        """

        Args:
            buffer: icmp header(without ethernet header)
        """
        assert len(buffer) == 8  # should be 8 bytes in total
        bit_string = ''.join(format(byte, '08b') for byte in [*buffer])
        self.type = int(bit_string[: 8], 2)
        self.code = int(bit_string[8: 16], 2)
        self.cksum = int(bit_string[16: 32], 2)

    def __str__(self) -> str:
        return f"ICMP (type {self.type}, code {self.code}, " + \
            f"cksum 0x{self.cksum:x})"


class UDP:
    # Each member below is a field from the UDP header.  They are listed below
    # in the order they appear in the packet.  All fields should be stored in
    # host byte order.
    #
    # You should only modify the __init__() function of this class.
    src_port: int
    dst_port: int
    len: int
    cksum: int

    def __init__(self, buffer: bytes):
        """

        Args:
            buffer: The header(without ethernet header)
        """
        assert len(buffer) == 8  # should be 8 bytes in total
        bit_string = ''.join(format(byte, '08b') for byte in [*buffer])
        self.src_port = int(bit_string[: 16], 2)
        self.dst_port = int(bit_string[16: 32], 2)
        self.len = int(bit_string[32: 48], 2)
        self.cksum = int(bit_string[48: 64], 2)

    def __str__(self) -> str:
        return f"UDP (src_port {self.src_port}, dst_port {self.dst_port}, " + \
            f"len {self.len}, cksum 0x{self.cksum:x})"

def traceroute(sendsock: util.Socket, recvsock: util.Socket, ip: str) \
        -> list[list[str]]:
    """ Run traceroute and returns the discovered path.

    Calls util.print_result() on the result of each TTL's probes to show
    progress.

    Arguments:
    sendsock -- This is a UDP socket you will use to send traceroute probes.
    recvsock -- This is the socket on which you will receive ICMP responses.
    ip -- This is the IP address of the end host you will be tracerouting.

    Returns:
    A list of lists representing the routers discovered for each ttl that was
    probed.  The ith list contains all of the routers found with TTL probe of
    i+1.   The routers discovered in the ith list can be in any order.  If no
    routers were found, the ith list can be empty.  If `ip` is discovered, it
    should be included as the final element in the list.
    """

    # TODO Add your implementation
    res = []
    routers_ttl = []
    routers_ttl_set = set()
    for ttl in range(1, TRACEROUTE_MAX_TTL+1):
        sendsock.set_ttl(ttl)
        # For stability, for each ttl, send multiple packets to compensate for the possible packet loss
        for _ in range(PROBE_ATTEMPT_COUNT):
            sendsock.sendto("Potato".encode(), (ip, TRACEROUTE_PORT_NUMBER))

            if recvsock.recv_select():
                buf, address = recvsock.recvfrom()
                # Convert the received packet header to corresponding class
                ip_header = IPv4(buf)
                curr_router_src = ip_header.src
                if curr_router_src not in routers_ttl_set:
                    routers_ttl_set.add(curr_router_src)
                    routers_ttl.append(curr_router_src)


            # outer_ip_len = int(''.join(format(buf[0], '08b'))[4:8], 2) * 4
            # icmp_header_buf = buf[outer_ip_len: outer_ip_len + 8]
            #
            # print(ICMP(icmp_header_buf))
            #
            # inner_ip_len = int(''.join(format(byte, '08b') for byte in buf[outer_ip_len + 8:])[4:8],2) * 4
            # udp_header_buf = buf[outer_ip_len + 8 + inner_ip_len: outer_ip_len + 8 + inner_ip_len + 8]
            # print(UDP(udp_header_buf))

        util.print_result(routers_ttl[:ttl], ttl)
        res.append(routers_ttl[:ttl])

    return res

if __name__ == '__main__':
    args = util.parse_args()
    ip_addr = util.gethostbyname(args.host)
    print(ip_addr)
    print(f"traceroute to {args.host} ({ip_addr})")
    traceroute(util.Socket.make_udp(), util.Socket.make_icmp(), ip_addr)
