from setuptools import setup, find_packages
import os


with open("README.md", "r", encoding="utf-8") as fh:
    long_description: str = fh.read()


version: str = "1.0.0"
with open(os.path.join("__init__.py"), "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"').strip("'")
            break


setup(
    name="appraiser-photo-bot",
    version=version,
    author="Oleg Diukaev",
    author_email="olegdixon5973@gmail.com",
    description="Telegram bot for creating Word documents with photo tables",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/oleg-dixon/appraiser-photo-bot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Communications :: Chat",
        "Topic :: Office/Business",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: AsyncIO",
    ],
    python_requires=">=3.12",
    install_requires=[
        "python-telegram-bot>=20.0",
        "python-telegram-bot[job-queue]>=20.0",
        "pillow>=10.0.0",
        "python-docx>=1.1.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "uv>=0.4.0",
            "black>=23.0",
            "flake8>=6.0",
            "mypy>=1.0",
            "pytest>=7.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0",
            "pre-commit>=3.0",
            "isort>=5.12",
            "types-pillow",
            "types-setuptools",
        ],
    },
    entry_points={
        "console_scripts": [
            "appraiser-photo-bot=cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "appraiser_photo_bot": ["py.typed"],
    },
    keywords=[
        "telegram",
        "bot",
        "word",
        "document",
        "table",
        "photo",
        "image",
        "automation",
    ],
    project_urls={
        "Bug Reports": "https://github.com/oleg-dixon/appraiser-photo-bot/issues",
        "Source": "https://github.com/oleg-dixon/appraiser-photo-bot",
        "Documentation": "https://github.com/oleg-dixon/appraiser-photo-bot#readme",
    },
)
