#!/usr/bin/env python3
import argparse
import json
import subprocess
import re
import atexit


def print_performance_data(res_mtr):
    print("Hops:")
    hops = res_mtr["report"]["hubs"]
    for i in range(len(hops)-1):
        hop = hops[i]
        print("{}. {} {}% {} {} {} {} {} {}".format(hop["count"], hop["host"], hop["Loss%"], hop["Snt"], hop["Last"],
                                                    hop["Avg"], hop["Best"], hop["Wrst"], hop["StDev"]))
    hop = hops[len(hops)-1]
    print("{}. {} {}% {} {} {} {} {} {} | ".format(hop["count"], hop["host"], hop["Loss%"], hop["Snt"], hop["Last"],
                                                   hop["Avg"], hop["Best"], hop["Wrst"], hop["StDev"]), end="")
    for i in range(len(hops)):
        hop = hops[i]
        print("'hop_{}_rta'={};; ".format(hop["host"], hop["Avg"]), end="")
        print("'hop_{}_pl'={};; ".format(hop["host"], hop["Loss%"]), end="")


def parse_hops(hops: str):
    parsed_hops = []
    hops_list = hops.split(",")
    for i in range(len(hops_list)):
        # Wildcard section
        if hops_list[i] == "*":
            parsed_hops.append("*")
            continue
        if hops_list[i].startswith("*"):
            current_hop = hops_list[i][1:]
            current_hop = current_hop.split("-")
            try:
                if len(current_hop) > 2:
                    print("UNKNOWN - Wrong format of hops string!")
                    exit(3)
                elif len(current_hop) == 2:
                    parsed_hops.append(range(int(current_hop[0]), int(current_hop[1])+1))
                elif len(current_hop) == 1:
                    parsed_hops.append(int(current_hop[0]))
            except ValueError:
                print("UNKNOWN - Wrong format of hops string!")
                exit(3)
        # Hostname/IP section
        else:
            hop = hops_list[i].split("[")
            latency, package_loss = None, None
            if len(hop) > 1:
                numbers = re.compile(r'\d+(?:\.\d+)?')
                values = hop[1].split(":")
                if len(values) != 2:
                    print("UNKNOWN - Wrong format of hops latency/package loss!")
                    exit(3)
                latency = numbers.findall(values[0])
                if len(latency) == 0:
                    latency = None
                else:
                    latency = float(latency[0])
                package_loss = numbers.findall(values[1])
                if len(package_loss) == 0:
                    package_loss = None
                else:
                    package_loss = float(package_loss[0])
            parsed_hops.append({"type": "Ip", "value": hop[0], "latency": latency, "package_loss": package_loss})
    return parsed_hops


def parse_routers(routers: str):
    return routers.strip("[]").replace(" ", "").split(",")


def parse_cli():
    parser = argparse.ArgumentParser(
        description="Monitoring check plugin that compares the expected values for hops, latency and packet loss "
                    "to the actual MTR results")
    parser.add_argument("-H", "--host", type=str, help="Host to check MTR on")
    parser.add_argument("-j", "--jumps", type=str, help="Expected hops/jumps")
    parser.add_argument("-l", "--latency", type=str, help="Maximum expected latency")
    parser.add_argument("-p", "--packetloss", type=str, help="Maximum expected packet loss")
    parser.add_argument("-r", "--routers", type=str, help="Routers that should be in the routing path")
    parser.add_argument("-4", "--ipv4", action='store_true', help="Use IPv4 for mtr")
    parser.add_argument("-6", "--ipv6", action='store_true', help="Use IPv6 for mtr")
    args = parser.parse_args()
    args = args.__dict__

    # No host => Exit
    if args["host"] is None:
        print("UNKNOWN - No host was given!")
        exit(3)

    # No expected values given => Exit
    if args["jumps"] is None and args["latency"] is None and args["packetloss"] is None and args["routers"] is None:
        print("UNKNOWN - At least one expectation (-H, -p, -l, -r) must be given!")
        exit(3)

    # IPv4 or IPv6?
    ip4, ip6 = args["ipv4"], args["ipv6"]

    # Parse values
    hops, ping, loss, routers = None, args["latency"], args["packetloss"], None
    if args["jumps"] is not None:
        hops = parse_hops(args["jumps"])
    if args["routers"] is not None:
        routers = parse_routers(args["routers"])
    try:
        if ping is not None:
            ping = float(ping)
        if loss is not None:
            loss = float(loss)
    except (ValueError, TypeError):
        print("UNKNOWN - The maximum expected latency and package loss must be integer values!")
        exit(3)
    return hops, ping, loss, routers, args["host"], ip4, ip6


