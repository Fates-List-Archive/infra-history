HISTCONTROL="ignorespace${HISTCONTROL:+:$HISTCONTROL}"
tmux kill-server
tmux new-session -d -s dragon 
tmux send-keys -t dragon 'cd ~/FatesList/modules/infra/dragon && ./dragon --cmd dragon.server; exec $SHELL' Enter
tmux new-session -d -s manager 
tmux send-keys -t manager 'dragon --cmd site.manager; exec $SHELL' Enter
tmux new-session -d -s mapleshade
tmux send-keys -t mapleshade 'cd ~/GitHub-Updates-Bot && source ~/.mapleshadecfg && npm start; exec $SHELL' Enter
tmux new-session -d -s main 
tmux send-keys -t main 'dragon --cmd site.run; exec $SHELL' Enter
export HISTCONTROL
