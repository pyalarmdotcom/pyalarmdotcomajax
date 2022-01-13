import os

from setuptools import setup

import pyalarmdotcomajax

here = os.path.abspath(os.path.dirname(__file__))


def read(*filenames, **kwargs):
    encoding = kwargs.get("encoding", "utf-8")
    sep = kwargs.get("sep", "\n")
    buf = []
    for filename in filenames:
        with open(filename, encoding=encoding) as f:
            buf.append(f.read())
    return sep.join(buf)


long_description = read("README.md")

setup(
    name="pyalarmdotcomajax",
    version=pyalarmdotcomajax.__version__,
    url="http://github.com/uvjustin/pyalarmdotcomajax/",
    license="MIT",
    author="Justin Wong",
    author_email="46082645+uvjustin@users.noreply.github.com",
    maintainer="Justin Wong, Elahd Bar-Shai",
    maintainer_email="46082645+uvjustin@users.noreply.github.com, 466460+elahd@users.noreply.github.com",
    install_requires=[],
    description="Python Interface for Alarm.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=["pyalarmdotcomajax"],
    include_package_data=True,
    package_data={"": ["*.csv"]},
    platforms="any",
    classifiers=[
        "Programming Language :: Python",
        "Development Status :: 3 - Alpha",
        "Natural Language :: English",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
