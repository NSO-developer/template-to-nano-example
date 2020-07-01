# -*- mode: python; python-indent: 4 -*-
import ncs


class ComponentCallback(ncs.application.NanoService):
    """
    General handler for components.
    """
    @ncs.application.NanoService.create
    def cb_nano_create(self, tctx, root, service, plan, component, state,
                       opaque, comp_vars):
        comp_vars = dict(comp_vars)
        # The nano service is nice enough to give us all the variables it created
        info = vnfInfo(comp_vars['VNF'], root)
        device = iter(info.get_created_devices_per_vdu()['CSR']).next()
        for i in device.interface:
            s_interface = service.operdata.GigabitEthernet.create(i.nic_id+1)
            s_interface.address = i.ip_address
            s_interface.mac = i.mac_address
            s_interface.gateway = i.gateway


class Main(ncs.application.Application):
    def setup(self):
        self.log.info('Main RUNNING')
        # self.register_service('ourservice-nano-servicepoint', ServiceCallbacks)
        self.register_nano_service("ourservice-nano-servicepoint",
                                   "ncs:self",
                                   "ourservice-nano:vm-config",
                                   ComponentCallback)

    def teardown(self):
        self.log.info('Main FINISHED')


class InstanceError(Exception):
    pass


class vnfInfo(object):
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
