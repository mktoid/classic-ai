## Classic.AI
(in progress)

### Running locally

$ sudo docker run -v $PWD:/tmp/working -w=/tmp/working -p 8000:8000 -p 9200:9200 --rm -it mktoid/classic
elasticsearch@63365dd1cdff:/tmp/working$ elasticsearch & python server.py &

