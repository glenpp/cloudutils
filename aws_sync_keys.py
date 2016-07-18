#!/usr/bin/env python
#    AWS ssh Id sync tool (maintains known_hosts)
#    Copyright (C) 2016  Glen Pitt-Pladdy
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
# See: https://www.pitt-pladdy.com/blog/
#

import boto.ec2
import time
import os
import re
import time

# if we should, and how to wait for booting instances
waitforboot = True
pollinterval = 30
timeout = 600

# generate our datestamp (ISO)
datestamp = time.strftime ( '%Y%m%d' )

# default known_hosts
sshknownhosts = "%s/.ssh/known_hosts" % os.environ['HOME']

# defalt aws-cli credentials
awsclicredentials = "%s/.aws/config" % os.environ['HOME']

# read in creds
awsid = None
awskey = None
awsregion = None
with open ( awsclicredentials, 'r' ) as f:
	for line in f:
		matches = re.match ( r'^(\S+)\s*=\s*(\S+)$', line.strip() )
		if not matches: continue
		if matches.group(1) == 'aws_access_key_id':
			awsid = matches.group(2)
		elif matches.group(1) == 'aws_secret_access_key':
			awskey = matches.group(2)
		elif matches.group(1) == 'region':
			awsregion = matches.group(2)
if awsid == None or awskey == None or awsregion == None:
	sys.exit ( "FATAL - couldn't parse \"%s\"" % awsclicredentials )

# understand existing ssh keys
sshinstances = {}
knownhosts = []
with open ( sshknownhosts, 'r' ) as f:
	for line in f:
		matches = re.match ( r'^(\S+)\s+(\S.+\S)\s+AWS:(i-\S+)$', line.strip() )	# unhashed with instance id
# TODO multiple keys TODO
		if matches:
			# ec2 instance
			if matches.group(3) not in sshinstances:
				sshinstances[matches.group(3)] = {
						'addr': matches.group(1),
						'keys': [],
					}
			sshinstances[matches.group(3)]['keys'].append ( matches.group(2) )
		else:
			# normal ssh known_host
			knownhosts.append ( line )


# get boto up
bconn = boto.ec2.connect_to_region (
			awsregion,
			aws_access_key_id=awsid,
			aws_secret_access_key=awskey
		)

# get instances, merge known keys
awsinstances = {}
#for reservation in bconn.get_all_reservations(filters={'instance-state-name': ['running','pending','shutting-down','stopping','stopped']}):
for reservation in bconn.get_all_reservations():
	for instance in reservation.instances:
#		print instance.id
#		print instance.state
# skip "terminated"
		# TODO loop all instances TODO
		if instance.state == 'terminated': continue
		instance = {
			'private_dns': reservation.instances[0].private_dns_name,
			'private_ip': reservation.instances[0].private_ip_address,
			'public_dns': reservation.instances[0].public_dns_name,
			'public_ip': reservation.instances[0].ip_address,
		}
#		print reservation.instances[0].private_dns_name
#		print reservation.instances[0].private_ip_address
#		print reservation.instances[0].public_dns_name
#		print reservation.instances[0].ip_address
#		print reservation.instances[0].id
		timeoutafter = time.time () + timeout
		if reservation.instances[0].id in sshinstances and 'keys' in sshinstances[reservation.instances[0].id]:
			instance['keys'] = sshinstances[reservation.instances[0].id]['keys']
#			print "existing"
#			print  instance['keys']
			booting = False
		else:
			booting = True
			while booting:
				linecount = 0
				linesafterlogin = 0
				keys = False
				foundlogin = False
				keylines = []
				console = bconn.get_console_output ( reservation.instances[0].id ).output
				if console != None:
					for line in console.splitlines():
#						print ">"+line.strip()
						linecount += 1
						if foundlogin: linesafterlogin += 1
						if re.match ( r'^ip-\d+-\d+-\d+-\d+\s+login:', line.strip() ):
#							print "login"
							foundlogin = True
						if re.match ( r'^---+BEGIN SSH HOST KEY KEYS---+$', line.strip() ):
#							print "begin"
							keys = True
							continue
						if re.match ( r'^---+END SSH HOST KEY KEYS---+$', line.strip() ):
#							print "end"
							keys = False
							continue
						if keys == True:
							keylines.append ( line.strip() )
					if len(keylines) > 0:
						instance['keys'] = keylines
#						print "captured keys"
#						print  instance['keys']
					if linesafterlogin == 0 or not foundlogin:
						# normally it stops at the login prompt - we would only use ssh so lines after means rebooting
						booting = False
					if not foundlogin:
						booting = True
#					print "lines"
#					print  keylines
				if waitforboot:
					timenow = time.time ()
					if booting and timenow < timeoutafter:
#						print "%s: waitng for boot" % reservation.instances[0].id
						time.sleep ( pollinterval )
					else:
#						print "%s: booted or timed out" % reservation.instances[0].id
						break
		instance['Booting'] = booting
		awsinstances[reservation.instances[0].id] = instance

# TODO now rewrite ~/.ssh/known_hosts TODO
for instance in awsinstances:
	addresses = []
	for address in ['private_dns','private_ip','public_dns','public_ip']:
			if awsinstances[instance][address] != '' and awsinstances[instance][address] != None:
				addresses.append ( awsinstances[instance][address] )
	if len(addresses) == 0: addresses.append ( 'NULL' )
	addresses = ','.join ( addresses )
	for key in awsinstances[instance]['keys']:
		knownhosts.append ( "%s %s AWS:%s\n" % (addresses,key,instance) )
# TODO we only see one key now ... others probably being overwritten
print ''.join ( knownhosts ).rstrip()	# rstrip() takes off CR to compensate for the one we get from print



#import pprint
#pprint.pprint ( awsinstances )

