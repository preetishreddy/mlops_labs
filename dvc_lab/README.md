# DVC Lab (Iris)
- Dataset: Iris (CSV dumped via scikit-learn)
- Remote: gs://ml-ops-lab-dvc-preetish
- Steps:
  1) dvc add data/iris.csv
  2) git commit -m "track iris"
  3) dvc push
- Update flow: edit CSV → dvc add → git commit → dvc push
- Revert: git checkout <commit> → dvc checkout
