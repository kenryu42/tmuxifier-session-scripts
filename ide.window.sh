# Set window root path. Default is `$session_root`.
# Must be called before `new_window`.
#window_root "~/Projects/ide"

# Create new window. If no argument is given, window name will be based on
# layout file name.
window_root "$PWD"

tmux set-option -g default-size "$(tput cols)x$(tput lines)"
new_window ${PWD##*/}

run_cmd "tmux split-window -c '#{pane_current_path}' -l 15"
run_cmd "tmux select-pane -U"

run_cmd "nvim"
run_cmd ":Neotree"
