## Setup
```bash
cd Docker/Dockerfiles
./build_all_containers
cd ../..
cp config.py.example config.py
```

## Start
```bash
docker-compose up -d rabbit && sleep 10 && docker-compose up --build main
```
