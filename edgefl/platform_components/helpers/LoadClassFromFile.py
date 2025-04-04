import importlib.util

def load_class_from_file(file_path, class_name):
    spec = importlib.util.spec_from_file_location(class_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, class_name):  # Ensure class exists in the module
        return getattr(module, class_name)  # Return the class
    else:
        raise AttributeError(f"Class '{class_name}' not found in '{file_path}'")