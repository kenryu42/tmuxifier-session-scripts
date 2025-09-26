# Set a custom session root path. Default is `$HOME`.
# Must be called before `initialize_session`.
session_root "$PWD"

if initialize_session ${PWD##*/}; then

  tmux set-option -g default-size "$(tput cols)x$(tput lines)"
  new_window ${PWD##*/}

  run_cmd "tmux split-window -c '#{pane_current_path}' -l 15"
  run_cmd "tmux select-pane -U"

  run_cmd "nvim"
  run_cmd ":Neotree"
fi

finalize_and_go_to_session
