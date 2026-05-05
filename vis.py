import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

# 1. Load the data
filename = 'benchmark_results'
df = pd.read_csv(f'{filename}.csv')

# Clean up script names for the chart labels
df['Script'] = df['Script'].replace({
    './playwright_script.py': 'Playwright',
    './selenium_script.py': 'Selenium'
})

# ============================================================
# CHART 1: Average Execution Time (Bar Chart)
# ============================================================
fig1, ax1 = plt.subplots(figsize=(10, 6))
speed_data = df.groupby('Script')['Total_Time_Sec'].mean()
colors = ['#2ca02c', '#4285f4']  # Green for Playwright, Blue for Selenium

bars = ax1.bar(speed_data.index, speed_data.values, color=colors, width=0.5)
ax1.set_title('Rata-Rata Waktu Eksekusi', fontsize=14, fontweight='bold')
ax1.set_ylabel('Detik (Lebih rendah lebih baik)', fontsize=12)
ax1.set_ylim(0, 50)
ax1.grid(axis='y', alpha=0.3, linestyle='--')

# Add text labels on top of the bars
for bar in bars:
    yval = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2, yval + 1, f'{round(yval, 2)}s', 
             ha='center', va='bottom', fontweight='bold', fontsize=11)

plt.tight_layout()
plt.savefig(f'{filename}_execution_time.png', dpi=300, bbox_inches='tight')
print(f"Chart 1 saved as '{filename}_execution_time.png'")
plt.close(fig1)

# ============================================================
# CHART 2: Accessibility Violations (Grouped Column Chart)
# ============================================================
fig2, ax2 = plt.subplots(figsize=(12, 6))
axe_cols = ['Axe_Login', 'Axe_Dashboard', 'Axe_Files', 'Axe_Settings']
pw_axe = df[df['Script'] == 'Playwright'][axe_cols].iloc[0].values
sel_axe = df[df['Script'] == 'Selenium'][axe_cols].iloc[0].values

pages = ['Login', 'Dashboard', 'Files', 'Settings']
x = np.arange(len(pages))
width = 0.35

# Create grouped columns
rects1 = ax2.bar(x - width/2, pw_axe, width, label='Playwright', color='#2ca02c')
rects2 = ax2.bar(x + width/2, sel_axe, width, label='Selenium', color='#4285f4')

ax2.set_title('Pelanggaran Axe Accessibility Terdeteksi', fontsize=14, fontweight='bold')
ax2.set_ylabel('Jumlah Pelanggaran (Lebih tinggi = Lebih ketat)', fontsize=12)
ax2.set_xticks(x)
ax2.set_xticklabels(pages)
ax2.legend(fontsize=11)
ax2.set_ylim(0, max(sel_axe) + 1)
ax2.grid(axis='y', alpha=0.3, linestyle='--')

