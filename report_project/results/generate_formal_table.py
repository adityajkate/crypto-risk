import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Set up professional academic style
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
plt.rcParams['font.size'] = 28

# Data
papers = ['L-FED (2025)', 'HSIF (2025)', 'Crypto Risk Lens\n(Our Project)']
categories = ['Real-time\nAnalysis', 'Multi-model\nEnsemble', 'Sentiment\nAnalysis',
              'Technical\nIndicators', 'Interactive\nUI', 'Production\nDeployment']
scores = np.array([
    [4, 8, 8, 7, 0, 3],  # L-FED
    [5, 7, 9, 6, 0, 4],  # HSIF
    [9, 9, 8, 9, 9, 8]   # Ours
])
totals = scores.sum(axis=1)

# Create figure
fig, ax = plt.subplots(figsize=(54, 18), dpi=100)
ax.axis('off')

# Define colors - professional grayscale with accent
header_bg = '#2c3e50'
row_bg_1 = '#ecf0f1'
row_bg_2 = '#ffffff'
highlight_bg = '#e8f4f8'
border_color = '#34495e'
text_color = '#2c3e50'
score_excellent = '#27ae60'
score_good = '#f39c12'
score_poor = '#e74c3c'

# Table dimensions
n_rows = len(papers) + 1  # +1 for header
n_cols = len(categories) + 2  # +2 for paper name and total

col_widths = [0.20] + [0.11] * len(categories) + [0.12]
row_height = 1.0 / n_rows

# Draw header row
y_pos = 1.0 - row_height
header_rect = mpatches.Rectangle((0, y_pos), 1.0, row_height,
                                  facecolor=header_bg, edgecolor=border_color,
                                  linewidth=3, zorder=1)
ax.add_patch(header_rect)

# Header text
x_pos = 0
ax.text(x_pos + col_widths[0]/2, y_pos + row_height/2, 'Research Work',
        ha='center', va='center', fontsize=32, fontweight='bold', color='white')
x_pos += col_widths[0]

for i, cat in enumerate(categories):
    ax.text(x_pos + col_widths[i+1]/2, y_pos + row_height/2, cat,
            ha='center', va='center', fontsize=28, fontweight='bold', color='white')
    x_pos += col_widths[i+1]

ax.text(x_pos + col_widths[-1]/2, y_pos + row_height/2, 'Total\nScore',
        ha='center', va='center', fontsize=32, fontweight='bold', color='white')

# Draw data rows
for row_idx, (paper, score_row, total) in enumerate(zip(papers, scores, totals)):
    y_pos = 1.0 - (row_idx + 2) * row_height

    # Highlight our project
    if row_idx == 2:
        bg_color = highlight_bg
    else:
        bg_color = row_bg_1 if row_idx % 2 == 0 else row_bg_2

    # Row background
    row_rect = mpatches.Rectangle((0, y_pos), 1.0, row_height,
                                   facecolor=bg_color, edgecolor=border_color,
                                   linewidth=2, zorder=1)
    ax.add_patch(row_rect)

    # Paper name
    x_pos = 0
    font_weight = 'bold' if row_idx == 2 else 'normal'
    ax.text(x_pos + col_widths[0]/2, y_pos + row_height/2, paper,
            ha='center', va='center', fontsize=30, fontweight=font_weight,
            color=text_color)
    x_pos += col_widths[0]

    # Scores
    for col_idx, score in enumerate(score_row):
        # Determine score color
        if score >= 8:
            score_color = score_excellent
        elif score >= 5:
            score_color = score_good
        else:
            score_color = score_poor

        ax.text(x_pos + col_widths[col_idx+1]/2, y_pos + row_height/2,
                f'{score}', ha='center', va='center', fontsize=34,
                fontweight='bold', color=score_color)
        x_pos += col_widths[col_idx+1]

    # Total score
    ax.text(x_pos + col_widths[-1]/2, y_pos + row_height/2,
            f'{total}', ha='center', va='center', fontsize=36,
            fontweight='bold', color=text_color)

# Draw vertical grid lines
x_pos = 0
for width in col_widths:
    ax.plot([x_pos, x_pos], [0, 1], color=border_color, linewidth=2, zorder=2)
    x_pos += width
ax.plot([1.0, 1.0], [0, 1], color=border_color, linewidth=2, zorder=2)

# Draw horizontal grid lines
for i in range(n_rows + 1):
    y_pos = 1.0 - i * row_height
    ax.plot([0, 1], [y_pos, y_pos], color=border_color, linewidth=2, zorder=2)

# Add legend
legend_y = -0.08
legend_elements = [
    mpatches.Patch(facecolor=score_excellent, label='Excellent (8-10)'),
    mpatches.Patch(facecolor=score_good, label='Good (5-7)'),
    mpatches.Patch(facecolor=score_poor, label='Limited (0-4)')
]
ax.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, legend_y),
          ncol=3, frameon=True, fontsize=28, edgecolor=border_color, fancybox=False)

# Add title
fig.text(0.5, 0.98, 'Comparative Analysis: State-of-the-Art vs. Crypto Risk Lens',
         ha='center', va='top', fontsize=40, fontweight='bold', color=header_bg)

# Add note
fig.text(0.5, 0.01, 'Scoring Scale: 0-10 | Higher scores indicate better capability',
         ha='center', va='bottom', fontsize=24, style='italic', color=text_color)

plt.xlim(0, 1)
plt.ylim(0, 1)
plt.tight_layout(rect=[0, 0.02, 1, 0.97])

# Save
output_path = r'C:\Users\adity\OneDrive\Desktop\crypto-risk\results\2_formal_table_4k.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
plt.close()

print(f"Formal academic table saved: {output_path}")
