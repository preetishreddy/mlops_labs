from datetime import datetime
from pathlib import Path
from airflow import DAG
from airflow.operators.bash import BashOperator

D = Path(__file__).resolve().parent
SRC = D / "src"

default_args = {"owner": "airflow", "retries": 0}

with DAG(
    dag_id="sms_spam_pipeline",
    start_date=datetime(2024,1,1),
    schedule="@daily",
    catchup=False,
    default_args=default_args,
    tags=["mlops","nlp","lab1"]
):
    download = BashOperator(task_id="download", bash_command=f"python {SRC/'download.py'}")
    prep     = BashOperator(task_id="prep",     bash_command=f"python {SRC/'prep.py'}")
    train    = BashOperator(task_id="train",    bash_command=f"python {SRC/'train.py'}")
    evaluate = BashOperator(task_id="evaluate", bash_command=f"python {SRC/'eval.py'}")
    batch    = BashOperator(task_id="batch",    bash_command=f"python {SRC/'batch_predict.py'}")

    download >> prep >> train >> evaluate >> batch
