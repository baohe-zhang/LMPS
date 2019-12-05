# Copyright 2012 James McCauley
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpidToStr
from pox.lib.recoco import Timer
import time, struct
from pox.lib.packet.packet_base import packet_base
from pox.lib.packet.packet_utils import *
from pox.lib.packet import ethernet
from pox.lib.addresses import IPAddr, EthAddr
from pox.misc.topo_discovery import switches, TopoDiscoveryController, get_paths

log = core.getLogger()

probe_timer = None

src_dpid = 0
dst_dpid = 0

start_time = 0.0
send_time_1 = 0.0
send_time_2 = 0.0
received_time_1 = 0.0
received_time_2 = 0.0
T1 = 0.0
T2 = 0.0
PROBE_TYPE = 0x8888

paths = []

class probe_proto(packet_base) :
    """
    Probing packets to measure the delay
    """
    def __init__(self) :
        packet_base.__init__(self)
        self.ts = 0.0
    
    def hdr(self, payload):
        return struct.pack('!d', self.ts)

class LearningSwitch (object):
  """
  A Tutorial object is created for each switch that connects.
  A Connection object for that switch is passed to the __init__ function.
  """
  def __init__ (self, connection):
    # Keep track of the connection to the switch so that we can
    # send it messages!
    self.connection = connection

    # This binds our PacketIn event listener
    connection.addListeners(self)

    # Use this table to keep track of which ethernet address is on
    # which switch port (keys are MACs, values are ports).
    self.mac_to_port = {}

  def resend_packet (self, packet_in, out_port):
    """
    Instructs the switch to resend a packet that it had sent to us.
    "packet_in" is the ofp_packet_in object the switch had sent to the
    controller due to a table-miss.
    """
    msg = of.ofp_packet_out()
    msg.data = packet_in
    msg.in_port = packet_in.in_port

    # Add an action to send to the specified port
    action = of.ofp_action_output(port = out_port)
    msg.actions.append(action)

    # Send message to switch
    self.connection.send(msg)

  def act_like_hub (self, packet, packet_in):
    """
    Implement hub-like behavior -- send all packets to all ports besides
    the input port.
    """

    # We want to output to all ports -- we do that using the special
    # OFPP_ALL port as the output port.  (We could have also used
    # OFPP_FLOOD.)
    self.resend_packet(packet_in, of.OFPP_ALL)

    # Note that if we didn't get a valid buffer_id, a slightly better
    # implementation would check that we got the full data before
    # sending it (len(packet_in.data) should be == packet_in.total_len)).


  def act_like_switch (self, packet, packet_in):
    """
    Implement switch-like behavior.
    """

    # DELETE THIS LINE TO START WORKING ON THIS (AND THE ONE BELOW!) #

    # Here's some psuedocode to start you off implementing a learning
    # switch.  You'll need to rewrite it as real Python code.

    # Learn the port for the source MAC
    if packet.src not in self.mac_to_port :
        log.debug("Controller learn mac address %s from port %d" % (packet.src, packet_in.in_port))
    self.mac_to_port[packet.src] = packet_in.in_port
    print(self.mac_to_port)

    if packet.dst in self.mac_to_port :
        # Send packet out the associated port
        #log.debug("Flow table hit, sends out packet to port %d" % self.mac_to_port[packet.dst])
        #self.resend_packet(packet_in, self.mac_to_port[packet.dst])
        # Once you have the above working, try pushing a flow entry
        # instead of resending the packet (comment out the above and
        # uncomment and complete the below.)
        dst = packet.dst
        out_port = self.mac_to_port[packet.dst]
        log.debug("Installing flow...")
        log.debug("Destination MAC %s" % dst)
        log.debug("Destination port %s" % out_port)

        fm = of.ofp_flow_mod()
        fm.match = of.ofp_match.from_packet(packet, in_port = packet_in.in_port)

        # it is not mandatory to set fm.data or fm.buffer_id
        if packet_in.buffer_id != -1 and packet_in.buffer_id is not None:
            fm.buffer_id = packet_in.buffer_id
        else:
            if packet_in.data is None:
                return
            fm.data = packet_in.data
        # Add an action to send to the specified port
        action = of.ofp_action_output(port=out_port)
        fm.actions.append(action)

        # Send message to switch to install this flow
        self.connection.send(fm)

    else:
        # Flood the packet out everything but the input port
        # This part looks familiar, right?
        self.resend_packet(packet_in, of.OFPP_FLOOD)
        print("FLOODING")

  def _handle_BarrierIn (self, event):
    global start_time, receive_time_1, receive_time_2, send_time_1, send_time_2, src_dpid, dst_dpid, T1, T2

    #print("Handle timestamp %f" % receive_time)
    if event.connection.dpid == dst_dpid :
        receive_time_2 = time.time() * 1000
        T2 = (receive_time_2 - send_time_2) / 2
        print("Get the T2 RTT %f ms" % T2)
    elif event.connection.dpid == src_dpid :
        receive_time_1 = time.time() * 1000
        T1 = (receive_time_1 - send_time_1) / 2
        print("Get the T1 RTT %f ms" % T1)

  def _handle_PacketIn (self, event):
    """
    Handles packet in messages from the switch.
    """
    global start_time, T1, T2, PROBE_TYPE, dst_dpid
    packet = event.parsed # This is the parsed packet data.
    if not packet.parsed:
      log.warning("Ignoring incomplete packet")
      return

    if packet.type == PROBE_TYPE :
        received_time = time.time() * 1000
        ts = packet.find("ethernet").payload
        ts, = struct.unpack("!d", ts)
        path_idx = str(packet.dst).split(':')[-1]
        delay = received_time - ts - T1 - T2
        print("Path [%s] delay from s1 to s2: %f ms" % (path_idx, delay))
        #print("T1 %f T2 %f" % (T1, T2))
        return

    packet_in = event.ofp # The actual ofp_packet_in message.

    # Comment out the following line and uncomment the one after
    # when starting the exercise.
    #self.act_like_hub(packet, packet_in)
    self.act_like_switch(packet, packet_in)


