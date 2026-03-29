import pandas as pd
import numpy as np
import re
from pathlib import Path

class CSVFeatureExtractor:
    """
    Extract features from web-collected CSV data
    """
    
    def __init__(self, csv_path='all_participant_data.csv'):
        self.csv_path = csv_path
        
    def extract_linguistic_features(self, text):
        """
        Extract linguistic features from typed text
        """
        if not text or pd.isna(text) or len(str(text).strip()) < 10:
            return {}
        
        text = str(text).lower()
        words = re.findall(r'\b\w+\b', text)
        
        if len(words) == 0:
            return {}
        
        # Negative emotion words
        negative_words = set([
            'sad', 'depressed', 'unhappy', 'miserable', 'hopeless', 'worthless',
            'tired', 'exhausted', 'stressed', 'anxious', 'worried', 'afraid',
            'alone', 'lonely', 'isolated', 'empty', 'numb', 'bad', 'terrible',
            'awful', 'horrible', 'struggle', 'difficult', 'hard', 'pain', 'hurt',
            'fail', 'failure', 'weak', 'overwhelmed', 'burden', 'useless'
        ])
        
        # Positive emotion words
        positive_words = set([
            'happy', 'joy', 'good', 'great', 'wonderful', 'excellent', 'amazing',
            'love', 'enjoy', 'excited', 'fun', 'beautiful', 'peaceful', 'calm',
            'relaxed', 'confident', 'proud', 'satisfied', 'grateful', 'blessed',
            'hope', 'better', 'improve', 'success', 'accomplish'
        ])
        
        # First person pronouns
        first_person = set(['i', 'me', 'my', 'mine', 'myself'])
        
        # Count occurrences
        negative_count = sum(1 for word in words if word in negative_words)
        positive_count = sum(1 for word in words if word in positive_words)
        first_person_count = sum(1 for word in words if word in first_person)
        
        # Lexical diversity
        unique_words = len(set(words))
        lexical_diversity = unique_words / len(words) if len(words) > 0 else 0
        
        # Sentence count
        sentences = re.split(r'[.!?]+', text)
        sentence_count = len([s for s in sentences if s.strip()])
        
        features = {
            'word_count': len(words),
            'unique_word_count': unique_words,
            'lexical_diversity': lexical_diversity,
            
            'negative_word_count': negative_count,
            'positive_word_count': positive_count,
            'negative_word_ratio': negative_count / len(words) if len(words) > 0 else 0,
            'positive_word_ratio': positive_count / len(words) if len(words) > 0 else 0,
            
            'sentiment_balance': (positive_count - negative_count) / len(words) if len(words) > 0 else 0,
            
            'first_person_count': first_person_count,
            'first_person_ratio': first_person_count / len(words) if len(words) > 0 else 0,
            
            'sentence_count': sentence_count,
            'avg_words_per_sentence': len(words) / sentence_count if sentence_count > 0 else 0
        }
        
        return features
    
    def process_csv(self):
        """
        Process the CSV file and extract features
        """
        print(f"Loading data from {self.csv_path}...")
        df = pd.read_csv(self.csv_path)
        
        print(f"Total participants: {len(df)}")
        print(f"\nColumns in CSV: {list(df.columns)}")
        
        # Extract features for each participant
        feature_rows = []
        
        for idx, row in df.iterrows():
            participant_features = {
                'participant_id': row['participant_id'],
                'age': row['age'],
                'gender': row['gender'],
                'year_of_study': row['year_of_study'],
                'phq9_total': row['phq9_total'],
                'phq9_severity': row['phq9_severity'],
                'depression_label': row['depression_label']
            }
            
            # Add PHQ-9 individual scores
            for i in range(1, 10):
                col_name = f'phq9_q{i}'
                if col_name in df.columns:
                    participant_features[col_name] = row[col_name]
            
            # Copy task features
            if 'copy_task_duration' in df.columns:
                participant_features['copy_task_duration'] = row.get('copy_task_duration', 0)
                participant_features['copy_task_word_count'] = row.get('copy_task_word_count', 0)
                participant_features['copy_task_char_count'] = row.get('copy_task_char_count', 0)
                
                # Calculate typing speed (WPM)
                if row.get('copy_task_duration', 0) > 0:
                    participant_features['copy_task_wpm'] = (row.get('copy_task_word_count', 0) / row['copy_task_duration']) * 60
                else:
                    participant_features['copy_task_wpm'] = 0
            
            # Free writing task features
            if 'free_writing_duration' in df.columns:
                participant_features['free_writing_duration'] = row.get('free_writing_duration', 0)
                participant_features['free_writing_word_count'] = row.get('free_writing_word_count', 0)
                participant_features['free_writing_char_count'] = row.get('free_writing_char_count', 0)
                
                # Calculate typing speed (WPM)
                if row.get('free_writing_duration', 0) > 0:
                    participant_features['free_writing_wpm'] = (row.get('free_writing_word_count', 0) / row['free_writing_duration']) * 60
                else:
                    participant_features['free_writing_wpm'] = 0
                
                # Extract linguistic features from free writing text
                if 'free_writing_text' in df.columns and pd.notna(row.get('free_writing_text')):
                    ling_features = self.extract_linguistic_features(row['free_writing_text'])
                    for key, value in ling_features.items():
                        participant_features[f'free_writing_{key}'] = value
            
            feature_rows.append(participant_features)
        
        # Create feature DataFrame
        feature_df = pd.DataFrame(feature_rows)
        
        print(f"\nFeatures extracted: {len(feature_df.columns)}")
        print(f"\nSample features: {list(feature_df.columns[:10])}")
        
        return feature_df
    
    def save_processed_data(self, feature_df, output_path='processed_dataset.csv'):
        """Save processed features to CSV"""
        feature_df.to_csv(output_path, index=False)
        print(f"\n✅ Processed dataset saved to {output_path}")
        print(f"Total participants: {len(feature_df)}")
        print(f"Total features: {len(feature_df.columns)}")
        
        # Display summary
        print("\n" + "="*60)
        print("DATASET SUMMARY")
        print("="*60)
        print(f"\nDepression Distribution:")
        print(feature_df['depression_label'].value_counts())
        print(f"\nPHQ-9 Severity Distribution:")
        print(feature_df['phq9_severity'].value_counts())
        
        return output_path

def main():
    """
    Main execution
    """
    print("="*60)
    print("CSV FEATURE EXTRACTION")
    print("="*60)
    
    # Initialize extractor
    extractor = CSVFeatureExtractor('all_participant_data.csv')
    
    # Process data
    feature_df = extractor.process_csv()
    
    # Save processed data
    output_file = extractor.save_processed_data(feature_df)
    
    print("\n" + "="*60)
    print("EXTRACTION COMPLETE!")
    print("="*60)
    print(f"\nNext step: Run ML training")
    print(f"Command: python ml_training.py")

if __name__ == "__main__":
    main()
