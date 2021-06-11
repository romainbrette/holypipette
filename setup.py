from setuptools import setup, find_packages

setup(
    name='holypipette',
    version='0.1',
    description='Semi-automated patch clamp recordings',
    url='https://github.com/romainbrette/holypipette/',
    author='Romain Brette, Marcel Stimberg, Hoang Nguyen',
    author_email='romain.brette@inserm.fr',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
    packages=find_packages(),
    install_requires=['numpy', 'PyQt5', 'qtawesome', 'pillow', 'pyserial',
                      'param', 'pyyaml']
)