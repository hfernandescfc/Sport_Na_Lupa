import matplotlib.pyplot as plt
import numpy as np

# -------------------------
# Dados (extraídos da imagem)
# -------------------------
players = [
    "Felipinho", "Zé Gabriel", "C. Barletta", "Marcelo Ajul",
    "Yago Felipe", "Perotti", "Zé Marcos", "Augusto Pucci",
    "Biel Fonseca", "Zé Lucas"
]

minutes = [450, 423, 345, 332, 316, 307, 304, 301, 270, 252]

data = np.array([
    [16.1, 16.2, 17.4, 16.6, 14.8, 4.7],
    [16.6, 15.1, 13.2, 13.8, 14.8, 2.3],
    [5.6, 9.3, 9.4, 17.3, 9.6, 30.2],
    [14.4, 7.5, 12.1, 15.3, 13.3, np.nan],
    [9.7, 11.6, 9.5, 7.8, 10.4, 14.0],
    [2.2, 2.3, 4.0, 0.9, 8.1, 27.9],
    [15.7, 11.8, 12.6, 13.7, 5.9, 4.7],
    [6.9, 8.1, 8.8, 4.1, 8.9, 2.3],
    [7.2, 10.8, 7.1, 4.5, 5.9, 7.0],
    [5.5, 7.3, 5.8, 6.1, 8.1, 7.0]
])

cols = [
    "PASSES\nCOMPL.", "PASSES\nADV.",
    "AÇÕES\nBOLA", "PROGRESSÃO",
    "RECUP.", "FINAL."
]

# -------------------------
# Setup
# -------------------------
fig, ax = plt.subplots(figsize=(10, 12))
fig.patch.set_facecolor("#0b0b0b")
ax.set_facecolor("#0b0b0b")

ax.set_xlim(0, len(cols)+2)
ax.set_ylim(0, len(players)+1)

# -------------------------
# Destaque (maiores por coluna)
# -------------------------
max_vals = np.nanmax(data, axis=0)

# -------------------------
# Plot
# -------------------------
for i, player in enumerate(players):
    y = len(players) - i
    
    # Nome + minutos
    ax.text(0.2, y, player, color="white", fontsize=11, va="center")
    ax.text(0.2, y-0.35, f"{minutes[i]} min", color="#888", fontsize=8)
    
    for j, val in enumerate(data[i]):
        x = j + 2
        
        if np.isnan(val):
            ax.scatter(x, y, s=1200, facecolors='none', edgecolors="#333", linewidth=1)
            continue
        
        # Intensidade
        intensity = val / max_vals[j]
        
        # Cor base
        color = (1.0, 0.8 * intensity, 0.0)  # dourado
        
        # Destaque máximo
        if val == max_vals[j]:
            edge = "white"
            lw = 2.5
            size = 1400
        else:
            edge = "#222"
            lw = 1
            size = 1200
        
        ax.scatter(x, y, s=size, color=color, edgecolors=edge, linewidth=lw)
        
        ax.text(x, y, f"{val:.1f}%", ha='center', va='center',
                color="white", fontsize=9, fontweight="bold")

# -------------------------
# Cabeçalho
# -------------------------
for j, col in enumerate(cols):
    ax.text(j+2, len(players)+0.5, col,
            color="#f5c518", ha="center", fontsize=10, fontweight="bold")

# -------------------------
# Título
# -------------------------
ax.text(0.2, len(players)+1,
        "CONTRIBUIÇÃO NA SÉRIE B 2026",
        color="white", fontsize=16, fontweight="bold")

ax.text(0.2, len(players)+0.7,
        "Top jogadores por contribuição relativa • destaque automático por métrica",
        color="#aaa", fontsize=9)

# -------------------------
# Limpeza
# -------------------------
ax.axis('off')

plt.tight_layout()
plt.savefig("visualizacao_x.png", dpi=300, facecolor=fig.get_facecolor())
plt.show()