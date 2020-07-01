# -*- mode: python; python-indent: 4 -*-
import ncs
from ncs.application import Service, PlanComponent

class ServiceCallbacks(Service):
    @Service.create
    def cb_create(self, tctx, root, service, proplist):
        template = ncs.template.Template(service)
        variables = ncs.template.Variables()

        # 1 Create initial PLAN states for our service
        plan = PlanComponent(service, "self", "ncs:self")
        plan.append_state("ncs:init")
        plan.append_state("ourservice-python:allocation")
        plan.append_state("ourservice-python:vm-run")
        plan.append_state("ourservice-python:vm-config")
        plan.append_state("ncs:ready")
        plan.set_reached("ncs:init")

        # 2 Create allocation
        template.apply('ourservice-python-ro-template')
        # if no RO, create kicker on ro result

        # 3 Wait for allocation to be ready
        if not is_allocation_ready(tctx, service.allocation):
            template.apply('ourservice-python-ro-kicker-template')
            return
        plan.set_reached("ourservice-python:allocation")

        # 4 Get allocation response data and use it to instantiate a VNF-INFO
        host, vnfm = get_allocation_info(tctx, service.allocation)
        vnfinfo = "{}-csr".format(service.name)
        variables.add("HOST", host)
        variables.add("VNFM", vnfm)
        variables.add("VNF", vnfinfo)
        template.apply('ourservice-python-vnf-info-template', variables)

        # 5 Wait for the VNF to be up and running
        if not is_vnf_ready(root, vnfinfo):
            template.apply('ourservice-python-vnf-info-kicker-template')
            return

        # 6 Configure the device and update our PLAN that the device is
        # up and configured
        plan.set_reached("ourservice-python:vm-run")
        template.apply('ourservice-python-csr-template')
        plan.set_reached("ourservice-python:vm-config")

        # 7 Fetch some operational data from the device and store it in our service
        info = VnfInfo(vnfinfo, root)
        device = iter(info.get_created_devices_per_vdu()['CSR']).next()
        for i in device.interface:
            s_interface = service.operdata.GigabitEthernet.create(i.nic_id+1)
            s_interface.address = i.ip_address
            s_interface.mac = i.mac_address
            s_interface.gateway = i.gateway
        # Mark service ready
        plan.set_reached("ncs:ready")

# ---------------------------------------------
# COMPONENT THREAD THAT WILL BE STARTED BY NCS.
# ---------------------------------------------


class Main(ncs.application.Application):
    def setup(self):
        self.log.info('Main RUNNING')
        self.register_service(
            'ourservice-python-servicepoint', ServiceCallbacks)

    def teardown(self):
        self.log.info('Main FINISHED')


class InstanceError(Exception):
    pass


class VnfInfo(object):
    def __init__(self, vnf_info_name, transOrRoot):
        self.name = vnf_info_name
        if type(transOrRoot) is ncs.maagic.Root:
            self.root = transOrRoot
        elif type(transOrRoot) is ncs.maapi.Transaction:
            self.root = ncs.maagic.get_root(Transaction)
        if not self.root.nfv__nfv.vnf_info_plan.exists(vnf_info_name):
            raise InstanceError("no such instance")

        self.deployment_name = self._get_deployment_name()
        self.deployment_result = self._get_deployment_result()
        self.vm_groups = self.deployment_result.vm_group

    def get_vm_group_devices(self, vm_group):
        return self.vm_groups[vm_group].vm_device

    def get_vdu_vm_group(self, vdu):
        return self.vm_groups["{}-{}".format(self.name, vdu)]

    def get_vm_group(self, name):
        return self.vm_groups[name]

    def get_created_devices_per_vdu(self):
        devices = {}
        for vmg in self.vm_groups:
            devices[vmg.vdu] = vmg.vm_device
        return devices

    def get_created_nso_devices_per_vdu(self):
        devices = self.get_created_devices_per_vdu()
        nso_devices = {}
        for key, devs in devices.items():
            for d in devs:
                nso_devices[key] = d.device_name
        return nso_devices

    def get_all_created_nso_devices(self):
        devices = self.get_created_nso_devices_per_vdu()
        return list(devices.values())

    def is_vnf_plan_ready(self):
        return self.root.nfv__nfv.cisco_nfvo__vnf_info_plan[self.name].plan.component['ncs:self', 'self'].state['ncs:ready'].status == "reached"

    def _get_deployment_name(self):
        plan = self.root.nfv__nfv.cisco_nfvo__vnf_info_plan[self.name].plan
        plist = plan.component['ncs:self',
                               'self'].private.property_list.property
        return plist['DEPLOYMENT_ID'].value

    def _get_deployment_result(self):
        return self.root.nfv__nfv.cisco_nfvo__internal.netconf_deployment_result[self.deployment_name]


def is_allocation_ready(tctx, allocation_id):
    with ncs.maapi.single_read_trans(tctx.username, "system", db=ncs.OPERATIONAL) as th:
        allocations = ncs.maagic.get_root(
            th).nfv__nfv.cisco_nfvo_ro__resource_orchestration.allocation
        if allocation_id in allocations:
            return allocations[allocation_id].response.response == "ok"
        return False

def get_allocation_info(tctx, allocation_id):
    with ncs.maapi.single_read_trans(tctx.username, "system",
                                     db=ncs.OPERATIONAL) as th:
        allocation = ncs.maagic.get_root(
            th).nfv__nfv.cisco_nfvo_ro__resource_orchestration.allocation[allocation_id]
        result = allocation.response.ok.vdu['none', 'CSR1kv', 'CSR']
        return (result.virtual_compute.hostname, result.virtual_compute.vnfm)

def is_vnf_ready(root, vnfinfo):
    try:
        info = VnfInfo(vnfinfo, root)
        return info.is_vnf_plan_ready()
    except InstanceError:
        return False
