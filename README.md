# Creating an NSO service - from template to nano
This repository contains the code used in the NSO Developer Days 2020 (recorded) Live session
[Building a Service - from Template to Reactive FastMap to Nano services](https://youtu.be/OIzBhzdAC9M)

There are four versions of the package, presented in the order of the live session:
1. simple-template-service - A simple template service without reactive fastmap
1. rfm-template-service - A reactive fastmap template service
1. rfm-python-service - A reactive fastmap python service
1. nano-service - A nano-service

# Pre-requisites
The following NEDs are required for the services to run:
* ESC NED: 5.1.0
* OPENSTACK-COS: 4.2.13
* CISCO-IOS: 6.56.1

And the function pack NFVO:
* CISCO-ETSI-NFVO: 4.3

The code in the services are just example code, and is not intended
to work as generic solution. There are a lot of hard coded values and
assumption made in the code that worked in the environment used in the demo.

View the code as inspiration for your service creation process, not as something
you should actually use without modifications.

That said, if you do want to be able to compile and run the services, you would
need the NFVO function pack, the NEDs listed above, and an environment with Cisco
ESC running on Openstack.
