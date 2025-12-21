import os

# Get current user and group IDs
# These will be queried by the test to verify privilege dropping
# On Unix these functions always exist, on Windows the sandbox won't start
current_uid = os.getuid()
current_euid = os.geteuid()
current_gid = os.getgid()
current_egid = os.getegid()
