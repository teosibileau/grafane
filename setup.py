from setuptools import setup
from os import path

try:  # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError:  # for pip <= 9.0.3
    from pip.req import parse_requirements

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


requirements = [str(r.req) for r in
                parse_requirements('requirements.txt', session=False)]

setup(
    name='Grafane',
    version='0.6',
    packages=['grafane'],
    author=u'Teofilo Sibileau',
    author_email='teo.sibileau@gmail.com',
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://gitlab.com/drkloc/grafane',
    install_requires=requirements,
)
