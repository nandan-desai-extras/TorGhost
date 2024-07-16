#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
from requests import get
import subprocess
import time
import signal
from stem import Signal
from stem.control import Controller
import notify2

VERSION = "3.1.1"

IP_API = "https://check.torproject.org/api/ip"

LATEST_RELEASE_API = "https://api.github.com/repos/databurn-in/torghost/releases/latest"


class bcolors:

    BLUE = '\033[94m'
    GREEN = '\033[92m'
    RED = '\033[31m'
    YELLOW = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    BGRED = '\033[41m'
    WHITE = '\033[37m'


def t():
    current_time = time.localtime()
    ctime = time.strftime('%H:%M:%S', current_time)
    return '[' + ctime + ']'


def sigint_handler(signum, frame):
    print("User interrupt ! shutting down")
    stop_tor()


def logo():
    print(bcolors.RED + bcolors.BOLD)
    logo = """

 _____             ___    _                   _   
(_   _)           (  _`\ ( )                 ( )_ 
  | |   _    _ __ | ( (_)| |__     _     ___ | ,_)
  | | /'_`\ ( '__)| |___ |  _ `\ /'_`\ /',__)| |  
  | |( (_) )| |   | (_, )| | | |( (_) )\__, \| |_ 
  (_)`\___/'(_)   (____/'(_) (_)`\___/'(____/`\__)
                                  
        v{} - by DataBurn

    """.format(VERSION)
    print(logo)
    print(bcolors.ENDC)


def usage():
    print("""
    torghost usage:
    -s    --start       Start Tor
    -r    --switch      Request new tor exit node
    -x    --stop        Stop Tor
    -h    --help        printhelp
    -u    --update      Check for update
    -v    --version     Check the current version
    -i    --info        Check the current ip address and Tor status
    -c                  Start Tor with specific countries as exit nodes
    """)
    sys.exit()


def print_version():
    print("torghost version: " + VERSION)
    sys.exit()


def info():
    try:
        jsonRes = get(IP_API).json()
        ipTxt = jsonRes["IP"]
        print("CURRENT IP : " + bcolors.GREEN + ipTxt + bcolors.ENDC)
        torStatus = jsonRes["IsTor"]
        if torStatus == True:
            print("Tor status : " + bcolors.GREEN +
                  "Tor is active!" + bcolors.ENDC)
        else:
            print("Tor status : " + bcolors.RED +
                  "Tor is inactive!" + bcolors.ENDC)
    except Exception as e:
        f = open("torghost.dump", "w")
        f.write(str(e))
        print(t() + bcolors.RED + " Some error occured while connecting to https://check.torproject.org. Error message is dumped in 'torghost.dump' file in the current directory." + bcolors.ENDC)
        f.close()
    sys.exit()


def tor_active():
    try:
        jsonRes = get(IP_API).json()
        return jsonRes["IsTor"]
    except Exception as e:
        f = open("torghost.dump", "w")
        f.write(str(e))
        print(t() + bcolors.RED + " Some error occured while connecting to https://check.torproject.org. Error message is dumped in 'torghost.dump' file in the current directory." + bcolors.ENDC)
        f.close()
    return False


def check_root():
    if os.geteuid() != 0:
        print("You must be root to use torghost. Use 'sudo torghost'")
        sys.exit(0)


try:
    notify2.init("torghost")
    n = notify2.Notification(None)
    n.set_urgency(notify2.URGENCY_NORMAL)
    n.set_timeout(10000)
except:
    pass


def notify(text):
    try:
        n.update('torghost', text)
        n.show()
    except:
        # ignore if any notification related errors
        pass


signal.signal(signal.SIGINT, sigint_handler)


resolvString = 'nameserver 127.0.0.1'

torrc = '/etc/tor/torghostrc'
resolv = '/etc/resolv.conf'


def reset():
    os.system('mv /etc/resolv.conf.bak /etc/resolv.conf')
    IpFlush = \
        """
	iptables -P INPUT ACCEPT
	iptables -P FORWARD ACCEPT
	iptables -P OUTPUT ACCEPT
	iptables -t nat -F
	iptables -t mangle -F
	iptables -F
	iptables -X
	"""
    os.system(IpFlush)


def get_countries(countries):
    if len(countries) == 0:
        print("no countries")
    else:
        countryStr = ""
        for country in countries:
            countryStr = countryStr + "{" + country + "},"
        # remove the last ','
        return countryStr[:(len(countryStr)-1)]


