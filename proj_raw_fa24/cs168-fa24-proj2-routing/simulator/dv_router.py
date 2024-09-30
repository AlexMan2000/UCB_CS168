"""
Your awesome Distance Vector router for CS 168

Based on skeleton code by:
  MurphyMc, zhangwen0411, lab352
"""

import sim.api as api
from cs168.dv import (
    RoutePacket,
    Table,
    TableEntry,
    DVRouterBase,
    Ports,
    FOREVER,
    INFINITY,
)


class DVRouter(DVRouterBase):

    # A route should time out after this interval
    ROUTE_TTL = 15

    # -----------------------------------------------
    # At most one of these should ever be on at once
    SPLIT_HORIZON = False
    POISON_REVERSE = False
    # -----------------------------------------------

    # Determines if you send poison for expired routes
    POISON_EXPIRED = False

    # Determines if you send updates when a link comes up
    SEND_ON_LINK_UP = False

    # Determines if you send poison when a link goes down
    POISON_ON_LINK_DOWN = False

    def __init__(self):
        """
        Called when the instance is initialized.
        DO NOT remove any existing code from this method.
        However, feel free to add to it for memory purposes in the final stage!
        """
        assert not (
            self.SPLIT_HORIZON and self.POISON_REVERSE
        ), "Split horizon and poison reverse can't both be on"

        self.start_timer()  # Starts signaling the timer at correct rate.

        # Contains all current ports and their latencies.
        # See the write-up for documentation.
        self.ports = Ports()

        # This is the table that contains all current routes
        self.table = Table()
        self.table.owner = self

        ##### Begin Stage 10A #####

        ##### End Stage 10A #####

    def add_static_route(self, host, port):
        """
        Adds a static route to this router's table.

        Called automatically by the framework whenever a host is connected
        to this router.

        :param host: the host.
        :param port: the port that the host is attached to.
        :returns: nothing.
        """
        # `port` should have been added to `peer_tables` by `handle_link_up`
        # when the link came up.
        assert port in self.ports.get_all_ports(), "Link should be up, but is not."

        ##### Begin Stage 1 #####
        self.table[host] = TableEntry(dst=host, port=port, latency=self.ports.get_latency(port), expire_time=api.current_time() + FOREVER)
        ##### End Stage 1 #####

    def handle_data_packet(self, packet, in_port):
        """
        Called when a data packet arrives at this router.

        You may want to forward the packet, drop the packet, etc. here.

        :param packet: the packet that arrived.
        :param in_port: the port from which the packet arrived.
        :return: nothing.
        """
        
        ##### Begin Stage 2 #####
        if packet.dst not in self.table:
            # Table doesn't contain the route to the dst host
            return
        table_entry = self.table[packet.dst]
        if table_entry.latency >= INFINITY:
            # Cannot reach the destination host, so don't send
            return
        self.send(packet, port=table_entry.port)
        ##### End Stage 2 #####

    def send_routes(self, force=False, single_port=None):
        """
        Send route advertisements for all routes in the table.

        :param force: if True, advertises ALL routes in the table;
                      otherwise, advertises only those routes that have
                      changed since the last advertisement.
               single_port: if not None, sends updates only to that port; to
                            be used in conjunction with handle_link_up.
        :return: nothing.
        """
        if self.SPLIT_HORIZON and self.POISON_REVERSE:
            raise RuntimeError("Cannot set SPLIT_HORIZON and POISON_REVERSE to be True at the same time!")
        
        ##### Begin Stages 3, 6, 7, 8, 10 #####
        for route_dst, table_entry in self.table.items():
            for port in self.ports.get_all_ports():
                if self.SPLIT_HORIZON:
                    if port != table_entry.port:
                        # 当前端口是不是下家，是的话就不发
                        self.send_route(port, route_dst, INFINITY if table_entry.latency >=INFINITY else table_entry.latency)
                elif self.POISON_REVERSE:
                    if port == table_entry.port:
                        self.send_route(port, route_dst, INFINITY)
                    else:
                        self.send_route(port, route_dst, INFINITY if table_entry.latency >=INFINITY else table_entry.latency)
                else:
                    self.send_route(port, route_dst, INFINITY if table_entry.latency >=INFINITY else table_entry.latency)
        ##### End Stages 3, 6, 7, 8, 10 #####

    def expire_routes(self):
        """
        Clears out expired routes from table.
        accordingly.
        """
        
        ##### Begin Stages 5, 9 #####
        should_expire_key = []
        for route_dst, table_entry in self.table.items():
            if api.current_time() >= table_entry.expire_time:
                self.s_log(f"Router {self.table.owner}'s entry of {route_dst} has expired!")
                should_expire_key.append(route_dst)
        for route_dst in should_expire_key:
            if self.POISON_EXPIRED:
                port = self.table[route_dst].port
                self.table[route_dst] = TableEntry(dst=route_dst, port=port, latency=INFINITY, expire_time=api.current_time()+self.ROUTE_TTL)
            else:
                self.table.pop(route_dst)
        ##### End Stages 5, 9 #####

    def handle_route_advertisement(self, route_dst, route_latency, port):
        """
        Called when the router receives a route advertisement from a neighbor.

        :param route_dst: the destination of the advertised route.
        :param route_latency: latency from the neighbor to the destination.
        :param port: the port that the advertisement arrived on.
        :return: nothing.
        """
        
        ##### Begin Stages 4, 10 #####
        # Entry doesn't exist
        if route_dst not in self.table:
            init_latency = self.ports.get_latency(port) + route_latency
            self.table[route_dst] = TableEntry(
                dst=route_dst,
                port=port,
                latency=init_latency,
                expire_time=api.current_time()+self.ROUTE_TTL)
        next_hop_info = self.table[route_dst]
        next_hop_port = next_hop_info.port
        # Rule 2: Update from next-hop
        if port == next_hop_port:
            self.table[route_dst] = TableEntry(
                dst=route_dst,
                port=next_hop_port,
                latency=route_latency + self.ports.get_latency(next_hop_port),
                expire_time=api.current_time() + self.ROUTE_TTL
            )
        else:
            # Rule 1: Distributed Bellman Ford
            new_latency = route_latency + self.ports.get_latency(port)
            # Tiebreak and choose the current latency instead of new one
            # More stable
            if new_latency < next_hop_info.latency:
                self.table[route_dst] = TableEntry(
                    dst=route_dst,
                    port=port,
                    latency=new_latency,
                    expire_time=api.current_time() + self.ROUTE_TTL
                )
        ##### End Stages 4, 10 #####

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this router goes up.

        :param port: the port that the link is attached to.
        :param latency: the link latency.
        :returns: nothing.
        """
        self.ports.add_port(port, latency)

        ##### Begin Stage 10B #####

        ##### End Stage 10B #####

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this router goes down.

        :param port: the port number used by the link.
        :returns: nothing.
        """
        self.ports.remove_port(port)

        ##### Begin Stage 10B #####

        ##### End Stage 10B #####

    # Feel free to add any helper methods!
