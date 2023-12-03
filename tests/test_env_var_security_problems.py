# https://docs.docker.com/engine/reference/commandline/port/
# List port mappings or a specific mapping for the container
#  docker port CONTAINER [PRIVATE_PORT[/PROTO]]

import io
import os
import re
import shutil
import subprocess

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import pytest
import yaml

from lib.db import DB
from lib import utils
from lib.global_config import GlobalConfig
from tests import test_functions as Tests
from runner import Runner

GlobalConfig().override_config(config_name='test-config.yml')
config = GlobalConfig().config

## Note:
# Always do asserts after try:finally: blocks
# otherwise failing Tests will not run the runner.cleanup() properly

# This should be done once per module
@pytest.fixture(autouse=True, scope="module", name="build_image")
def build_image_fixture():
    uri = os.path.abspath(os.path.join(
            CURRENT_DIR, 'stress-application/'))
    subprocess.run(['docker', 'compose', '-f', uri+'/compose.yml', 'build'], check=True)
    GlobalConfig().override_config(config_name='test-config.yml')

# cleanup test/tmp directory after every test run
@pytest.fixture(autouse=True, name="cleanup_tmp_directories")
def cleanup_tmp_directories_fixture():
    yield
    tmp_dir = os.path.join(CURRENT_DIR, 'tmp/')
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    if os.path.exists('/tmp/gmt-test-data'):
        shutil.rmtree('/tmp/gmt-test-data')

# This function runs the runner up to and *including* the specified step
#pylint: disable=redefined-argument-from-local

def get_env_vars(runner):
    try:
        Tests.run_until(runner, 'setup_services')

        ps = subprocess.run(
            ['docker', 'exec', 'test-container', '/bin/sh',
            '-c', 'env'],
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding='UTF-8'
        )
        env_var_output = ps.stdout
    finally:
        Tests.cleanup(runner)
    return env_var_output

def check_if_container_is_privileged(runner):
    try:
        Tests.run_until(runner, 'setup_services')

        ps = subprocess.run(
            ['docker', 'inspect', '--format={{.HostConfig.Privileged}}', 'test-container'],
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding='UTF-8'
        )
        is_container_privileged = ps.stdout.strip()
    finally:
        Tests.cleanup(runner)
    return is_container_privileged




### Test some special cases that could cause security problems ###
# allow_unsafe=True is used to show potential problems if not prevented

def test_env_variable_security_get_host_env_var(capsys):
    runner = Tests.setup_runner(usage_scenario='env_vars_stress_security_host_env_var.yml', allow_unsafe=True, dry_run=True)
    env_var_output = get_env_vars(runner)

    # Print env vars
    with capsys.disabled():
        print("env_var_output:\n", env_var_output)

    assert 'green-metrics-tool' not in env_var_output, Tests.assertion_info(' $(pwd) does not get evaluated', env_var_output)

def test_env_variable_security_privileged(capsys):
    runner = Tests.setup_runner(usage_scenario='env_vars_stress_security_privileged.yml', allow_unsafe=True, dry_run=True)
    is_container_privileged = check_if_container_is_privileged(runner)
    with capsys.disabled():
        print("is_container_privileged:\n", is_container_privileged)
    assert is_container_privileged == "false", Tests.assertion_info('container does not have privileged rights', is_container_privileged)

def test_env_variable_security_special_chars(capsys):
    runner = Tests.setup_runner(usage_scenario='env_vars_stress_security_special_chars.yml', allow_unsafe=True, dry_run=True)
    env_var_output = get_env_vars(runner)

    # Print env vars
    with capsys.disabled():
        print("env_var_output:\n", env_var_output)

    assert '$PWD' in env_var_output, Tests.assertion_info('$PWD in env var output', env_var_output)
    assert '${PWD}' in env_var_output, Tests.assertion_info('${PWD} in env var output', env_var_output)
    assert '$$PWD' in env_var_output, Tests.assertion_info('$$PWD in env var output', env_var_output)
    assert r'\$\$PWD' in env_var_output, Tests.assertion_info(r'\$\$PWD in env var output', env_var_output)
