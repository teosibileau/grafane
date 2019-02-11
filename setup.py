from setuptools import setup

try:  # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError:  # for pip <= 9.0.3
    from pip.req import parse_requirements

requirements = [str(r.req) for r in
                parse_requirements('requirements.txt', session=False)]

setup(
    name='Grafane',
    version='0.1',
    packages=['grafane'],
    author=u'Teofilo Sibileau',
    author_email='teo.sibileau@gmail.com',
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    install_requires=requirements,
)
