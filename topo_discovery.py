import time
from collections import defaultdict

from pox.core import core
from pox.lib.revent import *
from pox.lib.recoco import Timer
from pox.lib.util import dpid_to_str
from pox.openflow.discovery import Discovery

log = core.getLogger()

# [dpid] -> Switch
switches = {} 

# ethaddr -> (switch, port)
mac_map = {}

# Adjacency map.  [sw1][sw2] -> port from sw1 to sw2
adjacency = defaultdict(lambda: defaultdict(lambda: None))


def get_paths(src, dst):
	visited = set()
	path = []
	get_paths_helper(None, src, dst, visited, path)

def get_paths_helper(pre, cur, dst, visited, path):
	visited.add(cur)
	if pre is not None:
		path.append((pre.dpid, adjacency[pre][cur]))

	if cur == None:
		log.info(path)
	elif cur == dst:
		get_paths_helper(cur, None, dst, visited, path)
	else:
		for next_hop, port in adjacency[cur].iteritems():
			if next_hop not in visited:
				if port is None:
					continue
				get_paths_helper(cur, next_hop, dst, visited, path)

	if path:
		path.pop()
	visited.remove(cur)



class Switch(EventMixin):
	def __init__(self):
		self.connection = None
		self.ports = None
		self.dpid = None
		self._listeners = None
		self._connected_at = None

	def __repr__(self):
		return dpid_to_str(self.dpid)

	def disconnect(self):
		if self.connection is not None:
			self.connection.removeListeners(self._listeners)
			self.connection = None
			self._listeners = None

	def connect(self, connection):
		if self.dpid is None:
			self.dpid = connection.dpid

		if self.ports is None:
			self.ports = connection.features.ports

		self.disconnect()

		log.info('Connect %s' % (connection))
		self.connection = connection
		self._listeners = self.listenTo(connection)
		self._connected_at = time.time()

	def _handle_ConnectionDown(self, event):
		self.disconnect()




class TopoDiscoveryController(EventMixin):
	def __init__(self):
		core.listen_to_dependencies(self, listen_args={'openflow':{'priority':0}})

	def _handle_openflow_discovery_LinkEvent(self, event):
		log.info('Handle link event')

		def flip(link):
			return Discovery.Link(link[2],link[3], link[0],link[1])

		l = event.link
		sw1 = switches[l.dpid1]
		sw2 = switches[l.dpid2]

		if event.removed:
			# TODO: handle link remove event
			pass
		else:
			if adjacency[sw1][sw2] is None:
				if flip(l) in core.openflow_discovery.adjacency:
					log.info('Add Link')
					adjacency[sw1][sw2] = l.port1
					adjacency[sw2][sw1] = l.port2

	def _handle_openflow_ConnectionUp(self, event):
		log.info('Handle connection up')

		sw = switches.get(event.dpid)
		if sw is None:
			# New switch
			sw = Switch()
			switches[event.dpid] = sw
			sw.connect(event.connection)
		else:
			sw.connect(event.connection)


def test_get_paths():
	sw1 = switches[1]
	sw2 = switches[2]

	get_paths(sw1, sw2)


def launch():
	core.registerNew(TopoDiscoveryController)

	Timer(10, test_get_paths)