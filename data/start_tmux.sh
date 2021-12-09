tmux new-session -d -s dragon 'cd ~/FatesList/modules/infra/dragon && ./dragon --cmd dragon.server'
tmux new-session -d -s manager 'dragon --cmd site.manager'
tmux new-session -d -s mapleshade 'cd ~/GitHub-Updates-Bot && source ~/.mapleshadecfg && npm start'
tmux new-session -d -s main 'dragon --cmd site.run'
