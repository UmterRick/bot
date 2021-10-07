import os
from utils import ROOT_DIR
import datetime
path = ROOT_DIR + "/log/"

logs = (os.listdir(path))
for file in logs:
    with open(ROOT_DIR + '/log/' + file, 'r+') as log_file:
        log_file.truncate(0)

with open(ROOT_DIR + '/log/main.log', 'w') as file:
    file.write(f"{datetime.datetime.now()} - ALL LOGS FILE WAS CLEARED BY SCRIPT")
