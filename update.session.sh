# Set a custom session root path. Default is `$HOME`.
# Must be called before `initialize_session`.
# session_root "~/Developer/420024-lab/prolingo-firebase/functions"

# Create session with specified name if it does not already exist. If no
# argument is given, session name will be based on layout file name.
if initialize_session "update"; then
  tmux set-option -g default-size "$(tput cols)x$(tput lines)"

  new_window "update"

  # Run the Python system updater script with virtual environment
  run_cmd "cd ~/.tmuxifier/layouts && source bin/activate && python3 system_updater.py && deactivate"

fi

# Finalize session creation and switch/attach to it.
finalize_and_go_to_session
