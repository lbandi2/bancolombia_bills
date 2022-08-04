#!/bin/bash

mkdir -p logs
cd /home/sergio/scripts/bancolombia_mails/
. ./env/bin/activate
/home/sergio/scripts/bancolombia_mails/env/bin/python3 /home/sergio/scripts/bancolombia_mails/main.py >> logs/bancolombia_mails-"`date +"%Y-%m-%d_%H.%M.%S"`".log 2>&1
deactivate
