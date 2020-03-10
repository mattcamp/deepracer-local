import docker
import pprint
import time

client = docker.from_env()

ready = False
sagemaker = None
robomaker = None

while not ready:
    for container in client.containers.list():
        if "sagemaker" in container.attrs['Config']['Image']:
            sagemaker = container
            print("Sagemaker: %s" % sagemaker.attrs['State']['Status'])

        if "robomaker" in container.attrs['Config']['Image']:
            robomaker = container
            print("Robomaker: %s" % robomaker.attrs['State']['Status'])

    if (sagemaker != None) and (robomaker != None):
        ready = True
        print("Ready")
    else:
        if robomaker is None:
            print("Robomaker not yet running")
        if sagemaker is None:
            print("Sagemaker not yet running")
        time.sleep(1)


