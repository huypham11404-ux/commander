from setuptools import setup, find_packages

setup(
    name="commander",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "mido",
        "pretty_midi",
        "music21",
        "numpy",
        "scipy",
        "websockets",
        "psutil"
    ]
)
