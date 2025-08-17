# envstack_completions.sh
#
# Copyright (c) 2025, Ryan Galloway (ryan@rsgalloway.com)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  - Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
#  - Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
#  - Neither the name of the software nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# This script provides tab completion for the `envstack` command.
#
# INSTALLATION:
# copy to /etc/bash_completion.d/envstack or source in your .bashrc
#

_envstack_completions() {
    local cur="${COMP_WORDS[COMP_CWORD]}"

    # These are the valid completions for envstack's positional argument(s).
    # You can hardcode them or dynamically generate them.
    # local options="test build deploy"

    # Extract the directories from the $ENVPATH variable
    IFS=':' read -ra directories <<< "$ENVPATH"

    # Initialize an empty array to store the basenames
    local basenames=()

    # Iterate over each directory
    for directory in "${directories[@]}"; do
        # Check if the directory exists
        if [[ -d "$directory" ]]; then
            # Get the basenames of the files in the directory and append them to the array
            basenames+=($(basename -a "$directory"/* | sed 's/\.[^.]*$//'))
        fi
    done

    # Set options to the basenames
    local options="${basenames[@]}"

    # Tell Bash which options match the current word being typed
    COMPREPLY=( $(compgen -W "${options}" -- "${cur}") )
}

# Associate the function `_envstack_completions` with the command `envstack`
complete -F _envstack_completions envstack