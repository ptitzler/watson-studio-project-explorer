from setuptools import setup, find_packages
setup(name='watsonstudioprojectexplorer',
	  version='0.1.1',
	  description='Watson Studio project explorer',
	  url='https://github.com/ptitzler/watson-studio-project-explorer',
	  install_requires=['pixiedust >= 1.1.9', 'pandas','requests'],
	  author='Patrick Titzler',
	  author_email='ptitzler@us.ibm.com',
	  license='Apache 2.0',
	  packages=find_packages(),
	  include_package_data=False,
	  zip_safe=False,
	  classifiers=[
	   'Development Status :: 4 - Beta',
	   'Programming Language :: Python :: 2.7',
	   'Programming Language :: Python :: 3.5'
	  ],
	  python_requires='>=2.7'
)
