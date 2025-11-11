# Global scope print statements
print("Global print: Loading student code...")
print("Global print: Setting up variables...")

# Global variable
GLOBAL_MESSAGE = "Hello from global scope!"


def simple_function_with_print():
    print("Function print: Hello from student code!")
    print("Function print: This is a second line of output")
    return 42


def get_global_message():
    return GLOBAL_MESSAGE


# More global print statements
print("Global print: Student code loaded successfully!")
