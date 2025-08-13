import os
from glob import glob
from setuptools import setup

package_name = 'typedb_tactics'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # (os.path.join('share', package_name, 'config'),
        #     glob('config/*')),
        # (os.path.join('share', package_name, 'launch'),
        #     glob('launch/*'))
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Gustavo Rezende',
    maintainer_email='g.rezendesilva@tudelft.nl',
    description='typedb tactics',
    license='Apache-2.0',
    extras_require = {
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            # 'typedb_tactics = typedb_tactics.typedb_tactics_node:main'
        ],
    },
)
