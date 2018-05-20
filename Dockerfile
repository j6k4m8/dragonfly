FROM library/python:3-alpine3.6

COPY . .
RUN pip3 install -r requirements.txt
ENV LANG=en

CMD [ "python3", "run.py", "$LANG", "/mnt/indir" ]

# Usage:
# docker run -v $(pwd)/inputs/:/mnt/indir/ -p 5000:5000 -e LANG=en dragonfly-ner
