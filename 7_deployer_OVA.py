"""
                Déploiement d'OVA

Ici, on se cherche à se connecter à un serveur vSphere, lire un fichier OVA, et déployer une machine virtuelle
    (VM) à partir de ce fichier.
"""

import json
import ssl
import base64
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import atexit
import time

def connect_to_vsphere(host, user, password):
    try:
        # Désactiver la validation du certificat SSL
        service_instance = SmartConnect(host=host, user=user, pwd=password, disableSslCertValidation=True)
        atexit.register(Disconnect, service_instance)
        print("Connected to vSphere")
        return service_instance
    except Exception as e:
        print(f"Erreur de connexion à vSphere : {e}")
        return None

def deploy_ova(si, config):
    try:
        data_center = si.content.rootFolder.childEntity[0]
        vm_folder = data_center.vmFolder
        resource_pool = data_center.hostFolder.childEntity[0].resourcePool
        datastore = data_center.datastore[0]

        ovf_manager = si.content.ovfManager

        # Lire et encoder le fichier OVA en base64
        with open(config["ova_path"], 'rb') as ova_file:
            ovf_descriptor = base64.b64encode(ova_file.read()).decode('utf-8')

        import_spec_params = vim.OvfManager.CreateImportSpecParams()
        import_spec = ovf_manager.CreateImportSpec(ovf_descriptor, resource_pool, datastore, import_spec_params)

        # Vérifier les erreurs d'importation
        if import_spec.error:
            for error in import_spec.error:
                print("Erreur lors de l'importation de l'OVA : %s" % error)
            return

        task = resource_pool.ImportVApp(import_spec.importSpec, vm_folder)
        print("Déploiement en cours...")

        while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
            time.sleep(1)

        if task.info.state == vim.TaskInfo.State.success:
            print("Déploiement terminé avec succès !")
        else:
            print(f"Échec du déploiement : {task.info.error}")

    except Exception as e:
        print(f"Erreur lors du déploiement de l'OVA : {e}")

def main():
    try:
        with open("./conf.json", "r") as f:
            config = json.load(f)

        si = connect_to_vsphere(config["vsphere_host"], config["vsphere_user"], config["vsphere_password"])

        if si:
            for i in range(config["number_of_instances"]):
                new_vm_name = f"Deployed_VM_{i + 1}"
                print(f"Déploiement de l'instance {new_vm_name}...")
                deploy_ova(si, config)

    except Exception as e:
        print(f"Erreur dans la fonction principale : {e}")

if __name__ == "__main__":
    main()
