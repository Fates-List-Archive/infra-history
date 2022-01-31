HISTCONTROL="ignorespace${HISTCONTROL:+:$HISTCONTROL}"
ulimit -Sv 3000000 # Force set 3gb ram limit
KILL=1 flamepaw --cmd site.reload 
tmux kill-server
#tmux new-session -d -s flamepaw 
#tmux send-keys -t flamepaw ' cd ~/FatesList/modules/infra/flamepaw && ./flamepaw --cmd server; exec $SHELL' Enter
tmux new-session -d -s manager 
tmux send-keys -t manager ' flamepaw --cmd site.manager; exec $SHELL' Enter
tmux new-session -d -s main 
tmux send-keys -t main ' flamepaw --cmd site.run; exec $SHELL' Enter
cpulimit -e flamepaw -l 80 &
export HISTCONTROL
echo "Run 'systemd-run --scope -p CPUQuota=50% modules/infra/flamepaw/flamepaw --cmd server' to stop memory leaks"
