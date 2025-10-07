# 🚀 Airflow Lab 1 — SMS Spam Classification Pipeline

---

## 🧩 Overview
This lab demonstrates an **end-to-end MLOps workflow** using **Apache Airflow** for orchestration.  
It automates the pipeline for **SMS Spam Detection** using **TF-IDF** and **Logistic Regression**, covering:
- Data ingestion  
- Preprocessing  
- Model training  
- Evaluation  
- Batch inference  

Each of these stages is implemented as an individual Airflow task, forming a complete ML pipeline.

---

## 🏗️ Project Structure

**Folder Layout**

airflow_lab1/
│
├── dags/                → Airflow DAGs (mounted in container)
│   ├── data/            → Input & processed data
│   ├── model/           → Trained model & outputs
│   ├── src/             → Pipeline step scripts
│   │   ├── download.py
│   │   ├── prep.py
│   │   ├── train.py
│   │   ├── eval.py
│   │   ├── batch_predict.py
│   │   └── __init__.py
│   ├── airflow.py       → DAG definition
│   ├── requirements.txt → Python dependencies
│   └── .gitignore
│
├── logs/                → Airflow container logs
├── plugins/             → Custom operators (currently empty)
├── Dockerfile           → Custom Airflow image
├── docker-compose.yml   → Containerized Airflow setup
├── .env                 → Environment variables for Airflow
└── README.md            → Project documentation

---

## ⚙️ Pipeline Workflow

| Stage | Description | Script | Airflow Task |
|:------|:-------------|:--------|:--------------|
| 🧠 **Data Download** | Fetches SMS Spam dataset from UCI | `download.py` | `download` |
| 🧹 **Preprocessing** | Cleans and encodes text data | `prep.py` | `prep` |
| 🏋️‍♂️ **Model Training** | Trains TF-IDF + Logistic Regression | `train.py` | `train` |
| 📈 **Evaluation** | Prints metrics (Accuracy, F1, ROC AUC) | `eval.py` | `evaluate` |
| 📦 **Batch Prediction** | Scores unseen messages | `batch_predict.py` | `batch` |

---

## 🐳 Running in Docker + Airflow

### Build and Initialize
cd airflow_lab1
docker compose build
docker compose up airflow-init

### Start Airflow
docker compose up -d

Then open Airflow: http://localhost:8081  
**Login credentials:**  
username: admin  
password: admin  

---

## 🧭 DAG Overview

**DAG ID:** `sms_spam_pipeline`  
**Task Flow:** download → prep → train → evaluate → batch

(Insert Airflow DAG Screenshot here)

---

## 📂 Output Artifacts

After a successful run, you’ll find results in airflow_lab1/dags/model/:

- sms_model.joblib — Trained TF-IDF + Logistic Regression model  
- test.parquet — Saved test dataset split  
- batch_scored.csv — Predictions with spam probabilities

---

## 📊 Example Outputs

| text | spam_prob |
|------|------------|
| "congrats! you won a free voucher" | 0.98 |
| "see you at class tomorrow" | 0.03 |

---

## 🧰 Environment Details

| Component | Version |
|------------|----------|
| Airflow | 2.9.2 |
| Python | 3.10 |
| Postgres | 15 |
| Executor | LocalExecutor |
| Port | 8081 (host) → 8080 (container) |

---

## 🧠 Key Learnings

- Structured ML project design for Airflow  
- Task orchestration across preprocessing, training, and inference  
- Containerized MLOps setup with docker-compose  
- Mounting DAG folders locally for rapid development

---

## 🖼️ Future Enhancements

- [ ] Add ROC Curve and Confusion Matrix visuals  
- [ ] Integrate XGBoost classifier for comparison  
- [ ] Push model artifacts to cloud storage (e.g., S3)  
- [ ] Add email notification upon DAG completion  

---

## 🧹 Cleanup

Stop all running containers:  
docker compose down  

Rebuild from scratch:  
docker compose build --no-cache  
docker compose up -d  

---

## ✨ Credits

- Dataset: UCI Machine Learning Repository — SMS Spam Collection  
- Base Image: apache/airflow:2.9.2-python3.10  
- Author: Preetish Reddy
