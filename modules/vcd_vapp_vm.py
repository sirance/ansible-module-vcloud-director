# Copyright © 2018 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2-Clause

# !/usr/bin/python

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
client: vcd_vapp_vm
short_description: This module is to create virtual machines under provided vapp
version_added: "2.4"
description:
    - "This module is to to create virtual machines under provided vapp"
options:
    user:
        description:
            - vCloud Director user name
        required: false
    password:
        description:
            - vCloud Director user password
        required: false
    host:
        description:
            - vCloud Director host address
        required: false
    org:
        description:
            - Organization name on vCloud Director to access
        required: false
    api_version:
        description:
            - Pyvcloud API version
        required: false
    verify_ssl_certs:
        description:
            - whether to use secure connection to vCloud Director host
        required: false
    target_vm_name:
        description:
            - target VM name
        required: false
    target_vapp:
        description:
            - target vApp name
        required: false
    target_vdc:
        description:
            - target VDC
        required: false
    source_vapp:
        description:
            - source vApp name
        required: false
    source_vm_name:
        description:
            - source VM name
        required: false
    source_catalog_name:
        description:
            - source catalog name
        required: false
    source_template_name:
        description:
            - source template name
        required: false
    hostname:
        description:
            - target guest hostname
        required: false
    vmpassword:
        description:
            - set the administrator password for target machine
        required: false
    vmpassword_auto:
        description:
            - "true"/"false", autogenerate administrator password
        required: false
    vmpassword_reset:
        description:
            - "true" if the administrator password for this virtual machine must be reset after first use else "false"
        required: false
    cust_script:
        description:
            - script to run on guest customization
        required: false
    network:
        description:
            - Name of the vApp network to connect. If omitted, the VM won't be connected to any network
        required: false
    storage_profile:
        description:
            - the name of the storage profile to be used for this VM
        required: false
    state:
        description:
            - state of new virtual machines ('present'/'absent').One from state or operation has to be provided.
        required: false
    operation:
        description:
            - operations performed over new vapp ('poweron'/'poweroff'/'modifycpu'/'modifymemory'/'reloadvm').One from state or operation has to be provided.
        required: false
    all_eulas_accepted:
        description:
            - "true" / "false"
        required: false
    ip_allocation_mode:
        description:
            - "dhcp"
        required: false
    virtual_cpus:
        description:
            - Number of virtual cpus
        required: false
    cores_per_socket:
        description:
            - Number of cores per socket
        required: false
    memory:
        description:
            - memory size in MB
        required: false

author:
    - mtaneja@vmware.com
'''

EXAMPLES = '''
- name: Test with a message
  vcd_vapp_vm:
    user: terraform
    password: abcd
    host: csa.sandbox.org
    org: Terraform
    api_version: 30
    verify_ssl_certs: False
    target_vm_name = "vm_name"
    target_vapp = "vapp1"
    target_vdc = "vdc1"
    source_vapp = "vapp1"
    source_vm_name = "sourcevm1"
    hostname = "vcdcell"
    vmpassword = "rootpass"
    vmpassword_auto = "false"
    vmpassword_reset = "false"
    cust_script = "/home/setup.sh"
    network = "MGMT"
    storage_profile = "PERFORMACE_1"
    state = "present"
    all_eulas_accepted = "true"
