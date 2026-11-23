# GreenCloud

GreenCloud is a cloud-native web application that monitors CPU and memory usage of containers, finds under-utilized resources, and gives advice to reduce waste, cost and energy use.

## Features
- Flask dashboard showing CPU and memory usage
- Advice engine that recommends lowering CPU requests and reducing replicas
- Containerized with Docker
- Orchestrated with Kubernetes (Deployment and Service, 2 replicas)
- Monitored with Prometheus and Grafana
- Deployed in a hybrid setup: private cloud (Docker Desktop Kubernetes) and a public cloud environment (Kind cluster)

## Project files
- `app.py`: web dashboard
- `advisor.py`: advice logic
- `Dockerfile`: container recipe
- `deployment.yaml`, `service.yaml`: Kubernetes configuration

## Run it
1. `docker build -t greencloud:v5 .`
2. `kubectl apply -f deployment.yaml`
3. `kubectl apply -f service.yaml`
4. Open `localhost:8080`

## Results
| | Before | After |
|---|---|---|
| CPU reserved per pod | 100m | 10m |
| CPU limit per pod | 250m | 100m |
| Utilization of reserved CPU | 0.72% | 11.24% |

Reserved CPU was cut by 90% with the app still working.

## Hybrid cloud
The same image and YAML files run on two clusters: a private cloud (Docker Desktop Kubernetes) and a public cloud environment simulated with Kind. Deploying to a real provider such as AWS, GCP or Azure follows the same steps and is listed as future work.