def s2_timer_handler() :
    global start_time, send_time_1, send_time_2, src_dpid, dst_dpid, PROBE_TYPE
    send_time_2 = time.time() * 1000
    print("Send to S2:", send_time_2)
    xid = of.generate_xid()
    core.openflow.getConnection(dst_dpid).send(of.ofp_barrier_request())

def s1_timer_handler() :
    global start_time, send_time_1, send_time_2, src_dpid, dst_dpid, PROBE_TYPE
    send_time_1 = time.time() * 1000
    print("Send to S1:", send_time_1)
    core.openflow.getConnection(src_dpid).send(of.ofp_barrier_request())


def timer_handler() :
    global paths
    for path_idx in range(len(paths)) :
        probe = probe_proto()
        probe.ts = time.time() * 1000
        eth = ethernet()
        eth.src = EthAddr("06:12:3d:5d:ae:0c")
        eth.dst = EthAddr("00:00:00:00:00:" + "%2d" % (path_idx + 1))
        eth.type = PROBE_TYPE
        eth.set_payload(probe)
        msg = of.ofp_packet_out()
        msg.data = eth.pack()
        msg.actions.append(of.ofp_action_output(port=paths[path_idx][0][1]))
        core.openflow.getConnection(src_dpid).send(msg)


def probe_flowmod_msg(path_idx, output_port) :
    fm = of.ofp_flow_mod()
    fm.idle_timeout = 0
    fm.hard_timeout = 0
    fm.match.dl_type = PROBE_TYPE
    fm.match.dl_dst = EthAddr("00:00:00:00:00:" + "%2d" % (path_idx + 1))
    fm.actions.append(of.ofp_action_output(port=output_port))
    return fm
 

def setup_probe_connectivity() :
    # Having the overall topology discovered
    # discover(start, end)
    global paths
    paths = get_paths(switches[1], switches[2])
    log.info("Path:", paths)
    for idx in range(len(paths)) :
        for sw, port in paths[idx] :
            fm = probe_flowmod_msg(idx, port) if port else probe_flowmod_msg(idx, of.OFPP_CONTROLLER)
            core.openflow.getConnection(sw).send(fm)
  
def launch():
    """
    Starts the component
    """
    def start_switch (event):
        # Instance for each switch 
        LearningSwitch(event.connection)
        global probe_timer, src_dpid, dst_dpid, paths
        log.debug("Controlling %s" % (event.connection,))
        for p in event.connection.features.ports :
            if p.name == "s1-eth2" :
                src_dpid = event.connection.dpid
            elif p.name == "s2-eth2" :
                dst_dpid = event.connection.dpid
        # When the two switch connection up, starting timer
        log.debug(switches)
        if len(switches) == 4 :
            Timer(10, setup_probe_connectivity)
            probe_timer = Timer(15, timer_handler, recurring = True)
            probe_timer.start()
            s1_timer = Timer(2, s1_timer_handler, recurring = True)
            s1_timer.start()
            s2_timer = Timer(2, s2_timer_handler, recurring = True)
            s2_timer.start()

    def stop_switch (event):
        global probe_timer, src_dpid, dst_dpid
        log.debug("Down %s" % (event.connection,))
        probe_timer.cancel()
        src_dpid = 0
        dst_dpid = 0

    core.registerNew(TopoDiscoveryController)
    core.openflow.addListenerByName("ConnectionUp", start_switch)
    core.openflow.addListenerByName("ConnectionDown", stop_switch)
    #core.openflow.addListenerByName("PortStatsReceived", _handle_portstats_received)
