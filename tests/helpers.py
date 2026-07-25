import os
import shutil
import tempfile

envpath = os.path.join(os.path.dirname(__file__), "fixtures", "env")


def create_test_root():
    """Creates a temporary directory with the contents of the "env" folder."""
    root = tempfile.mkdtemp()

    for env in ("prod", "dev"):
        shutil.copytree(envpath, os.path.join(root, env, "env"))

    return root


def update_env_file(file_path: str, key: str, value: str):
    """Updates a key in a YAML file with a new value."""
    import yaml

    with open(file_path, "r") as f:
        data = yaml.safe_load(f)

    for _, env_config in data.items():
        if isinstance(env_config, dict) and key in env_config:
            env_config[key] = value

    with open(file_path, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def create_fixture_env_root():
    """Create a temporary envstack root populated from test fixtures."""
    root = tempfile.mkdtemp()
    prod_env = os.path.join(root, "prod", "env")
    dev_env = os.path.join(root, "dev", "env")

    os.makedirs(prod_env)
    os.makedirs(dev_env)

    shutil.copy2(os.path.join(envpath, "default.env"), prod_env)
    shutil.copy2(os.path.join(envpath, "test.env"), prod_env)
    shutil.copy2(os.path.join(envpath, "keys.env"), prod_env)
    shutil.copy2(os.path.join(envpath, "secrets.env"), prod_env)
    shutil.copy2(os.path.join(envpath, "project.env"), prod_env)
    shutil.copy2(os.path.join(envpath, "hello.env"), prod_env)
    shutil.copy2(os.path.join(envpath, "dev.env"), dev_env)

    return root
