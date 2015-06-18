import re

from setuptools import setup


try:
    # Distributions have to delete *requirements.txt
    with open('requirements.txt', 'r') as fp:
        install_requires = [re.split(r'[<>=~]', line)[0]
                            for line in fp if line.strip()]
except EnvironmentError:
    print("No requirements.txt, not handling dependencies")
    install_requires = []


setup(
    name = "python-ironic-inspector-client",
    version = "1.0.0",
    description = open('README.rst', 'r').readline().strip(),
    author = "Dmitry Tantsur",
    author_email = "dtantsur@redhat.com",
    url = "https://pypi.python.org/pypi/python-ironic-inspector-client",
    packages = ['ironic_inspector_client', 'ironic_inspector_client.test'],
    install_requires = install_requires,
    entry_points = {
        'openstack.cli.extension': [
            'baremetal-introspection = ironic_inspector_client.shell',
        ],
        'openstack.baremetal_introspection.v1': [
            "baremetal_introspection_start = ironic_inspector_client.shell:StartCommand",
            "baremetal_introspection_status = ironic_inspector_client.shell:StatusCommand",
        ],
    },
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: OpenStack',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX',
    ],
    license = 'APL 2.0',
)
