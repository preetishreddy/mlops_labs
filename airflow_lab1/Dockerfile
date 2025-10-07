FROM apache/airflow:2.9.2-python3.10

# Install the Python deps used by THIS lab's DAGs
COPY dags/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
