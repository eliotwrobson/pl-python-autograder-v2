import os

# Get current user and group IDs
# These will be queried by the test to verify privilege dropping
current_uid = os.getuid() if hasattr(os, "getuid") else None
current_euid = os.geteuid() if hasattr(os, "geteuid") else None
current_gid = os.getgid() if hasattr(os, "getgid") else None
current_egid = os.getegid() if hasattr(os, "getegid") else None