def get_mtr_values(host, ip4, ip6):
    if (not ip4) and ip6:
        out = subprocess.check_output(['mtr', '-j', '-6', host])
    else:
        out = subprocess.check_output(['mtr', '-j', '-4', host])
    return json.loads(out)


def check_hop_values(hop, real_hop):
    if hop["latency"] is not None and hop["latency"] < real_hop["Avg"]:
        print("CRITICAL - The latency for hop " + real_hop["host"] + " was " + str(real_hop["Avg"]) +
              " ms, but expected was a latency smaller than " + str(hop["latency"]) + " ms!")
        exit(2)
    if hop["package_loss"] is not None and hop["package_loss"] < real_hop["Loss%"]:
        print("CRITICAL - The package loss for hop " + real_hop["host"] + " was " + str(real_hop["Loss%"]) +
              "%, but expected was a latency smaller than " + str(hop["package_loss"]) + "%!")
        exit(2)


def check_hops(expected_hops, res):
    current_hops = 0
    for hop in expected_hops:
        # Wildcard
        if type(hop) == str and hop == "*":
            if type(current_hops) == list:
                start = current_hops[0]
            else:
                start = current_hops
            current_hops = [x for x in range(start, len(res))]
        # Wildcard range
        if type(hop) == range:
            if type(current_hops) == int:
                current_hops = [x + current_hops for x in hop]
            elif type(current_hops) == list:
                new_hops = []
                for i in range(len(hop)):
                    for j in range(len(current_hops)):
                        summing = hop[i] + current_hops[j]
                        if summing not in new_hops:
                            new_hops.append(summing)
                current_hops = new_hops
        # Wildcard static value
        if type(hop) == int:
            if type(current_hops) == int:
                current_hops += hop
            elif type(current_hops) == list:
                current_hops = [x + hop for x in current_hops]
        # Hostname/Ip
        if type(hop) == dict:
            found = False
            if type(current_hops) == list:
                for hop_number in current_hops:
                    if hop_number >= len(res):
                        break
                    if res[hop_number]["host"] == hop["value"]:
                        check_hop_values(hop, res[hop_number])
                        current_hops = hop_number + 1
                        found = True
                        break
                if not found:
                    print("CRITICAL - The expected hop " + hop["value"] + " was not in the routing path!")
                    exit(2)
            elif type(current_hops) == int:
                if res[current_hops]["host"] != hop["value"]:
                    print("CRITICAL - The expected hop " + hop["value"] + " was not in the routing path!")
                    exit(2)
                else:
                    check_hop_values(hop, res[current_hops])
                current_hops += 1


def check_mtr_values(expected_hops, expected_ping, expected_loss, expected_routers, mtr_res):
    res = mtr_res["report"]["hubs"]

    # Check latency
    if expected_ping is not None:
        for node in res:
            if float(node["Avg"]) > float(expected_ping):
                print("CRITICAL - Latency was higher than the maximum expected value!")
                exit(2)

    # Check packet loss
    if expected_loss is not None:
        for node in res:
            if float(node["Loss%"]) > float(expected_loss):
                print("CRITICAL - Packet loss was higher than the maximum expected value!")
                exit(2)

    # Check routers
    if expected_routers is not None:
        routers = []
        for node in res:
            routers.append(node["host"])
        for node in expected_routers:
            if node not in routers:
                print("CRITICAL - One of the expected routers was not in the routing path!")
                exit(2)
        pass

    # Check hops
    if expected_hops is not None:
        check_hops(expected_hops, res)


def main():
    hops, ping, loss, routers, host, ip4, ip6 = parse_cli()
    mtr_res = get_mtr_values(host, ip4, ip6)
    atexit.register(print_performance_data, mtr_res)
    check_mtr_values(hops, ping, loss, routers, mtr_res)
    print("OK - All values were in the valid range")
    exit(0)


if __name__ == "__main__":
    main()
