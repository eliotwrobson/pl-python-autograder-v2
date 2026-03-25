def get_cwd():
    import os  # 'os' is in the default blacklist — should raise ImportError at call time
    return os.getcwd()
