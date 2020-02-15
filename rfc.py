#! /usr/bin/python2.7

# imports
#######################################
from __future__ import print_function
import time
import argparse
from rflib import *
import datetime

# terminal colors
#######################################
color_default 	= "\033[39m"
color_black 	= "\033[30m"
color_red 		= "\033[31m"
color_green 	= "\033[32m"
color_yellow 	= "\033[33m"
color_blue 		= "\033[34m"
color_magenta 	= "\033[35m"
color_cyan 		= "\033[36m"
color_lgray 	= "\033[37m"
color_dgray 	= "\033[90m"
color_lred 		= "\033[91m"
color_lgreen 	= "\033[92m"
color_lyellow 	= "\033[93m"
color_lblue 	= "\033[94m"
color_lmagenta 	= "\033[95m"
color_lcyan 	= "\033[96m"
color_white 	= "\033[97m"

# clear screen function
# os.sys can also be used to call clear command
clr = lambda : print("".join(["\n" for _ in range(200)]))

print()

# set up argument parser
#######################################
parser = argparse.ArgumentParser(description='DEF CON 27 TPMS Program')

parser.add_argument('-d', '--delay',     	metavar='SECONDS', 	type=float, 	help='number of seconds to wait between transmissions')
parser.add_argument('-m', '--manchester', 	metavar='{0,1,2}', 	type=int, 		help='type of Manchester encoding to use')
parser.add_argument('-f', '--frequency', 	metavar='Hz', 		type=float, 	help='frequency to transmit on')
parser.add_argument('-b', '--bits', 		metavar='10...',	type=str, 	    help='string of bits to use')
parser.add_argument('-n', '--repeat', 		metavar='n',	 	type=int, 	    help='number of times to repeat transmission')

args = parser.parse_args()

# sanity checks on arguments
#######################################
def fatal_error(msg):
	print(color_red + "[!] error: " + color_yellow + msg + '\n')
	exit(1)

if args.delay is None:
	fatal_error("no delay specified. use -d")

if args.frequency is None:
	fatal_error("no frequency specified. use -f")

if args.bits is None:
	fatal_error("no bit string specified. use -b")


# utilities for converting to/from hex
#######################################

# create ASCII binary reperesentation of ASCII hex string
def hex_to_bin(h):
	# strip all invalid characters from hex string
	h = "".join([c if c.lower() in "0123456789abcdef" else '' for c in h])
	r = ""
	for char in h:
		b = "{0:b}".format(int(char, 16))
		b = "".join(["0" for _ in range(4-len(b))]) + b
		r += b
	return r

# create ASCII hex representation of ASCII string
string_to_hex = lambda s : "".join([c.encode('hex').upper() + ' ' for c in s]).strip()

# more sanity checks on bit string
#######################################

# determine type of bit string (hex or bin)
# make sure that length of binary data is a multiple of 8
# (because of the weird hacky shit that I had to do to satisfy RFXmit)
if args.bits[0:2].lower() == "0b" and len(args.bits) > 1:
	args.bits = args.bits[2:]
	if len(args.bits)%8:
		fatal_error("length of binary string is not a multiple of 8\n\
	   consider adding leading or trailing zeros")
	bstr = args.bits
elif args.bits[0:2].lower() == "0x" and len(args.bits) > 1:
	args.bits = args.bits[2:]
	if len(args.bits)%2:
		fatal_error("length of hex string is not a multiple of 2\n\
	   consider adding a leading or trailing zero")
	bstr = hex_to_bin(args.bits)
else:
	fatal_error("invalid bit string prefix. must start with 0x or 0b")


# bullshit hack stuff
# abandon hope all ye who enter here
#######################################

# take a string of ASCII 1s and 0s and turn it
# into a probably-unprintable string that will
# be passed to RFXmit()
def bits_to_rfcat_string(bit_string, m=False):
	# split bit string into groups of 8
	grouped_bit_string = [bit_string[n:n+8] for n in range(0, len(bit_string), 8)]

	# turn each group of 8 bits into an integer
	bits_integer_array = [int(c,2) for c in grouped_bit_string]

	# turn each integer into an ASCII character
	bits_char_array = [chr(i) for i in bits_integer_array]

	# join these characters together into a string
	bits_character_string = "".join(bits_char_array)

	return bits_character_string



# information display
#######################################
status_strings = {}

def print_status():
	for key in status_strings:
		print(color_blue + key + ":\t" + color_yellow + str(status_strings[key]))
	print()

# set up manchester
#######################################

if args.manchester == None or args.manchester == 0:
	manchester = ("0","1")
elif args.manchester == 1:
	manchester = ("01", "10")
elif args.manchester == 2:
	manchester = ("10", "01")
else:
	fatal_error("invalid Manchester encoding type specified")
status_strings['manchester'] = args.manchester

# function to replace 1s and 0s with the correct values for manchester
apply_manchester = lambda s : "".join([str(manchester[1] if c == "1" else manchester[0]) for c in s])



# provision RFCat
#######################################
print(color_magenta + "setting up RFCat object..." + color_white)
d = RfCat()
d.setFreq(args.frequency)
d.setMdmModulation(MOD_2FSK)
d.setMdmDeviatn(31000)
d.setMdmDRate(20000)
d.setMdmSyncMode(SYNC_MODE_NO_PRE)
d.setEnableMdmManchester(False)
if args.manchester is not None:
	d.makePktFLEN(len(bits_to_rfcat_string(bstr)))
else:
	d.makePktFLEN(len(bits_to_rfcat_string(apply_manchester(bstr))))
status_strings['frequency'] = args.frequency

# transmit loop
#######################################

# keep track of how many transmissions must be sent
# loop until that number has been reached
# if not specified, loop ad infinitum
past_transmissions = 0
max_transmissions = 0 if args.repeat is None else args.repeat
try:
	while past_transmissions < max_transmissions or max_transmissions == 0:#
		past_transmissions += 1

		clr()
		print_status()

		# print timestamp
		timestamp = str(datetime.datetime.now().replace(microsecond=0))
		print(color_blue + timestamp, end='')
		
		# print current transmission number
		print(color_magenta + " ({}".format(past_transmissions), end='')

		# if applicable, print max transmission number
		if max_transmissions > 0:
			print("/{}".format(max_transmissions), end='')
		print(')' + color_white)

		# print unencoded hex data
		print(color_lgreen + "  unencoded:")
		print("    " + color_yellow + string_to_hex(bits_to_rfcat_string(bstr)), end=color_white+'\n')

		# if applicable, print manchestered hex data
		if args.manchester == 1 or args.manchester == 2:
			print(color_lgreen + "  manchester {}:".format(args.manchester))
			print("    " + color_yellow + string_to_hex(bits_to_rfcat_string(apply_manchester(bstr))), end=color_white+'\n')

		if args.manchester == 1 or args.manchester == 2:
			d.RFxmit(bits_to_rfcat_string(apply_manchester(bstr)))
		else:
			d.RFxmit(bits_to_rfcat_string(bstr))

		# print delay and wait
		if past_transmissions < max_transmissions or max_transmissions == 0:
			print(color_dgray + str(args.delay) + "s..." + color_white)
			time.sleep(args.delay)

# exit cleanly on signal interrupt
except KeyboardInterrupt:
	pass

print(color_green + "\n\n[+] farewell ;^)\n")