Kubernetes Deployment & Rollout Notes
📍 Project: Agentic Health Insurance Chatbot
Environment: macOS (Apple Silicon arm64), Minikube (Docker driver), kubectl.
🏗️ 1. Infrastructure Setup Observations
Driver Connectivity: On Apple Silicon, ensuring Docker Desktop is installed via the proper "Apple Chip" method and Rosetta 2 is active is required for the docker driver to function with Minikube.
Internal Registry: By using eval $(minikube docker-env), we avoided the overhead of pushing images to Docker Hub. Images were built directly inside the Minikube environment.
Security: Using Kubernetes Secrets for the GROQ_API_KEY successfully decoupled sensitive credentials from the deployment manifests.
⚖️ 2. Scaling & Load Balancing
Command: kubectl scale deployment backend-deployment --replicas=3
Observation: Scaling is near-instant. Kubernetes automatically created the 3rd pod and the backend-service (ClusterIP) began distributing internal traffic across all three available IP addresses.
Redundancy: By maintaining 2+ replicas, the application is protected against a single pod failure.
🔄 3. Zero-Downtime Rollout 
Strategy: Rolling Update.
Logic: When shifting from chatbot-backend:latest to chatbot-backend:v2, K8s followed a "create-then-kill" logic.
Key Win: Because of the readinessProbe, Kubernetes waited for the new v2 pod to load the heavy sentence-transformers models (staying 0/1 READY for ~30s) before it terminated the old v1 pod.
Result: The Streamlit frontend never lost connection to a valid backend during the entire update process.
🏥 4. Health & Readiness (The ML Factor)
Running vs. Ready: A major observation was pods showing Status: Running but READY: 0/1.
Reasoning: In an AI/ML context, "Running" means the container started; "Ready" means the Python process has successfully loaded the models into RAM and passed the /health check.
Probes: The initialDelaySeconds: 30 prevented premature health check failures while the models were warming up