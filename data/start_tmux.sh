HISTCONTROL="ignorespace${HISTCONTROL:+:$HISTCONTROL}"
KILL=1 flamepaw --cmd site.reload 
tmux kill-server
tmux new-session -d -s flamepaw 
tmux send-keys -t flamepaw ' cd ~/FatesList/modules/infra/flamepaw && ./flamepaw --cmd server; exec $SHELL' Enter
tmux new-session -d -s manager 
tmux send-keys -t manager ' flamepaw --cmd site.manager; exec $SHELL' Enter
tmux new-session -d -s mapleshade
tmux send-keys -t mapleshade ' cd ~/GitHub-Updates-Bot && source ~/.mapleshadecfg && npm start; exec $SHELL' Enter
tmux new-session -d -s main 
tmux send-keys -t main ' flamepaw --cmd site.run; exec $SHELL' Enter
export HISTCONTROL