'''

RETURN = '''
result: success/failure message relates to vapp_vm operation
'''

import json
from lxml import etree
from pyvcloud.vcd.vm import VM
from pyvcloud.vcd.org import Org
from pyvcloud.vcd.vdc import VDC
from pyvcloud.vcd.vapp import VApp
from pyvcloud.vcd.client import EntityType
from ansible.module_utils.vcd import VcdAnsibleModule
from pyvcloud.vcd.exceptions import EntityNotFoundException, OperationNotSupportedException


VAPP_VM_STATES = ['present', 'absent', 'update']
VAPP_VM_OPERATIONS = ['poweron', 'poweroff', 'reloadvm',
                      'deploy', 'undeploy']


def vapp_vm_argument_spec():
    return dict(
        target_vm_name=dict(type='str', required=False),
        target_vapp=dict(type='str', required=False),
        target_vdc=dict(type='str', required=False),
        source_vdc=dict(type='str', required=False),
        source_vapp=dict(type='str', required=False),
        source_catalog_name=dict(type='str', required=False),
        source_template_name=dict(type='str', required=False),
        source_vm_name=dict(type='str', required=False),
        hostname=dict(type='str', required=False),
        vmpassword=dict(type='str', required=False),
        vmpassword_auto=dict(type='bool', required=False),
        vmpassword_reset=dict(type='bool', required=False),
        cust_script=dict(type='str', required=False),
        network=dict(type='str', required=False),
        storage_profile=dict(type='str', required=False),
        all_eulas_accepted=dict(type='bool', required=False),
        ip_allocation_mode=dict(type='str', required=False),
        virtual_cpus=dict(type='int', required=False),
        cores_per_socket=dict(type='int', required=False),
        memory=dict(type='str', required=False),
        power_on=dict(type='bool', required=False),
        state=dict(choices=VAPP_VM_STATES, required=False),
        operation=dict(choices=VAPP_VM_OPERATIONS, required=False)
    )


class VappVM(VcdAnsibleModule):
    def __init__(self, **kwargs):
        super(VappVM, self).__init__(**kwargs)
        vapp_resource = self.get_target_resource()
        self.vapp = VApp(self.client, resource=vapp_resource)

    def manage_states(self):
        state = self.params.get('state')
        if state == "present":
            return self.add_vm()

        if state == "absent":
            return self.delete_vm()

        if state == "update":
            return self.update_vm()

    def manage_operations(self):
        operation = self.params.get('operation')
        if operation == "poweron":
            return self.power_on_vm()

        if operation == "poweroff":
            return self.power_off_vm()

        if operation == "reloadvm":
            return self.reload_vm()

        if operation == "deploy":
            return self.deploy_vm()

        if operation == "undeploy":
            return self.undeploy_vm()

    def get_source_resource(self):
        source_catalog_name = self.params.get('source_catalog_name')
        source_template_name = self.params.get('source_template_name')
        source_vdc = self.params.get('source_vdc')
        source_vapp = self.params.get('source_vapp')
        org_resource = Org(self.client, resource=self.client.get_org())
        source_vapp_resource = None

        if source_vapp:
            source_vdc_resource = VDC(
                self.client, resource=org_resource.get_vdc(source_vdc))
            source_vapp_resource_href = source_vdc_resource.get_resource_href(
                name=source_vapp, entity_type=EntityType.VAPP)
            source_vapp_resource = self.client.get_resource(
                source_vapp_resource_href)

        if source_catalog_name:
            catalog_item = org_resource.get_catalog_item(
                source_catalog_name, source_template_name)
            source_vapp_resource = self.client.get_resource(
                catalog_item.Entity.get('href'))

        return source_vapp_resource

    def get_target_resource(self):
        target_vapp = self.params.get('target_vapp')
        target_vdc = self.params.get('target_vdc')
        org_resource = Org(self.client, resource=self.client.get_org())
        target_vapp_resource = None

        target_vdc_resource = VDC(
            self.client, resource=org_resource.get_vdc(target_vdc))
        target_vapp_resource = target_vdc_resource.get_vapp(target_vapp)

        return target_vapp_resource

    def get_vm(self):
        vapp_vm_resource = self.vapp.get_vm(self.params.get('target_vm_name'))

        return VM(self.client, resource=vapp_vm_resource)

    def add_vm(self):
        params = self.params
        source_vapp_resource = self.get_source_resource()
        target_vm_name = params.get('target_vm_name')
        source_vm_name = params.get('source_vm_name')
        hostname = params.get('hostname')
        vmpassword = params.get('vmpassword')
        vmpassword_auto = params.get('vmpassword_auto')
        vmpassword_reset = params.get('vmpassword_reset')
        network = params.get('network')
        all_eulas_accepted = params.get('all_eulas_accepted', True)
        power_on = params.get('power_on', True)
        ip_allocation_mode = params.get('ip_allocation_mode')
        # cust_script = params.get('cust_script')
        # storage_profile = params.get('storage_profile')
        response = dict()
        response['changed'] = False

        try:
            self.get_vm()
        except EntityNotFoundException:
            specs = [{
                'source_vm_name': source_vm_name,
                'vapp': source_vapp_resource,
                'target_vm_name': target_vm_name,
                'hostname': hostname,
                'password': vmpassword,
                'password_auto': vmpassword_auto,
                'password_reset': vmpassword_reset,
                'ip_allocation_mode': ip_allocation_mode,
                'network': network,
                # 'cust_script': cust_script,
                # 'storage_profile': json.loads(storage_profile)
            }]
            add_vms_task = self.vapp.add_vms(specs, power_on=power_on,
                                             all_eulas_accepted=all_eulas_accepted)
            self.execute_task(add_vms_task)
            response['msg'] = 'Vapp VM {} has been created.'.format(
                target_vm_name)
            response['changed'] = True
        else:
            response['msg'] = 'Vapp VM {} is already present.'.format(
                target_vm_name)

        return response

    def delete_vm(self):
        vm_name = self.params.get('target_vm_name')
        response = dict()
        response['changed'] = False

        try:
            self.get_vm()
        except EntityNotFoundException:
            response['msg'] = 'Vapp VM {} is not present.'.format(vm_name)
        else:
            self.undeploy_vm()
            delete_vms_task = self.vapp.delete_vms([vm_name])
            self.execute_task(delete_vms_task)
            response['msg'] = 'Vapp VM {} has been deleted.'.format(vm_name)
            response['changed'] = True

        return response

    def update_vm(self):
        vm_name = self.params.get('target_vm_name')
        response = dict()
        response['changed'] = False

        if self.params.get("virtual_cpus"):
            self.update_vm_cpu()
            response['changed'] = True

        if self.params.get("memory"):
            self.update_vm_memory()
            response['changed'] = True

        response['msg'] = 'Vapp VM {} has been updated.'.format(vm_name)

        return response

    def update_vm_cpu(self):
        virtual_cpus = self.params.get('virtual_cpus')
        cores_per_socket = self.params.get('cores_per_socket')

        vm = self.get_vm()
        update_cpu_task = vm.modify_cpu(virtual_cpus, cores_per_socket)

        return self.execute_task(update_cpu_task)

    def update_vm_memory(self):
        memory = self.params.get('memory')

        vm = self.get_vm()
        update_memory_task = vm.modify_memory(memory)

        return self.execute_task(update_memory_task)

    def power_on_vm(self):
        vm_name = self.params.get('target_vm_name')
        response = dict()
        response['changed'] = False

        try:
            vm = self.get_vm()
            power_on_task = vm.power_on()
            self.execute_task(power_on_task)
            response['msg'] = 'Vapp VM {} has been powered on.'.format(vm_name)
            response['changed'] = True
        except OperationNotSupportedException:
            response['msg'] = 'Vapp VM {} is already powered on.'.format(
                vm_name)

        return response

    def power_off_vm(self,):
        vm_name = self.params.get('target_vm_name')
        response = dict()
        response['changed'] = False

        try:
            vm = self.get_vm()
            power_off_task = vm.power_off()
            self.execute_task(power_off_task)
            response['msg'] = 'Vapp VM {} has been powered off.'.format(
                vm_name)
            response['changed'] = True
        except OperationNotSupportedException:
            response['msg'] = 'Vapp VM {} is already powered off.'.format(
                vm_name)

        return response

    def reload_vm(self):
        vm_name = self.params.get('target_vm_name')
        response = dict()
        response['changed'] = False

        vm = self.get_vm()
        vm.reload()
        response['msg'] = 'Vapp VM {} has been reloaded.'.format(vm_name)
        response['changed'] = True

        return response

    def deploy_vm(self):
        vm_name = self.params.get('target_vm_name')
        response = dict()
        response['changed'] = False

        try:
            vm = self.get_vm()
            deploy_vm_task = vm.deploy()
            self.execute_task(deploy_vm_task)
            response['msg'] = 'Vapp VM {} has been deployed.'.format(vm_name)
            response['changed'] = True
        except OperationNotSupportedException:
            response['msg'] = 'Vapp VM {} is already deployed.'.format(vm_name)

        return response

    def undeploy_vm(self):
        vm_name = self.params.get('target_vm_name')
        response = dict()
        response['changed'] = False

        try:
            vm = self.get_vm()
            undeploy_vm_task = vm.undeploy()
            self.execute_task(undeploy_vm_task)
            response['msg'] = 'Vapp VM {} has been undeployed.'.format(vm_name)
            response['changed'] = True
        except OperationNotSupportedException:
            response['msg'] = 'Vapp VM {} is already undeployed.'.format(
                vm_name)

        return response


def main():
    argument_spec = vapp_vm_argument_spec()
    response = dict(
        msg=dict(type='str')
    )
    module = VappVM(argument_spec=argument_spec, supports_check_mode=True)

    # try:
    if module.params.get('state'):
        response = module.manage_states()
    elif module.params.get('operation'):
        response = module.manage_operations()
    else:
        raise Exception('One of the state/operation should be provided.')

    # except Exception as error:
    #     response['msg'] = error.__str__()
    #     module.fail_json(**response)

    module.exit_json(**response)


if __name__ == '__main__':
    main()
