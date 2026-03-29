import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (classification_report, confusion_matrix, 
                            accuracy_score, precision_score, recall_score, 
                            f1_score, roc_auc_score, roc_curve)
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class DepressionClassifier:
    """
    Train and evaluate a model to detect depression from typing patterns
    """
    
    def __init__(self, dataset_path='processed_dataset.csv'):
        self.dataset_path = dataset_path
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.results = {}
        
    def load_and_prepare_data(self):
        """Load dataset and prepare for training"""
        print("Loading dataset...")
        df = pd.read_csv(self.dataset_path)
        
        print(f"Dataset shape: {df.shape}")
        print(f"Depression distribution:\n{df['depression_label'].value_counts()}")
        
        # Separate features and target
        # Drop non-feature columns
        drop_cols = ['participant_id', 'phq9_severity', 'collection_date', 
                     'age', 'gender', 'year_of_study', 'phq9_total',
                     'copy_task_text', 'free_writing_text']
        
        # Drop columns that exist
        existing_drop_cols = [col for col in drop_cols if col in df.columns]
        
        X = df.drop(columns=existing_drop_cols + ['depression_label'], errors='ignore')
        y = df['depression_label']
        
        # Handle missing values (fill with median)
        X = X.fillna(X.median())
        
        # Store feature names for later analysis
        self.feature_names = X.columns.tolist()
        
        print(f"\nFeatures used: {len(self.feature_names)}")
        print(f"Class distribution: {dict(y.value_counts())}")
        
        # Check if we have enough data
        if len(df) < 10:
            print("\n⚠️  WARNING: Very small sample size!")
            print("Results are for TESTING PIPELINE ONLY - not scientifically valid")
            print("Collect at least 40 participants for real analysis")
        
        return X, y, df
    
    def train_model(self, X_train, y_train):
        """Train Random Forest classifier"""
        print("\nTraining Random Forest model...")
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        # Train model with balanced class weights
        self.model = RandomForestClassifier(
            n_estimators=50,  # Reduced for small dataset
            max_depth=5,      # Reduced to prevent overfitting
            min_samples_split=2,
            min_samples_leaf=1,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        
        self.model.fit(X_train_scaled, y_train)
        print("Model trained successfully!")
        
        return X_train_scaled
    
    def evaluate_model(self, X_test, y_test):
        """Evaluate model performance"""
        print("\nEvaluating model...")
        
        # Scale test data
        X_test_scaled = self.scaler.transform(X_test)
        
        # Predictions
        y_pred = self.model.predict(X_test_scaled)
        y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]
        
        # Calculate metrics
        # Get unique classes in test set
        test_classes = np.unique(y_test)
        
        self.results = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0, average='binary' if len(test_classes) > 1 else 'macro'),
            'recall': recall_score(y_test, y_pred, zero_division=0, average='binary' if len(test_classes) > 1 else 'macro'),
            'f1': f1_score(y_test, y_pred, zero_division=0, average='binary' if len(test_classes) > 1 else 'macro'),
            'roc_auc': roc_auc_score(y_test, y_pred_proba) if len(test_classes) > 1 else 0,
            'confusion_matrix': confusion_matrix(y_test, y_pred),
            'classification_report': classification_report(y_test, y_pred, zero_division=0)
        }
        
        return y_pred, y_pred_proba
    
    def get_feature_importance(self):
        """Get and display feature importance"""
        print("\nTop 10 Most Important Features:")
        print("=" * 60)
        
        importances = self.model.feature_importances_
        feature_importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False)
        
        print(feature_importance_df.head(10).to_string(index=False))
        
        return feature_importance_df
    
    def plot_results(self, y_test, y_pred, y_pred_proba, feature_importance_df):
        """Generate visualization plots"""
        print("\nGenerating plots...")
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. Confusion Matrix
        cm = self.results['confusion_matrix']
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[0, 0],
                   xticklabels=['Not Depressed', 'Depressed'],
                   yticklabels=['Not Depressed', 'Depressed'])
        axes[0, 0].set_title('Confusion Matrix')
        axes[0, 0].set_ylabel('True Label')
        axes[0, 0].set_xlabel('Predicted Label')
        
        # 2. ROC Curve
        if len(np.unique(y_test)) > 1:
            fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
            axes[0, 1].plot(fpr, tpr, label=f'ROC (AUC = {self.results["roc_auc"]:.3f})')
            axes[0, 1].plot([0, 1], [0, 1], 'k--', label='Random')
            axes[0, 1].set_xlabel('False Positive Rate')
            axes[0, 1].set_ylabel('True Positive Rate')
            axes[0, 1].set_title('ROC Curve')
            axes[0, 1].legend()
            axes[0, 1].grid(True, alpha=0.3)
        else:
            axes[0, 1].text(0.5, 0.5, 'Not enough test samples\nfor ROC curve', 
                          ha='center', va='center')
        
        # 3. Feature Importance (Top 10)
        top_features = feature_importance_df.head(10)
        axes[1, 0].barh(range(len(top_features)), top_features['importance'])
        axes[1, 0].set_yticks(range(len(top_features)))
        axes[1, 0].set_yticklabels(top_features['feature'])
        axes[1, 0].set_xlabel('Importance')
        axes[1, 0].set_title('Top 10 Most Important Features')
        axes[1, 0].invert_yaxis()
        
        # 4. Performance Metrics Bar Chart
        metrics = ['Accuracy', 'Precision', 'Recall', 'F1-Score']
        values = [self.results['accuracy'], self.results['precision'], 
                 self.results['recall'], self.results['f1']]
        
        bars = axes[1, 1].bar(metrics, values, color=['#3498db', '#2ecc71', '#e74c3c', '#f39c12'])
        axes[1, 1].set_ylim(0, 1)
        axes[1, 1].set_ylabel('Score')
        axes[1, 1].set_title('Model Performance Metrics')
        axes[1, 1].grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            axes[1, 1].text(bar.get_x() + bar.get_width()/2., height,
                          f'{height:.3f}', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig('model_evaluation_plots.png', dpi=300, bbox_inches='tight')
        print("Plots saved as 'model_evaluation_plots.png'")
        plt.show()
    
    def save_model(self, output_dir='models'):
        """Save trained model and scaler"""
        Path(output_dir).mkdir(exist_ok=True)
        
        model_path = f"{output_dir}/depression_classifier.pkl"
        scaler_path = f"{output_dir}/feature_scaler.pkl"
        
        joblib.dump(self.model, model_path)
        joblib.dump(self.scaler, scaler_path)
        
        print(f"\nModel saved to {model_path}")
        print(f"Scaler saved to {scaler_path}")
    
    def generate_report(self):
        """Generate a text report of results"""
        report = f"""
================================================================================
DEPRESSION DETECTION MODEL - EVALUATION REPORT (PIPELINE TEST)
================================================================================

⚠️  NOTE: This is a TEST with only {len(self.feature_names)} participants
    Results are NOT scientifically valid - for testing pipeline only
    Collect 40+ participants for real analysis

MODEL PERFORMANCE METRICS:
--------------------------
Accuracy:  {self.results['accuracy']:.3f}
Precision: {self.results['precision']:.3f}
Recall:    {self.results['recall']:.3f}
F1-Score:  {self.results['f1']:.3f}
ROC-AUC:   {self.results['roc_auc']:.3f}

CONFUSION MATRIX:
----------------
{self.results['confusion_matrix']}

DETAILED CLASSIFICATION REPORT:
-------------------------------
{self.results['classification_report']}

================================================================================
        """
        
        with open('model_evaluation_report.txt', 'w') as f:
            f.write(report)
        
        print(report)
        print("\nReport saved to 'model_evaluation_report.txt'")

def main():
    """
    Main execution pipeline
    """
    print("=" * 80)
    print("DEPRESSION DETECTION FROM TYPING PATTERNS - ML TRAINING")
    print("=" * 80)
    
    # Initialize classifier
    classifier = DepressionClassifier('processed_dataset.csv')
    
    # Load data
    X, y, df = classifier.load_and_prepare_data()
    
    # Check minimum sample size
    if len(df) < 5:
        print("\n❌ ERROR: Not enough data to train")
        print("Need at least 5 participants. You have:", len(df))
        return
    
    # Split data (smaller test size for small datasets)
    test_size = 0.2 if len(df) >= 10 else 0.2
    
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
    except ValueError:
        # If stratification fails due to small sample
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
    
    print(f"\nTraining set size: {len(X_train)}")
    print(f"Test set size: {len(X_test)}")
    
    # Train model
    classifier.train_model(X_train, y_train)
    
    # Evaluate
    y_pred, y_pred_proba = classifier.evaluate_model(X_test, y_test)
    
    # Feature importance
    feature_importance_df = classifier.get_feature_importance()
    
    # Plot results
    classifier.plot_results(y_test, y_pred, y_pred_proba, feature_importance_df)
    
    # Generate report
    classifier.generate_report()
    
    # Save model
    classifier.save_model()
    
    print("\n" + "=" * 80)
    print("TRAINING COMPLETE!")
    print("=" * 80)
    print("\nGenerated files:")
    print("  - model_evaluation_plots.png")
    print("  - model_evaluation_report.txt")
    print("  - models/depression_classifier.pkl")
    print("  - models/feature_scaler.pkl")
    print("\n⚠️  REMEMBER: Results are for TESTING only with 5 participants")
    print("   Collect 40+ participants for scientifically valid results")

if __name__ == "__main__":
    main()
