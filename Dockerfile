FROM python:3
ADD script.py /
CMD [ "python", "./script.py" ]