def start_tor(countries):
    logo()
    print(t() + ' Always check for updates using -u option')
    TorrcCfgString = \
        """
        VirtualAddrNetwork 10.0.0.0/10
        AutomapHostsOnResolve 1
        TransPort 9040
        DNSPort 5353
        ControlPort 9051
        RunAsDaemon 1
        """
    if len(countries) != 0:
        print(t() + ' Exit nodes selected are : ' + str(countries))
        TorrcCfgString = TorrcCfgString + \
            """     
        ExitNodes {}
        StrictNodes 1
        """.format(get_countries(countries))
    os.system('sudo cp /etc/resolv.conf /etc/resolv.conf.bak')
    if os.path.exists(torrc) and TorrcCfgString in open(torrc).read():
        print(t() + ' Torrc file already configured')
    else:

        with open(torrc, 'w') as myfile:
            print(t() + ' Writing torcc file ')
            myfile.write(TorrcCfgString)
            print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    if resolvString in open(resolv).read():
        print(t() + ' DNS resolv.conf file already configured')
    else:
        with open(resolv, 'w') as myfile:
            print(t() + ' Configuring DNS resolv.conf file.. ', end=' ')
            myfile.write(resolvString)
            print(bcolors.GREEN + '[done]' + bcolors.ENDC)

    print(t() + ' Stopping Tor service (if already ON)', end=' ')
    os.system('sudo systemctl stop tor')
    os.system('sudo fuser -k 9051/tcp > /dev/null 2>&1')
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    print(t() + ' Starting new Tor daemon ', end=' ')
    os.system('sudo -u debian-tor tor -f /etc/tor/torghostrc > /dev/null'
              )
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    print(t() + ' Setting up iptables rules', end=' ')

    iptables_rules = \
        """
	NON_TOR="192.168.1.0/24 192.168.0.0/24"
	TOR_UID=%s
	TRANS_PORT="9040"

	iptables -F
	iptables -t nat -F

	iptables -t nat -A OUTPUT -m owner --uid-owner $TOR_UID -j RETURN
	iptables -t nat -A OUTPUT -p udp --dport 53 -j REDIRECT --to-ports 5353
	for NET in $NON_TOR 127.0.0.0/9 127.128.0.0/10; do
	 iptables -t nat -A OUTPUT -d $NET -j RETURN
	done
	iptables -t nat -A OUTPUT -p tcp --syn -j REDIRECT --to-ports $TRANS_PORT

	iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
	for NET in $NON_TOR 127.0.0.0/8; do
	 iptables -A OUTPUT -d $NET -j ACCEPT
	done
	iptables -A OUTPUT -m owner --uid-owner $TOR_UID -j ACCEPT
	iptables -A OUTPUT -j REJECT
	""" \
        % subprocess.getoutput('id -ur debian-tor')

    os.system(iptables_rules)
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    print(t() + ' Verifying your Tor connectivity...')
    time.sleep(5)
    if tor_active() == True:
        notify("Tor has started successfully!")
        print(t() + bcolors.GREEN + ' Tor has started successfully.' + bcolors.ENDC)
    else:
        print(t() + bcolors.RED +
              ' Something went wrong. Rolling back the process...' + bcolors.ENDC)
        reset()
        print(t() + bcolors.RED +
              ' You are not on Tor. Process was failed and rolled back.' + bcolors.ENDC)


def stop_tor():
    print(t() + bcolors.RED + ' Stopping Tor...' + bcolors.ENDC)
    print(t() + ' Flushing iptables, resetting to default', end=' ')
    reset()
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    print(t() + ' Shutting down Tor service', end=' ')
    os.system('sudo fuser -k 9051/tcp > /dev/null 2>&1')
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    print(t() + ' Restarting Network manager', end=' ')
    os.system('service network-manager restart')
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    print(t() + ' Verifying whether you have been disconnected from Tor or not...')
    time.sleep(3)
    if tor_active() == True:
        print(t() + bcolors.RED +
              ' Something went wrong. You are still on Tor.' + bcolors.ENDC)
    else:
        notify("Tor has stopped successfully!")
        print(t() + bcolors.GREEN + ' Tor has been' + bcolors.ENDC+bcolors.RED +
              ' stopped ' + bcolors.ENDC+bcolors.GREEN + 'successfully.' + bcolors.ENDC)


def switch_tor():
    print(t() + ' Please wait...')
    time.sleep(7)
    print(t() + ' Requesting new circuit...', end=' ')
    with Controller.from_port(port=9051) as controller:
        controller.authenticate()
        controller.signal(Signal.NEWNYM)
    print(bcolors.GREEN + '[done]' + bcolors.ENDC)
    notify("Tor has switched the circuit.")
    print(t() + ' Tor has switched the circuit.')


def check_update():
    print(t() + ' Checking for update...')
    jsonRes = get(LATEST_RELEASE_API).json()
    newversion = jsonRes["tag_name"][1:]
    if newversion != VERSION:
        print(t() + bcolors.GREEN + ' New update available!' + bcolors.ENDC)
        print(t() + ' Your current torghost version : ' +
              bcolors.GREEN + VERSION + bcolors.ENDC)
        print(t() + ' Latest torghost version available : ' +
              bcolors.GREEN + newversion + bcolors.ENDC)
        yes = {'yes', 'y', 'ye', ''}
        no = {'no', 'n'}

        choice = input(
            bcolors.BOLD + "Would you like to download latest version and build from Git repo? [Y/n]" + bcolors.ENDC).lower()
        if choice in yes:
            os.system(
                'cd /tmp && git clone  https://github.com/databurn-in/torghost')
            os.system('cd /tmp/torghost && sudo ./build.sh')
        elif choice in no:
            print(t() + " Update aborted by user")
        else:
            print("Please respond with 'yes' or 'no'")
    else:
        print(t() + " torghost is up to date!")


def main():
    check_root()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a", "--all", help="Route all traffic through Tor", action="store_true")
    parser.add_argument(
        "-i", "--info", help="Get info about Tor status and current IP address", action="store_true")
    parser.add_argument("-x", "--stop", help="Shutdown Tor",
                        action="store_true")
    parser.add_argument(
        "-u", "--update", help="Check for new updates for torghost", action="store_true")
    parser.add_argument(
        "-r", "--switch", help="Switch/Re-route Tor circuit", action="store_true")
    parser.add_argument("-c", "--countries",
                        help="Select certain countries for Tor exit node")
    parser.add_argument("-v", "--version",
                        help="Show version", action="store_true")
    args = parser.parse_args()

    if args.all:
        if args.countries != None:
            start_tor(args.countries.split(","))
        else:
            start_tor([])
    elif args.stop:
        stop_tor()
    elif args.info:
        info()
    elif args.update:
        check_update()
    elif args.switch:
        switch_tor()
    elif args.version:
        print_version()
    elif args.countries != None:
        print(bcolors.RED + "--countries option cannot be used alone"+bcolors.ENDC)


if __name__ == '__main__':
    main()
