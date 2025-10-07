## 📄 **`airflow_lab1/README.md`**

```markdown
# 🚀 Airflow Lab 1 — SMS Spam Classification Pipeline

![Project Banner — Add Screenshot Here](./images/lab1_banner_placeholder.png)

## 🧩 Overview
This lab demonstrates an **end-to-end MLOps workflow** using **Apache Airflow** for orchestration.  
The project automates the entire pipeline for **SMS spam detection** using TF-IDF + Logistic Regression.

Each stage of the machine learning lifecycle — data ingestion, preprocessing, training, evaluation, and batch prediction — is represented as a task in an Airflow DAG.

---

## 🏗️ Project Structure

```

airflow_lab1/
│
├── dags/                         # Airflow DAGs folder (mounted in container)
│   ├── data/                     # Input and processed data
│   ├── model/                    # Trained model & artifacts
│   ├── src/                      # Python scripts for each pipeline step
│   │   ├── download.py           # Downloads SMS spam dataset
│   │   ├── prep.py               # Cleans & preprocesses data
│   │   ├── train.py              # Trains TF-IDF + Logistic Regression model
│   │   ├── eval.py               # Evaluates model performance
│   │   ├── batch_predict.py      # Generates batch predictions
│   │   └── **init**.py
│   ├── airflow.py                # DAG definition
│   ├── requirements.txt          # Python dependencies
│   └── .gitignore
│
├── logs/                         # Airflow container logs
├── plugins/                      # Custom operators (if any, empty for now)
│
├── Dockerfile                    # Custom Airflow image with lab requirements
├── docker-compose.yml            # Containerized Airflow setup
├── .env                          # Environment variables for Airflow
│
└── README.md                     # This file

````

---

## ⚙️ Workflow Overview

| Stage | Description | Script | Airflow Task |
|--------|--------------|---------|---------------|
| 🧠 **Data Download** | Downloads SMS Spam Collection dataset from UCI | `download.py` | `download` |
| 🧹 **Preprocessing** | Cleans and encodes text data | `prep.py` | `prep` |
| 🏋️‍♂️ **Model Training** | Trains TF-IDF + Logistic Regression model | `train.py` | `train` |
| 📈 **Evaluation** | Evaluates accuracy, F1-score, ROC AUC | `eval.py` | `evaluate` |
| 📦 **Batch Prediction** | Scores unseen messages and saves output CSV | `batch_predict.py` | `batch` |

---

## 🐳 Running in Docker + Airflow

### 1️⃣ Build and Initialize
```bash
cd airflow_lab1
docker compose build
docker compose up airflow-init
````

### 2️⃣ Start Airflow

```bash
docker compose up -d
```

Access Airflow UI at: [http://localhost:8081](http://localhost:8081)
**Login:**

```
username: admin  
password: admin
```

---

## 🧭 DAG Overview

![Airflow DAG Screenshot Placeholder](./images/airflow_dag_placeholder.png)

### DAG ID

```
sms_spam_pipeline
```

### Tasks Flow

```
download → prep → train → evaluate → batch
```

---

## 📂 Output Artifacts

After successful DAG run, check:

```
airflow_lab1/dags/model/
│
├── sms_model.joblib      # Trained model
├── test.parquet          # Test dataset split
├── batch_scored.csv      # Predictions with spam probability
```

---

## 📊 Example Outputs

| text                               | spam_prob |
| ---------------------------------- | --------- |
| "congrats! you won a free voucher" | 0.98      |
| "see you at class tomorrow"        | 0.03      |

---

## 🧰 Airflow Environment Details

| Component | Version                        |
| --------- | ------------------------------ |
| Airflow   | 2.9.2                          |
| Python    | 3.10                           |
| Postgres  | 15                             |
| Executor  | LocalExecutor                  |
| Port      | 8081 (host) → 8080 (container) |

---

## 🧠 Key Learnings

* How to structure a lightweight ML project for Airflow.
* DAG orchestration for machine learning pipelines.
* Containerized MLOps setup using `docker-compose`.
* Mounting DAG folders locally for rapid iteration.

---

## 🖼️ Future Additions

* [ ] Add ROC curve and confusion matrix images
* [ ] Integrate XGBoost classifier for comparison
* [ ] Push artifacts to S3 or MinIO
* [ ] Add email notification on DAG completion

---

## 🧹 Cleanup

To stop all running containers:

```bash
docker compose down
```

To rebuild everything from scratch:

```bash
docker compose build --no-cache
docker compose up -d
```

---

## ✨ Credits

* Dataset: [UCI Machine Learning Repository — SMS Spam Collection](https://archive.ics.uci.edu/ml/datasets/sms+spam+collection)
* Airflow Base Image: [apache/airflow:2.9.2-python3.10](https://hub.docker.com/r/apache/airflow)
* Author: *Preetish Reddy*

---

## 📷 Image Placeholders

| Purpose        | Path                                     |
| -------------- | ---------------------------------------- |
| Project Banner | `./images/lab1_banner_placeholder.png`   |
| DAG Screenshot | `./images/airflow_dag_placeholder.png`   |
| Metrics/Charts | `./images/model_metrics_placeholder.png` |

