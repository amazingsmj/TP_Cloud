"""
            Déploiement de modèles et clonage

    L'idée, est de déployer un modèle de VM à partir d'un fichier OVA pour permettre le clonage futur (quesion suivante), 
    puis de cloner le modèle produit pour créer plusieurs instances de VM.
    
"""

import json
import ssl
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import atexit
import time

def connect_to_vsphere(host, user, password):
    context = ssl._create_unverified_context()  # Ignorer les vérifications SSL
    service_instance = SmartConnect(host=host, user=user, pwd=password, sslContext=context)
    atexit.register(Disconnect, service_instance)
    print("Connected to vSphere")
    return service_instance

def deploy_template_vm(si, config, vm_folder, resource_pool, datastore):
    """Déploie le modèle de VM (template) à partir de l'OVA pour les futurs clonages."""
    ovf_manager = si.content.ovfManager

    # Lire le fichier OVA
    try:
        with open(config["ova_path"], 'r', encoding='utf-8') as ova_file:
            ovf_descriptor = ova_file.read()
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier OVA : {e}")
        return None

    # Créer une spécification d'importation
    import_spec_params = vim.OvfManager.CreateImportSpecParams()
    import_spec = ovf_manager.CreateImportSpec(ovf_descriptor, resource_pool, datastore, import_spec_params)

    if import_spec.error:
        for error in import_spec.error:
            print("Erreur lors de l'importation de l'OVA : %s" % error)
        return None

    # Lancer l'importation
    task = resource_pool.ImportVApp(import_spec.importSpec, vm_folder, config["template_vm_name"])
    print("Déploiement du modèle en cours...")

    # Attendre que la tâche se termine
    while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
        time.sleep(1)

    if task.info.state == vim.TaskInfo.State.success:
        print("Déploiement du modèle terminé avec succès !")
        return task.info.result  # Retourner la VM modèle
    else:
        print(f"Échec du déploiement du modèle : {task.info.error}")
        return None

def clone_vm(si, template_vm, new_vm_name, vm_folder, datastore):
    """Clone une VM depuis un modèle."""
    # Vérifier que le modèle est une VM arrêtée
    if template_vm.runtime.powerState != vim.VirtualMachinePowerState.poweredOff:
        print(f"Le modèle '{template_vm.name}' doit être arrêté pour le clonage.")
        return

    # Créer la spécification de clonage
    spec_clone = vim.vm.CloneSpec()
    spec_clone.location = vim.vm.RelocateSpec()
    spec_clone.location.datastore = datastore
    spec_clone.powerOn = True
    spec_clone.template = False

    # Démarrer le clonage
    task = template_vm.Clone(folder=vm_folder, name=new_vm_name, spec=spec_clone)
    print(f"Clonage de '{template_vm.name}' vers '{new_vm_name}' en cours...")

    # Attendre que le clonage soit terminé
    while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
        time.sleep(1)

    if task.info.state == vim.TaskInfo.State.success:
        print(f"VM '{new_vm_name}' clonée avec succès !")
    else:
        print(f"Échec du clonage de la VM : {task.info.error}")

def main():
    # Charger la configuration
    with open("./conf.json", "r") as f:
        config = json.load(f)

    si = connect_to_vsphere(config["vsphere_host"], config["vsphere_user"], config["vsphere_password"])
    vm_folder = si.content.rootFolder.childEntity[0].vmFolder
    resource_pool = si.content.rootFolder.childEntity[0].hostFolder.childEntity[0].resourcePool
    datastore = si.content.rootFolder.childEntity[0].datastore[0]

    # Déployer le modèle depuis l'OVA pour les clonages futurs
    template_vm = deploy_template_vm(si, config, vm_folder, resource_pool, datastore)
    if not template_vm:
        print("Échec du déploiement du modèle. Arrêt du processus.")
        return

    # Cloner le modèle pour déployer les instances supplémentaires
    for i in range(config["number_of_instances"]):
        new_vm_name = f"Cloned_VM_{i + 1}"
        clone_vm(si, template_vm, new_vm_name, vm_folder, datastore)

if __name__ == "__main__":
    main()
