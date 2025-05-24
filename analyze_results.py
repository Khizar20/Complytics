import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from bert_score import score
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Read the CSV files with different encodings
try:
    # Try different encodings
    encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
    with_reasoning = None
    without_reasoning = None
    
    for encoding in encodings:
        try:
            with_reasoning = pd.read_csv('with reasoning.csv', encoding=encoding)
            without_reasoning = pd.read_csv('without reasoning.csv', encoding=encoding)
            print(f"Successfully read files with {encoding} encoding")
            break
        except UnicodeDecodeError:
            continue
    
    if with_reasoning is None or without_reasoning is None:
        raise Exception("Could not read CSV files with any of the attempted encodings")

    # Function to calculate BERT scores
    def calculate_bert_scores(reference, candidate):
        # Convert inputs to strings and handle NaN values
        if pd.isna(reference) or pd.isna(candidate):
            return 0.0
        
        reference = str(reference)
        candidate = str(candidate)
        
        # Skip empty strings
        if not reference.strip() or not candidate.strip():
            return 0.0
            
        try:
            P, R, F1 = score([candidate], [reference], lang='en', verbose=True)
            return float(F1.numpy()[0])
        except Exception as e:
            print(f"Error calculating BERT score: {str(e)}")
            return 0.0

    # Function to detect hallucinations
    def detect_hallucinations(reference, candidate):
        if pd.isna(reference) or pd.isna(candidate):
            return 1.0  # Consider as hallucination if missing data
        
        reference = str(reference)
        candidate = str(candidate)
        
        if not reference.strip() or not candidate.strip():
            return 1.0
            
        try:
            # Use TF-IDF to compare text similarity
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform([reference, candidate])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            # Convert similarity to hallucination score (1 - similarity)
            # Higher score means more hallucination
            return 1.0 - similarity
        except Exception as e:
            print(f"Error calculating hallucination score: {str(e)}")
            return 1.0

    # Calculate scores for each model
    def process_dataframe(df):
        results = []
        models = ['Answer by RAG', 'Answer by Gemini', 'Answer by Chatgpt', 'Answer By Deepseek']
        
        for _, row in df.iterrows():
            reference = row['Answer by RAG']
            for model in models:
                candidate = row[model]
                bert_score = calculate_bert_scores(reference, candidate)
                hallucination_score = detect_hallucinations(reference, candidate)
                
                results.append({
                    'Model': model,
                    'BERT Score': bert_score,
                    'Hallucination Score': hallucination_score
                })
        return pd.DataFrame(results)

    # Process both dataframes
    print("Processing with reasoning data...")
    with_reasoning_scores = process_dataframe(with_reasoning)
    print("Processing without reasoning data...")
    without_reasoning_scores = process_dataframe(without_reasoning)

    # Set the style for better visualization
    plt.style.use('seaborn')
    
    # Create plots with improved readability
    fig = plt.figure(figsize=(20, 15))
    
    # Set color palette
    colors = sns.color_palette("husl", 4)
    
    # Plot 1: BERT Scores Comparison
    plt.subplot(2, 2, 1)
    bert_with = with_reasoning_scores.groupby('Model')['BERT Score'].mean().reset_index()
    ax1 = sns.barplot(data=bert_with, x='Model', y='BERT Score', palette=colors)
    plt.title('Average BERT Scores - With Reasoning', fontsize=14, pad=20)
    plt.xlabel('Model', fontsize=12)
    plt.ylabel('BERT Score', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.ylim(0, 1)  # Set y-axis limit for better comparison
    
    # Add value labels on top of bars
    for i, v in enumerate(bert_with['BERT Score']):
        ax1.text(i, v + 0.02, f'{v:.2f}', ha='center', fontsize=10)

    plt.subplot(2, 2, 2)
    bert_without = without_reasoning_scores.groupby('Model')['BERT Score'].mean().reset_index()
    ax2 = sns.barplot(data=bert_without, x='Model', y='BERT Score', palette=colors)
    plt.title('Average BERT Scores - Without Reasoning', fontsize=14, pad=20)
    plt.xlabel('Model', fontsize=12)
    plt.ylabel('BERT Score', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.ylim(0, 1)  # Set y-axis limit for better comparison
    
    # Add value labels on top of bars
    for i, v in enumerate(bert_without['BERT Score']):
        ax2.text(i, v + 0.02, f'{v:.2f}', ha='center', fontsize=10)

    # Plot 2: Hallucination Scores Comparison
    plt.subplot(2, 2, 3)
    hall_with = with_reasoning_scores.groupby('Model')['Hallucination Score'].mean().reset_index()
    ax3 = sns.barplot(data=hall_with, x='Model', y='Hallucination Score', palette=colors)
    plt.title('Average Hallucination Scores - With Reasoning', fontsize=14, pad=20)
    plt.xlabel('Model', fontsize=12)
    plt.ylabel('Hallucination Score', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.ylim(0, 1)  # Set y-axis limit for better comparison
    
    # Add value labels on top of bars
    for i, v in enumerate(hall_with['Hallucination Score']):
        ax3.text(i, v + 0.02, f'{v:.2f}', ha='center', fontsize=10)

    plt.subplot(2, 2, 4)
    hall_without = without_reasoning_scores.groupby('Model')['Hallucination Score'].mean().reset_index()
    ax4 = sns.barplot(data=hall_without, x='Model', y='Hallucination Score', palette=colors)
    plt.title('Average Hallucination Scores - Without Reasoning', fontsize=14, pad=20)
    plt.xlabel('Model', fontsize=12)
    plt.ylabel('Hallucination Score', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.ylim(0, 1)  # Set y-axis limit for better comparison
    
    # Add value labels on top of bars
    for i, v in enumerate(hall_without['Hallucination Score']):
        ax4.text(i, v + 0.02, f'{v:.2f}', ha='center', fontsize=10)

    # Add a common legend
    fig.legend(['RAG', 'Gemini', 'ChatGPT', 'Deepseek'], 
              loc='upper center', 
              bbox_to_anchor=(0.5, 0.02),
              ncol=4,
              fontsize=12)

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)  # Make room for the legend
    plt.savefig('model_comparison_scores.png', dpi=300, bbox_inches='tight')
    plt.close()

    # Print interpretations
    print("\nInterpretation of Results:")
    print("\nBERT Scores:")
    print("1. Higher scores indicate better semantic similarity with the reference (RAG) responses")
    print("2. Scores range from 0 to 1, where 1 indicates perfect similarity")
    print("3. The impact of reasoning can be seen by comparing the scores between the two scenarios")
    
    print("\nHallucination Scores:")
    print("1. Lower scores indicate less hallucination (more factual responses)")
    print("2. Scores range from 0 to 1, where 0 indicates no hallucination")
    print("3. The effect of reasoning on reducing hallucinations can be observed by comparing the scores")
    
    print("\nKey Observations:")
    print("1. RAG serves as the baseline for comparison")
    print("2. The difference between with/without reasoning scenarios shows the impact of reasoning")
    print("3. Model performance can be evaluated based on both BERT and hallucination scores")

except Exception as e:
    print(f"An error occurred: {str(e)}")
    raise 