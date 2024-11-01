"""
        Création de VM avec ISO

Ici, nous cherchons à créer une nouvelle VM avec des spécifications définies, configurer un CD-ROM avec une image 
ISO, puis démarrer la VM.

"""

import json
import ssl
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import atexit
import time

def connect_to_vsphere(host, user, password):
    context = ssl._create_unverified_context()
    service_instance = SmartConnect(host=host, user=user, pwd=password, sslContext=context)
    atexit.register(Disconnect, service_instance)
    print("Connected to vSphere")
    return service_instance

def create_dummy_vm(si, vm_name, vm_folder, resource_pool, datastore, ram_mb=2048, disk_gb=10):
    config = vim.vm.ConfigSpec()
    config.name = vm_name
    config.memoryMB = ram_mb
    config.numCPUs = 1
    config.guestId = 'otherGuest'  # Ou utilisez un ID de système d'exploitation spécifique
    config.files = vim.vm.FileInfo(vmPathName=f'[{datastore.name}]')
    
    # Créer un disque
    disk_spec = vim.vm.device.VirtualDeviceSpec()
    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    disk = vim.vm.device.VirtualDisk()
    disk.capacityInKB = disk_gb * 1024 * 1024  # Convertir Go en Ko
    disk.controllerKey = 1000
    disk.unitNumber = 0
    disk_spec.device = disk
    config.deviceChange = [disk_spec]

    task = vm_folder.CreateVM_Task(config=config, pool=resource_pool)
    print(f"Creating VM '{vm_name}'...")

    # Attendre que la tâche soit terminée
    while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
        time.sleep(1)

    if task.info.state == vim.TaskInfo.State.success:
        print(f"VM '{vm_name}' created successfully!")
    else:
        print(f"Failed to create VM: {task.info.error}")

def configure_cdrom(si, vm_name, iso_path):
    vm = None
    vm_folder = si.content.rootFolder.childEntity[0].vmFolder  # Supposons que le premier est le bon
    for vm in vm_folder.childEntity:
        if vm.name == vm_name:
            break

    if not vm:
        print(f"VM '{vm_name}' not found!")
        return

    # Configuration du CD-ROM
    cdrom_device = vim.vm.device.VirtualCdrom()
    cdrom_device.key = 200
    cdrom_device.controllerKey = 200
    cdrom_device.backing = vim.vm.device.VirtualCdromIsoBackingInfo()
    cdrom_device.backing.fileName = iso_path
    cdrom_device.backing.allowGuestControl = True
    cdrom_device.deviceInfo = vim.Description()
    cdrom_device.deviceInfo.summary = 'CD-ROM Drive'

    dev_changes = []
    dev_change_spec = vim.vm.device.VirtualDeviceSpec()
    dev_change_spec.device = cdrom_device
    dev_change_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    dev_changes.append(dev_change_spec)

    vm.ReconfigVM_Task(spec=vim.vm.ConfigSpec(deviceChange=dev_changes))
    print(f"CD-ROM for VM '{vm_name}' configured with ISO '{iso_path}'.")

def start_vm(si, vm_name):
    vm = None
    vm_folder = si.content.rootFolder.childEntity[0].vmFolder  # Supposons que le premier est le bon
    for vm in vm_folder.childEntity:
        if vm.name == vm_name:
            vm = vm
            break

    if not vm:
        print(f"VM '{vm_name}' not found!")
        return

    task = vm.PowerOn()
    print(f"Starting VM '{vm_name}'...")

    # Attendre que la tâche soit terminée
    while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
        time.sleep(1)

    if task.info.state == vim.TaskInfo.State.success:
        print(f"VM '{vm_name}' started successfully!")
    else:
        print(f"Failed to start VM: {task.info.error}")

def main():
    # Charger la configuration
    with open("./conf.json", "r") as f:
        config = json.load(f)

    si = connect_to_vsphere(config["vsphere_host"], config["vsphere_user"], config["vsphere_password"])
    
    vm_folder = si.content.rootFolder.childEntity[0].vmFolder  # Supposons que le premier est le bon
    resource_pool = si.content.rootFolder.childEntity[0].hostFolder.childEntity[0].resourcePool  # Pareil pour le pool
    datastore = si.content.rootFolder.childEntity[0].datastore[0]  # Supposons que c'est le bon datastore

    # Créer la VM vide avec les paramètres du fichier de configuration
    create_dummy_vm(si, "MyNewVM", vm_folder, resource_pool, datastore, ram_mb=2048, disk_gb=10)

    # Configurer le CD-ROM avec le chemin spécifié dans le fichier de configuration
    configure_cdrom(si, "MyNewVM", config["iso_path"])

    # Démarrer la VM
    start_vm(si, "MyNewVM")

if __name__ == "__main__":
    main()
