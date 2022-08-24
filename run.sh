#!/bin/bash

mkdir -p logs
cd /home/sergio/scripts/bancolombia_bills/
find logs -type f -mtime +30 -delete
. ./env/bin/activate
/home/sergio/scripts/bancolombia_bills/env/bin/python3 /home/sergio/scripts/bancolombia_bills/main.py >> logs/bancolombia_bills-"`date +"%Y-%m-%d_%H.%M.%S"`".log 2>&1
deactivate
