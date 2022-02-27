import requests
import time
import os

reload_cmds = [
    "tmux new-session -d -s flamepaw",
    "tmux send-keys -t flamepaw ' cd ~/FatesList/modules/infra/flamepaw && ./flamepaw --cmd server; exec $SHELL' Enter"
]

while True:
    print("Flamepaw test begin")
    res = requests.get("https://api.fateslist.xyz/flamepaw/ping")
    if res.status_code == 408:
        print("Flamepaw is down")
        for cmd in reload_cmds:
            os.system(cmd)
    time.sleep(5)
