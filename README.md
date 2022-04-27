## dicom_parser_py

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

extract and sanitize specific DICOM tags to .csv/.json files using [pydicom](https://pydicom.github.io/pydicom/stable/index.html)

### Pipeline for DICOM reporting:
1. scan folder for valid source DICOMs
2. extract:  DICOM tags with pydicom
3. sanitize: tag values (remove invalid characters)
4. export: save specific tags of interest to file(s)


## Setup Python Virtual Environment
[Poetry Commands](https://python-poetry.org/docs/cli/)
```
# install 
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python3 -
python get-poetry.py

# validate installed version
poetry --version

# optional: update configuration settings
poetry config virtualenvs.in-project true
poetry config experimental.new-installer false
poetry config --list

# create poetry.lock and create virtual python environment in .venv
poetry check
poetry install -vvv | tee ./app/logs/poetry_install.log

# update pip in .venv
poetry run python -m pip install --upgrade pip
```

### DICOM Standard:
* [DICOM Current](https://www.dicomstandard.org/current)
* [DICOM Tags](https://www.dicomlibrary.com/dicom/dicom-tags/)

### DICOM Tools:
* [pydicom](https://github.com/pydicom/pydicom)
* [DCMTK](https://support.dcmtk.org/docs/)
* [Slicer3D](https://www.slicer.org/)
* [MATLAB DICOM Toolbox](https://www.mathworks.com/help/images/scientific-file-formats.html)

### DICOM Viewer:
* [MicroDicom](https://www.microdicom.com/)

### Public DICOM Test Data:
* [pydicom test_files](https://github.com/pydicom/pydicom/tree/master/pydicom/data/test_files)
* [TCIA on GCP](https://cloud.google.com/healthcare-api/docs/resources/public-datasets)
* [GDCM test datasets](http://gdcm.sourceforge.net/wiki/index.php/Sample_DataSet)
