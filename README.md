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

### Output + Performance Data
The plugin outputs the mtr results for the different hops on the routing path.
The plugin also prints out the latency (rta) and package loss (pl) as performance data.
So the values for latency and package loss will then be shown as performance data in your monitoring system 
after the check was executed.
The performance data are always printed, also when the check fails.
In the following there is an example of the output of the check plugin:

```shell
OK - All values were in the valid range
Hops:
1. 1.2.3.4 0.0% 10 3.234 15.401 5.308 59.167 10.101
2. 2.3.4.5 0.0% 10 1.783 2.097 1.365 5.015 10.73
3. 3.4.5.6 0.0% 10 4.485 4.611 4.367 5.143 0.219
4. 4.5.6.7 0.0% 10 49.007 9.351 4.832 49.007 13.933
5. 5.6.7.8 0.0% 10 8.936 8.999 8.766 9.104 0.111
6. 6.7.8.9 0.0% 10 9.425 9.981 9.425 10.98 0.482
7. 7.8.9.10 0.0% 10 8.89 8.88 8.797 8.925 0.041 | 'hop_1.2.3.4_rta'=10.401;; 'hop_1.2.3.4_pl'=0.0;; 'hop_2.3.4.5_rta'=1.097;; 'hop_2.3.4.5_pl'=0.0;; 'hop_3.4.5.6_rta'=4.611;; 'hop_3.4.5.6_pl'=0.0;; 'hop_4.5.6.7_rta'=9.351;; 'hop_4.5.6.7_pl'=0.0;; 'hop_5.6.7.8_rta'=8.999;; 'hop_5.6.7.8_pl'=0.0;; 'hop_6.7.8.9_rta'=9.981;; 'hop_6.7.8.9_pl'=0.0;; 'hop_7.8.9.10_rta'=8.88;; 'hop_7.8.9.10_pl'=0.0;;
```


## Dependencies
The script has no dependencies, all imported libraries are available from the python
standard library.