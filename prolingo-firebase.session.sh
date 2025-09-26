# Set a custom session root path. Default is `$HOME`.
# Must be called before `initialize_session`.
session_root "~/Developer/420024-lab/prolingo-firebase/functions"

# Create session with specified name if it does not already exist. If no
# argument is given, session name will be based on layout file name.
if initialize_session "prolingo-firebase"; then
  tmux set-option -g default-size "$(tput cols)x$(tput lines)"
  new_window "prolingo"
  # new_window "server"
  # select_window 1
  run_cmd "firebase emulators:start --import db --export-on-exit"
  
  split_h 55
  # select_window 0
  run_cmd "nvim"
  run_cmd ":Neotree"
  # send_keys "C-m"

  # Create a new window inline within session layout definition.
  #new_window "misc"

  # Load a defined window layout.
  #load_window "example"

  # Select the default active window on session creation.
  #select_window 1

fi

# Finalize session creation and switch/attach to it.
finalize_and_go_to_session

