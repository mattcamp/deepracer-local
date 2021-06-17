Notes/Instructions on getting started for deepracer-local on Windows 10.

Tested on Windows 10, version 21H1, build 19043.985 on 2021-06-03

## Outcome:  
Windows Subsystem for Linux (WSL) v2, Ubuntu 18.04
--base setup, use TMUX for terminal viewer. Someone may addendum with additional instructions to support the gnome / x-viewer / vnc visual approaches, but this setup is enough to get started!

## Group Step 1 (powershell admin):
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

## Group Step 2 (must restart after step 1):
Download and run: https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi 

Powershell as admin:
wsl --set-default-version 2

## Group Step 3 install ubuntu 18.04 in WSL and docker-desktop with WSL integration:
Ubuntu 18.04 is the recommended for DeepRacer: Microsoft store, ‘get’ then ‘install’ https://www.microsoft.com/store/apps/9N9TNGVNDL3Q   
Launch after install, setup your default linux username/password.

In Docker Desktop, go to ‘gear /settings’ -> Resources -> WSL Integration -> turn on integration for Ubuntu-18.04
--verify, go into ubuntu terminal and type ‘docker --version’, if it returns correctly everything good!

Group Step 4 (in ubuntu terminal, install docker compose):
sudo curl -L https://github.com/docker/compose/releases/download/1.21.2/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose 

sudo chmod +x /usr/local/bin/docker-compose

docker-compose –version


Group Step 5 (in ubuntu terminal):
NOTE: the deepracer-local docker-compose.yaml expects a deepracer-robomaker:cpu-avx2 so downloading it explicitly.

git clone https://github.com/mattcamp/deepracer-local.git 
docker pull awsdeepracercommunity/deepracer-sagemaker:cpu
docker pull awsdeepracercommunity/deepracer-robomaker:cpu-avx2
docker pull mattcamp/dr-coach
docker pull minio/minio

cd deepracer-local (or where-ever you cloned it)

vi docker-compose.yaml
(‘i’ for insert mode of vi)
--modify entry at top to version : “3.3”
( escape then :wq! to write and quit vi)


vi config.env
(‘i’ for insert mode of vi)
--modify entry into ENABLE_LOCAL_DESKTOP=false
--modify entry into ENABLE_TMUX=true
--modify entry into ENABLE_GPU_TRAINING=false   #if you have good nvidia cards, can research more into this
( escape then :wq! to write and quit vi)

ONETIME SETUP: docker network create sagemaker-local


Ready to train!

./start-training.sh

…wait up to several hours, pending complexity, cpu, or if enabled gpu support with a good nvidia card…

If happy with the results and want to use it for future needs:
$deepracer-local: ./local-copy.sh mymodel_v2


deepracer-local/data/minio/bucket/current/model/*.pb


