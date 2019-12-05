#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.cli import CLI
from mininet.node import RemoteController, CPULimitedHost

from sys import argv

class SimpleTopo(Topo):
	def __init__(self, **opts):
		Topo.__init__(self, **opts)

		switch1 = self.addSwitch('s1')
		host1 = self.addHost('h1', mac='20:00:00:00:00:01')

		switch2 = self.addSwitch('s2')
		host2 = self.addHost('h2', mac='20:00:00:00:00:02')

		switch3 = self.addSwitch('s3')
		host3 = self.addHost('h3', mac='20:00:00:00:00:03')

		switch4 = self.addSwitch('s4')
		host4 = self.addHost('h4', mac='20:00:00:00:00:04')

		self.addLink(switch1, host1)
		self.addLink(switch2, host2)
		self.addLink(switch3, host3)
		self.addLink(switch4, host4)

		self.addLink(switch1, switch3)
		self.addLink(switch1, switch4, delay='30ms')

		self.addLink(switch2, switch3)
		self.addLink(switch2, switch4)


		# # 30ms delay
		# self.addLink(switch1, switch2, delay='30ms')


def main():
	c = RemoteController('c0', '127.0.0.1', 6633)

	topo = SimpleTopo()
	net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink, autoStaticArp=True, controller=c)
	net.start()

	dumpNodeConnections(net.hosts)
	CLI(net)

	net.stop()

if __name__ == '__main__':
	setLogLevel('info')
	main()