# Add text labels on top of the grouped bars
for rects in [rects1, rects2]:
    for rect in rects:
        height = rect.get_height()
        ax2.annotate(f'{int(height)}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontweight='bold')

plt.tight_layout()
plt.savefig(f'{filename}_accessibility_violations.png', dpi=300, bbox_inches='tight')
print(f"Chart 2 saved as '{filename}_accessibility_violations.png'")
plt.close(fig2)

# ============================================================
# CHART 3: CPU Over Iterations (Line Chart with Regression)
# ============================================================
fig3, ax3 = plt.subplots(figsize=(10, 6))

# Separate data by script
pw_df = df[df['Script'] == 'Playwright'].sort_values('Iteration')
sel_df = df[df['Script'] == 'Selenium'].sort_values('Iteration')

# CPU Usage Over Time
ax3.plot(pw_df['Iteration'], pw_df['Avg_CPU_%'], marker='o', linewidth=2.5, 
         label='Playwright', color='#2ca02c', markersize=8)
ax3.plot(sel_df['Iteration'], sel_df['Avg_CPU_%'], marker='s', linewidth=2.5, 
         label='Selenium', color='#4285f4', markersize=8)

# Add linear regression lines
if len(pw_df) > 1:
    z_pw = np.polyfit(pw_df['Iteration'], pw_df['Avg_CPU_%'], 1)
    p_pw = np.poly1d(z_pw)
    ax3.plot(pw_df['Iteration'], p_pw(pw_df['Iteration']), linestyle='--', 
             color='#2ca02c', alpha=0.6, linewidth=2)

if len(sel_df) > 1:
    z_sel = np.polyfit(sel_df['Iteration'], sel_df['Avg_CPU_%'], 1)
    p_sel = np.poly1d(z_sel)
    ax3.plot(sel_df['Iteration'], p_sel(sel_df['Iteration']), linestyle='--', 
             color='#4285f4', alpha=0.6, linewidth=2)

ax3.set_title('Penggunaan CPU ', fontsize=12, fontweight='bold')
ax3.set_xlabel('Iterasi', fontsize=11)
ax3.set_ylabel('Penggunaan CPU (%)', fontsize=11)
ax3.legend(fontsize=10)
ax3.grid(True, alpha=0.3, linestyle='--')

plt.tight_layout()
plt.savefig(f'{filename}_cpu_metrics.png', dpi=300, bbox_inches='tight')
print(f"Chart 3 saved as '{filename}_cpu_metrics.png'")
plt.close(fig3)

# ============================================================
# CHART 4: Memory Over Iterations (Line Chart with Regression)
# ============================================================
fig4, ax4 = plt.subplots(figsize=(10, 6))

# Memory Usage Over Time
ax4.plot(pw_df['Iteration'], pw_df['Avg_Mem_MB'], marker='o', linewidth=2.5, 
         label='Playwright', color='#2ca02c', markersize=8)
ax4.plot(sel_df['Iteration'], sel_df['Avg_Mem_MB'], marker='s', linewidth=2.5, 
         label='Selenium', color='#4285f4', markersize=8)

# Add linear regression lines
if len(pw_df) > 1:
    z_pw = np.polyfit(pw_df['Iteration'], pw_df['Avg_Mem_MB'], 1)
    p_pw = np.poly1d(z_pw)
    ax4.plot(pw_df['Iteration'], p_pw(pw_df['Iteration']), linestyle='--', 
             color='#2ca02c', alpha=0.6, linewidth=2)

if len(sel_df) > 1:
    z_sel = np.polyfit(sel_df['Iteration'], sel_df['Avg_Mem_MB'], 1)
    p_sel = np.poly1d(z_sel)
    ax4.plot(sel_df['Iteration'], p_sel(sel_df['Iteration']), linestyle='--', 
             color='#4285f4', alpha=0.6, linewidth=2)

ax4.set_title('Penggunaan Memori', fontsize=12, fontweight='bold')
ax4.set_xlabel('Iterasi', fontsize=11)
ax4.set_ylabel('Memori (MB)', fontsize=11)
ax4.legend(fontsize=10)
ax4.grid(True, alpha=0.3, linestyle='--')

plt.tight_layout()
plt.savefig(f'{filename}_memory_metrics.png', dpi=300, bbox_inches='tight')
print(f"Chart 4 saved as '{filename}_memory_metrics.png'")
plt.close(fig4)

# ============================================================
# CHART 5: Execution Time Over Iterations (Line Chart with Regression)
# ============================================================
fig5, ax5 = plt.subplots(figsize=(10, 6))

# Execution Time Over Iterations
ax5.plot(pw_df['Iteration'], pw_df['Total_Time_Sec'], marker='o', linewidth=2.5, 
         label='Playwright', color='#2ca02c', markersize=8)
ax5.plot(sel_df['Iteration'], sel_df['Total_Time_Sec'], marker='s', linewidth=2.5, 
         label='Selenium', color='#4285f4', markersize=8)

# Add linear regression lines
if len(pw_df) > 1:
    z_pw = np.polyfit(pw_df['Iteration'], pw_df['Total_Time_Sec'], 1)
    p_pw = np.poly1d(z_pw)
    ax5.plot(pw_df['Iteration'], p_pw(pw_df['Iteration']), linestyle='--', 
             color='#2ca02c', alpha=0.6, linewidth=2)

if len(sel_df) > 1:
    z_sel = np.polyfit(sel_df['Iteration'], sel_df['Total_Time_Sec'], 1)
    p_sel = np.poly1d(z_sel)
    ax5.plot(sel_df['Iteration'], p_sel(sel_df['Iteration']), linestyle='--', 
             color='#4285f4', alpha=0.6, linewidth=2)

ax5.set_title('Waktu Eksekusi Seiring Waktu', fontsize=12, fontweight='bold')
ax5.set_xlabel('Iterasi', fontsize=11)
ax5.set_ylabel('Waktu Eksekusi (Detik)', fontsize=11)
ax5.legend(fontsize=10)
ax5.grid(True, alpha=0.3, linestyle='--')

plt.tight_layout()
plt.savefig(f'{filename}_execution_time_metrics.png', dpi=300, bbox_inches='tight')
print(f"Chart 5 saved as '{filename}_execution_time_metrics.png'")
plt.close(fig5)

print("\nAll visualizations have been generated successfully!")