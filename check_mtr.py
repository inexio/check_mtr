import argparse
import json
import socket
import subprocess


def check_ip(name):
    ip4 = socket.gethostbyname(name)
    if ip4 == name:
        return True
    else:
        return False


def parse_hops(hops: str):
    parsed_hops = []
    hops_list = hops.split(";")
    for i in range(len(hops_list)):
        # Wildcard section
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
            if check_ip(hops_list[i]):
                parsed_hops.append({"type": "Ip", "value": hops_list[i]})
            else:
                parsed_hops.append({"type": "Hostname", "value": hops_list[i]})
    return parsed_hops


def parse_cli():
    parser = argparse.ArgumentParser(
        description="Monitoring check plugin that compares the expected values for hops, latency and packet loss "
                    "to the actual MTR results")
    parser.add_argument("-H", "--host", type=str, help="Host to check MTR on")
    parser.add_argument("-j", "--jumps", type=str, help="Expected hops/jumps")
    parser.add_argument("-l", "--latency", type=str, help="Maximum expected latency")
    parser.add_argument("-p", "--packetloss", type=str, help="Maximum expected packet loss")
    args = parser.parse_args()
    args = args.__dict__

    # No host => Exit
    if args["host"] is None:
        print("UNKNOWN - No host was given!")
        exit(3)

    # No expected values given => Exit
    if args["jumps"] is None and args["latency"] is None and args["packetloss"] is None:
        print("UNKNOWN - At least one expectation (-H, -p, -l) must be given!")
        exit(3)

    # Parse values
    hops, ping, loss = None, args["latency"], args["packetloss"]
    if args["jumps"] is not None:
        hops = parse_hops(args["jumps"])
    try:
        if ping is not None:
            ping = int(ping)
        if loss is not None:
            loss = int(loss)
    except (ValueError, TypeError):
        print("UNKNOWN - The maximum expected latency and package loss must be integer values!")
        exit(3)
    return hops, ping, loss, args["host"]


def get_mtr_values(host):
    out = subprocess.check_output(['mtr', '-j', host])
    return json.loads(out)


def check_mtr_values(expected_hops, expected_ping, expected_loss, mtr_res):
    res = mtr_res["report"]["hubs"]

    # Check latency
    if expected_ping is not None:
        for node in res:
            if float(node["Avg"]) > float(expected_ping):
                print("CRITICAL - Latency was higher than the maximum expected value!")
                exit(3)

    # Check packet loss
    if expected_loss is not None:
        for node in res:
            if float(node["Loss%"]) > float(expected_loss):
                print("CRITICAL - Packet loss was higher than the maximum expected value!")
                exit(3)

    # Check hops
    current_hops = 0
    for hop in expected_hops:
        if type(hop) is list:
            if type(current_hops) is int:
                current_hops = [x + current_hops for x in hop]
            if type(current_hops) is list:
                length_before = len(current_hops)
                for i in range(len(hop)):
                    current_hops.append(current_hops[length_before-1] + hop[i])
        if type(hop) is int:
            if type(current_hops) is int:
                current_hops += hop
            if type(current_hops) is list:
                current_hops = [x + hop for x in current_hops]
        if type(hop) is dict:
            pass
            # TODO Check if hop is on one of the possible hops

def main():
    hops, ping, loss, host = parse_cli()
    mtr_res = get_mtr_values(host)
    check_mtr_values(hops, ping, loss, mtr_res)
    print("OK - All values were in the valid range")
    exit(0)


if __name__ == "__main__":
    main()
