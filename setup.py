import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


install_requires = [
    'Pyqtree',
    'ordered-set'
]

setuptools.setup(
    name="talktown", # Replace with your own username
    version="0.0.1",
    author="Shi Johnson-Bey",
    author_email="shijbey@ucsc.edu",
    description="Simulation based on Talk of the Toen by James Ryan",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ShiJbey/talktown",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
    install_requires=install_requires,
    python_requires='>=3.6',
)
