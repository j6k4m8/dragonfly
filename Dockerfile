FROM library/python:3-alpine3.6

COPY . .
RUN pip3 install -r requirements.txt

CMD [ "python3", "run.py", "$LANG", "/mnt/indir" ]
