#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.cli import CLI

from sys import argv

class SimpleTopo(Topo):
	def __init__(self, **opts):
		Topo.__init__(self, **opts)

		switch1 = self.addSwitch('s1')
		host1 = self.addHost('h1')

		switch2 = self.addSwitch('s2')
		host2 = self.addHost('h2')

		self.addLink(switch1, host1)
		self.addLink(switch2, host2)

		# 30ms delay
		self.addLink(switch1, switch2, delay='30ms')


def main():
	topo = SimpleTopo()
	net = Mininet(topo=topo, link=TCLink, autoStaticArp=True)
	net.start()

	dumpNodeConnections(net.hosts)
	CLI(net)

	net.stop()

if __name__ == '__main__':
	setLogLevel('info')
	main()
