# check_mtr

Check_mtr is a Nagios compatible monitoring plugin written in Python. It compares values retrieved from mtr, 
like average latency and package loss, to the expected values given to the script by the CLI. If any value does not meet the
expectations it returns CRITICAL (exit code 2).

There are three different values that the plugin is able to check. Every value has a different CLI option. If the option
is given then the value will be checked, otherwise it will not be checked.

## Usage

|                          Option                                 |         Description                                     |      required?              |            
|-----------------------------------------------------------------|---------------------------------------------------------|-----------------------------|
| -h                                                              | Help                                                    | ❌                          |
| -H/--host <host>                                                | The host to run mtr on                                  | ✅                          |
| -j/--jumps <routing regex>                                      | The routing regex that should match the routing path    | ❌                          |
| -l/--latency <latency>                                          | The maximum expected latency (ms)                       | ❌                          |
| -p/--packetloss <packet loss>                                   | The maximum expected packet loss (%)                    | ❌                          |
| -r/--routers                                                    | The routers on the routing path (Order is unimportant)  | ❌                          |
| -4/--ipv4                                                       | Use IPv4 to execute mtr                                 | ❌                          |
| -6/--ipv6                                                       | Use IPv6 to execute mtr                                 | ❌                          |


At least one of the options -j, -l and -p must be set, because otherwise nothing will be checked.
In this case the script returns UNKNOWN (exit code 3).
By default mtr is executed with IPv4, if you want to execute it with IPv6 add the -6/--ipv6 flag to the CLI.
If by accident both are given, then IPv4 will be used.

The latency and packet loss must be smaller than the maximum expected value for the check to be successful.
The routing path is checked by looking at the routing regex and then decide whether the regex matches the actual
routing path (returned by mtr) or not.

### Example:
```shell
python3 check_mtr.py -H example.com -l 100 -p 5 -j "*1-5,12.13.14.15,*1,123.124.125.126[15ms:1%]" -r "[123.124.125.126, 12.13.14.15]"
```

## Routing Regex
The routing regex can be build by the following rules: 

1. **routing** := **routing**,**routing** | **wildcard** | \<router address\>**values**
2. **wildcard** := * | *\<int\> | *\<int\> - \<int\>
3. **values** := [**latency**:**package loss**] | Ɛ
3. **latency** := \<int\> # in ms
4. **package loss** := \<int\> # in %

**A router address can be an IP or a hostname**

If the latency and package loss are given after a hostname in the regex then these are the maximum values
for latency and package loss that this host may have. If the actual values exceed these expected ones,
the plugin will return CRITICAL.

### Meaning of the wildcard cases:
1. \* = Any number of unspecified router addresses may follow
2. \*1 = One unspecified router address may follow
3. \*1-3 = One to three unspecified router addresses may follow

You are also able to simply hardcode expected routes by only using router addresses concatenated
with ","


## Dependencies
The script has no dependencies, all imported libraries are available from the python
standard library.