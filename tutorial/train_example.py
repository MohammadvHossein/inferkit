"""
Train a simple Iris model and save checkpoint for inference.py
Run: python tutorial/train_example.py
Output: checkpoints/model.pkl + target_names.pkl
"""
from pathlib import Path
import pickle

try:
    from sklearn.datasets import load_iris
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score
except ImportError:
    print("pip install scikit-learn")
    raise SystemExit(1)

print("Loading data...")
X, y = load_iris(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print("Training...")
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)

acc = accuracy_score(y_test, clf.predict(X_test))
print(f"Accuracy: {acc:.3f}")

Path("checkpoints").mkdir(exist_ok=True)
with open("checkpoints/model.pkl", "wb") as f:
    pickle.dump(clf, f)
with open("checkpoints/target_names.pkl", "wb") as f:
    pickle.dump(load_iris().target_names, f)

print("Checkpoint saved to checkpoints/model.pkl")
print("Now serve: inferkit dev inference.py  (or tutorial/inference_example.py)")
