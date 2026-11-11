from glob import glob
import os

from setuptools import setup

package_name = 'tactical_retreat_kb'

data_files = [
    ('share/ament_index/resource_index/packages',
     ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
    (os.path.join('share', package_name, 'launch'),
     glob('launch/*launch.[pxy][yma]*')),
]


def package_files(data_files, directory_list):

    paths_dict = {}

    for directory in directory_list:

        for (path, _, filenames) in os.walk(directory):

            for filename in filenames:

                file_path = os.path.join(path, filename)
                install_path = os.path.join('share', package_name, path)

                if install_path in paths_dict.keys():
                    paths_dict[install_path].append(file_path)

                else:
                    paths_dict[install_path] = [file_path]

    for key in paths_dict.keys():
        data_files.append((key, paths_dict[key]))

    return data_files


setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=package_files(data_files, ['schemas/', 'jars/']),
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Elvin Alberts',
    maintainer_email='e.g.alberts@tudelft.nl',
    description='tactical_retreat_kb',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'tactical_retreat = tactical_retreat_kb.tactical_retreat_node:main'
        ],
    },
)
