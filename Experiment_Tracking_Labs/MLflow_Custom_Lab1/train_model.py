import mlflow
import mlflow.sklearn
from mlflow.models.signature import infer_signature

from sklearn.datasets import fetch_california_housing
from sklearn.linear_model import ElasticNet
from sklearn.model_selection import train_test_split

import pandas as pd
import numpy as np
import warnings
import sys

from utils import eval_metrics

warnings.filterwarnings("ignore")
np.random.seed(42)

if __name__ == "__main__":
    # Load California housing dataset
    housing = fetch_california_housing(as_frame=True)
    X = housing.data
    y = housing.target

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Hyperparameters from CLI or defaults
    alpha = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
    l1_ratio = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5

    # Start MLflow run
    with mlflow.start_run():
        mlflow.log_param("alpha", alpha)
        mlflow.log_param("l1_ratio", l1_ratio)

        model = ElasticNet(alpha=alpha, l1_ratio=l1_ratio)
        model.fit(X_train, y_train)

        predictions = model.predict(X_test)
        rmse, mae, r2 = eval_metrics(y_test, predictions)

        mlflow.log_metric("rmse", rmse)
