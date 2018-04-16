from setuptools import setup


setup(name='redis-types',
      version='0.0.5',
      author='Owen Stranathan',
      author_email='owen@appfigures.com',
      packages=['redis_types'],
      url='http://github.com/appfigures/python-packages/redistools',
      license='LICENSE',
      description='Some better abstraction on redis types',
      long_description=open("README.md").read(),
      zip_safe=False,
      install_requires=[
          "redis"
      ])
