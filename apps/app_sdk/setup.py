from setuptools import setup, find_packages

setup(
    name="app sdk",
    version="1.0.0",
    description="App SDK",
    author_email="",
    url="",
    keywords=[],
    install_requires=[
        "async-timeout==3.0.1",
        "asynqp==0.6",
        "attrs==19.3.0",
        "beautifulsoup4==4.8.2",
        "certifi==2019.11.28",
        "chardet==3.0.4",
        "Click==7.0",
        "fastapi==0.46.0",
        "h11==0.9.0",
        "httptools==0.0.13",
        "idna==2.8",
        "importlib-metadata==1.3.0",
        "kombu==4.6.7",
        "more-itertools==8.0.2",
        "multidict==4.7.3",
        "pydantic==1.3",
        "python-consul==1.1.0",
        "python-dateutil==2.8.1",
        "PyYAML==5.4",
        "requests==2.22.0",
        "six==1.13.0",
        "soupsieve==1.9.5",
        "starlette==0.12.9",
        "swagger-client==1.0.0",
        "urllib3==1.25.7",
        "uvicorn==0.11.1",
        "uvloop==0.14.0",
        "vine==1.3.0",
        "websockets==8.1",
        "yarl==1.4.2",
        "zipp==0.6.0"
    ],
    packages=find_packages(),
    include_package_data=True,
    long_description=""
)
