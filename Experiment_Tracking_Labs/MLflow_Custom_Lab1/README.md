# MLflow Custom Lab 1 — California Housing

This lab teaches the basics of MLflow experiment tracking:
- How to log parameters and metrics
- How to log models as artifacts
- Manual logging vs autologging
- Running multiple experiment runs
- Viewing results in the MLflow UI
- Serving a trained model locally

## Folder Structure

```
MLflow_Custom_Lab1/
│
├── data/
├── starter.ipynb
├── train_model.ipynb
├── train_model.py
├── serving.ipynb
├── serving.py
├── utils.py
├── requirements.txt
└── README.md
```

## Step 1: Install Dependencies

Make sure you are inside the MLflow_Custom_Lab1 directory.

```
pip install -r requirements.txt
```

## Step 2: Run the Training Script

This will train an ElasticNet regression model on the California Housing dataset and log:
- Parameters
- Metrics
- Model artifact
- Signature

```
python train_model.py
```

You should see output showing RMSE, MAE, and R2.

## Step 3: Start the MLflow UI

In a separate terminal, run:

```
mlflow ui --port 5001
```

Then open:

```
http://localhost:5001
```

You will see the experiment runs logged under the "Default" experiment.

## Step 4: Explore train_model.ipynb

This notebook demonstrates:

- Manual logging with mlflow.log_param and mlflow.log_metric
- Autologging with mlflow.sklearn.autolog()
- Hyperparameter sweep with multiple runs

Running these cells will add additional runs to MLflow.

## Step 5: Serve a Model

Pick a run ID from the MLflow UI and use it to serve your model.

Example:

```
mlflow models serve -m mlruns/0/<RUN_ID>/artifacts/model -p 5002 --no-conda
```

Keep this terminal open. This starts a local server for predictions.

## Step 6: Test the Served Model

Use serving.py to send test data to the model server:

```
python serving.py
```

You should get back a prediction.


