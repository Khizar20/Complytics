import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set the style for better visualization
plt.style.use('bmh')  # Using a built-in style instead of seaborn

# Data for with reasoning
bert_with = pd.DataFrame({
    'Model': ['RAG', 'Gemini', 'ChatGPT', 'Deepseek'],
    'Score': [0.862314, 0.818860, 0.819641, 0.835427]
})

hall_with = pd.DataFrame({
    'Model': ['RAG', 'Gemini', 'ChatGPT', 'Deepseek'],
    'Score': [0.280352, 0.384761, 0.397133, 0.577599]
})

# Data for without reasoning
bert_without = pd.DataFrame({
    'Model': ['RAG', 'Gemini', 'ChatGPT', 'Deepseek'],
    'Score': [0.215385, 0.178189, 0.179528, 0.181178]
})

hall_without = pd.DataFrame({
    'Model': ['RAG', 'Gemini', 'ChatGPT', 'Deepseek'],
    'Score': [0.784615, 0.862870, 0.866231, 0.882258]
})

# Set color palette
colors = sns.color_palette("husl", 4)

# Plot 1: BERT Scores With Reasoning
plt.figure(figsize=(10, 6))
ax1 = sns.barplot(data=bert_with, x='Model', y='Score', palette=colors)
plt.title('BERT Scores - With Reasoning', fontsize=14, pad=20)
plt.xlabel('Model', fontsize=12)
plt.ylabel('BERT Score', fontsize=12)
plt.ylim(0.7, 1.1)  # Adjusted scale for better visualization
plt.xticks(rotation=45, ha='right')

# Add value labels on top of bars
for i, v in enumerate(bert_with['Score']):
    ax1.text(i, v + 0.02, f'{v:.3f}', ha='center', fontsize=10)

plt.tight_layout()
plt.savefig('bert_scores_with_reasoning.png', dpi=300, bbox_inches='tight')
plt.close()

# Plot 2: BERT Scores Without Reasoning
plt.figure(figsize=(10, 6))
ax2 = sns.barplot(data=bert_without, x='Model', y='Score', palette=colors)
plt.title('BERT Scores - Without Reasoning', fontsize=14, pad=20)
plt.xlabel('Model', fontsize=12)
plt.ylabel('BERT Score', fontsize=12)
plt.ylim(0, 0.3)  # Adjusted scale for better visualization
plt.xticks(rotation=45, ha='right')

# Add value labels on top of bars
for i, v in enumerate(bert_without['Score']):
    ax2.text(i, v + 0.01, f'{v:.3f}', ha='center', fontsize=10)

plt.tight_layout()
plt.savefig('bert_scores_without_reasoning.png', dpi=300, bbox_inches='tight')
plt.close()

# Plot 3: Hallucination Scores With Reasoning
plt.figure(figsize=(10, 6))
ax3 = sns.barplot(data=hall_with, x='Model', y='Score', palette=colors)
plt.title('Hallucination Scores - With Reasoning', fontsize=14, pad=20)
plt.xlabel('Model', fontsize=12)
plt.ylabel('Hallucination Score', fontsize=12)
plt.ylim(0, 0.7)  # Adjusted scale for better visualization
plt.xticks(rotation=45, ha='right')

# Add value labels on top of bars
for i, v in enumerate(hall_with['Score']):
    ax3.text(i, v + 0.02, f'{v:.3f}', ha='center', fontsize=10)

plt.tight_layout()
plt.savefig('hallucination_scores_with_reasoning.png', dpi=300, bbox_inches='tight')
plt.close()

# Plot 4: Hallucination Scores Without Reasoning
plt.figure(figsize=(10, 6))
ax4 = sns.barplot(data=hall_without, x='Model', y='Score', palette=colors)
plt.title('Hallucination Scores - Without Reasoning', fontsize=14, pad=20)
plt.xlabel('Model', fontsize=12)
plt.ylabel('Hallucination Score', fontsize=12)
plt.ylim(0.7, 1.0)  # Adjusted scale for better visualization
plt.xticks(rotation=45, ha='right')

# Add value labels on top of bars
for i, v in enumerate(hall_without['Score']):
    ax4.text(i, v + 0.01, f'{v:.3f}', ha='center', fontsize=10)

plt.tight_layout()
plt.savefig('hallucination_scores_without_reasoning.png', dpi=300, bbox_inches='tight')
plt.close()

print("Plots have been generated successfully!") 