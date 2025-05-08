from setuptools import setup, find_packages

setup(
    name="ocr_doc_utils",
    version="0.1.0",
    # Kéo vào đúng module ocr_doc_utils
    packages=find_packages(include=["ocr_doc_utils", "ocr_doc_utils.*"]),
)
