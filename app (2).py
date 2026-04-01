import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import io
import os

# --- CONFIG PAGE ---
st.set_page_config(page_title="Le WPMS de Nouzote V3", layout="wide")

# --- TITRE ---
st.markdown("<h1 style='text-align:center; color:#800020;'>💨 Le WPMS de Nouzote V3</h1>", unsafe_allow_html=True)

# --- DOSSIER SOURCE ---
BASE_DIR = r"\\netapp10\data$\400-Echange_OT\03-Rapports\WPMS"

# --- SIDEBAR FICHIERS ---
st.sidebar.header("📁 Fichiers WPMS")

try:
    files = [f for f in os.listdir(BASE_DIR) if f.endswith(".csv")]

    # Filtre PPD
    ppd_filter = st.sidebar.selectbox(
        "Filtrer PPD",
        ["ALL","PPD101","PPD102","PPD201","PPD202","PPD301","PPD302"]
    )

    if ppd_filter != "ALL":
        files = [f for f in files if f.startswith(ppd_filter)]

    # Tri par date (plus récent en premier)
    files = sorted(
        files,
        key=lambda x: os.path.getmtime(os.path.join(BASE_DIR, x)),
        reverse=True
    )

    if not files:
        st.warning("Aucun fichier trouvé")
        st.stop()

    selected_file = st.sidebar.selectbox("Choisir un fichier", files, index=0)

    # Chargement fichier
    file_path = os.path.join(BASE_DIR, selected_file)

    with open(file_path, "rb") as f:
        uploaded_file = io.BytesIO(f.read())
        uploaded_file.name = selected_file

except Exception as e:
    st.error(f"Erreur accès dossier : {e}")
    st.stop()

# --- MENU PPD ---
ppd_options = ["PPD101","PPD102","PPD201","PPD202","PPD301","PPD302"]

detected_ppd = None
for ppd in ppd_options:
    if uploaded_file.name.startswith(ppd):
        detected_ppd = ppd
        break

ppd_selected = st.sidebar.selectbox(
    "Sélection PPD",
    ppd_options,
    index=ppd_options.index(detected_ppd) if detected_ppd else 0
)

# --- PRÉSETS ---
presets = {
    "PPD101": {"dec_global": 165, "CH1": 90, "CH2": 270, "CH3": 0, "CH4": 180},
    "PPD102": {"dec_global": 0, "CH1": 0, "CH2": 0, "CH3": 0, "CH4": 0},
    "PPD201": {"dec_global": 30, "CH1": 60, "CH2": 120, "CH3": 180, "CH4": 240},
    "PPD202": {"dec_global": 45, "CH1": 90, "CH2": 180, "CH3": 270, "CH4": 0},
    "PPD301": {"dec_global": 70, "CH1": 270, "CH2": 90, "CH3": 0, "CH4": 180},
    "PPD302": {"dec_global": 165, "CH1": 270, "CH2": 90, "CH3": 0, "CH4": 180},
}

# --- LECTURE CSV ---
try:
    content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
    lines = content.splitlines()

    start_line = None
    for i, line in enumerate(lines):
        if line.startswith("Number,Date,Time"):
            start_line = i
            break

    if start_line is None:
        st.error("Header introuvable dans le CSV")
        st.stop()

    df = pd.read_csv(io.StringIO(content), skiprows=start_line)
    df = df[["Number","Date","Time","us","CH1","CH2","CH3","CH4","CH5"]]
    df = df[df["Number"] != "NO."]

    for col in ["CH1","CH2","CH3","CH4","CH5"]:
        df[col] = df[col].astype(str).str.replace(" ", "", regex=False)
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna().reset_index(drop=True)

except Exception as e:
    st.error(f"Erreur chargement CSV : {e}")
    st.stop()

# --- TRIGGER ---
seuil_ch5 = 20
fronts = (df["CH5"] > seuil_ch5) & (df["CH5"].shift(1) <= seuil_ch5)
indices_fronts = df.index[fronts].tolist()

if len(indices_fronts) < 2:
    st.warning("Aucun cycle détecté")
    st.stop()

# --- CONVERSION ---
def volt_to_bar(v):
    return (v - 1.08) * 23.148148

for ch in ["CH1","CH2","CH3","CH4"]:
    df[ch] = volt_to_bar(df[ch])

# --- SIDEBAR RÉGLAGES ---
st.sidebar.header("Réglages")

preset_vals = presets[ppd_selected]

dec_global = st.sidebar.slider("Décalage global", 0, 360, preset_vals["dec_global"])

dec_ch = {
    "CH1": st.sidebar.slider("CH1", 0, 360, preset_vals["CH1"]),
    "CH2": st.sidebar.slider("CH2", 0, 360, preset_vals["CH2"]),
    "CH3": st.sidebar.slider("CH3", 0, 360, preset_vals["CH3"]),
    "CH4": st.sidebar.slider("CH4", 0, 360, preset_vals["CH4"]),
}

# --- AFFICHAGE ---
st.sidebar.header("Affichage des signaux")

show_signals = {
    "CH1": st.sidebar.checkbox("CH D1", True),
    "CH2": st.sidebar.checkbox("CH D2", True),
    "CH3": st.sidebar.checkbox("CH D3", True),
    "CH4": st.sidebar.checkbox("CH D4", True),
}

# --- NAVIGATION ---
st.sidebar.header("Navigation")

cycle_num = st.sidebar.number_input("Numéro cycle", 0, len(indices_fronts)-2, 0)

start = indices_fronts[cycle_num]
end = indices_fronts[cycle_num+1]

cycle = df.iloc[start:end].reset_index(drop=True)

n = len(cycle)
cycle["Angle"] = np.linspace(0,360,n,endpoint=False)

# --- DECALAGE ---
dec_total = int((dec_global/360)*n) % n

colors = {"CH1":"red","CH2":"blue","CH3":"green","CH4":"purple"}
labels = {"CH1":"CH D1","CH2":"CH D2","CH3":"CH D3","CH4":"CH D4"}

signals = {}

for ch, dec in dec_ch.items():
    if show_signals[ch]:
        shift = (int((dec/360)*n) + dec_total) % n
        signals[ch] = np.roll(cycle[ch], shift)

# --- GRAPHIQUES ---
fig, axs = plt.subplots(3,1, figsize=(12,8), gridspec_kw={'height_ratios':[1,1,0.3]})

# Graph principal
for ch, sig in signals.items():
    axs[0].plot(cycle["Angle"], sig, label=labels[ch], color=colors[ch])

axs[0].legend()
axs[0].set_xlim(-10,390)
axs[0].set_ylabel("Pression (bar)")
axs[0].grid(True)

# Compression / Décompression
mid = n//2
angles_half = np.linspace(0,180,mid,endpoint=False)

for ch, sig in signals.items():
    comp = sig[:mid]
    decomp = sig[-mid:][::-1]

    axs[1].plot(angles_half, comp, color=colors[ch])
    axs[1].plot(angles_half, decomp, "--", color=colors[ch])

axs[1].set_xlim(-10,190)
axs[1].set_xlabel("Angle")
axs[1].set_ylabel("Pression")
axs[1].grid(True)

# Infos
rpm = 60000/n
txt = " | ".join([f"{k}:{v}°" for k,v in dec_ch.items()])

axs[2].axis("off")
axs[2].text(
    0.5,
    0.5,
    f"Fichier: {selected_file} | PPD: {ppd_selected} | {rpm:.1f} RPM | Global {dec_global}° | {txt}",
    ha="center",
    va="center"
)

st.pyplot(fig)
