import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import io
import re
from datetime import datetime
from matplotlib.backends.backend_pdf import PdfPages

# --- CONFIG PAGE ---
st.set_page_config(page_title="Le WPMS de Nouzote V3", layout="wide")

# --- TITRE ---
st.markdown("<h1 style='text-align:center; color:#800020;'>💨 Le WPMS de Nouzote V3</h1>", unsafe_allow_html=True)

# --- MODE ---
mode = st.radio("Mode", ["Single CSV", "Batch CSV"])

# --- PRÉSETS ---
ppd_options = ["PPD101","PPD102","PPD201","PPD202","PPD301","PPD302"]
presets = {
    "PPD101": {"dec_global": 165, "CH1": 90, "CH2": 270, "CH3": 0, "CH4": 180},
    "PPD102": {"dec_global": 0, "CH1": 0, "CH2": 0, "CH3": 0, "CH4": 0},
    "PPD201": {"dec_global": 30, "CH1": 60, "CH2": 120, "CH3": 180, "CH4": 240},
    "PPD202": {"dec_global": 45, "CH1": 90, "CH2": 180, "CH3": 270, "CH4": 0},
    "PPD301": {"dec_global": 70, "CH1": 270, "CH2": 90, "CH3": 0, "CH4": 180},
    "PPD302": {"dec_global": 165, "CH1": 270, "CH2": 90, "CH3": 0, "CH4": 180},
}

# --- FONCTION: EXTRACTION POMPE + DATE/HEURE ---
def parse_filename_info(filename):
    ppd_match = re.search(r"(PPD\d{3})", filename)
    ppd = ppd_match.group(1) if ppd_match else "PPD inconnue"
    date_match = re.search(r"_(\d{6})-(\d{6})", filename)
    if date_match:
        date_str, time_str = date_match.groups()
        dt = datetime.strptime(date_str+time_str, "%y%m%d%H%M%S")
        dt_str = dt.strftime("%d/%m/%y %H:%M:%S")
    else:
        dt_str = "Date inconnue"
    return ppd, dt_str

# --- FONCTION: TRAITEMENT CSV ---
def process_csv(uploaded_file):
    try:
        content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        lines = content.splitlines()
        start_line = next((i for i, line in enumerate(lines) if line.startswith("Number,Date,Time")), None)
        if start_line is None:
            st.warning(f"Header introuvable dans {uploaded_file.name}")
            return None, None
        df = pd.read_csv(io.StringIO(content), skiprows=start_line)
        df = df[["Number","Date","Time","us","CH1","CH2","CH3","CH4","CH5"]]
        df = df[df["Number"] != "NO."]
        for col in ["CH1","CH2","CH3","CH4","CH5"]:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(" ", "", regex=False), errors="coerce")
        df = df.dropna().reset_index(drop=True)
        return df, uploaded_file.name
    except Exception as e:
        st.warning(f"Erreur fichier {uploaded_file.name} : {e}")
        return None, None

# --- FONCTION: CREATION FIGURE ---
def create_figure(df, ppd_selected, dec_global, dec_ch, show_signals, uploaded_file_name):
    seuil_ch5 = 20
    fronts = (df["CH5"] > seuil_ch5) & (df["CH5"].shift(1) <= seuil_ch5)
    indices_fronts = df.index[fronts].tolist()
    if len(indices_fronts) < 2:
        st.warning(f"Aucun cycle détecté pour {uploaded_file_name}")
        return None

    # conversion pression
    for ch in ["CH1","CH2","CH3","CH4"]:
        df[ch] = (df[ch] - 1.08) * 23.148148

    start, end = indices_fronts[0], indices_fronts[1]
    cycle = df.iloc[start:end].reset_index(drop=True)
    n = len(cycle)
    cycle["Angle"] = np.linspace(0,360,n,endpoint=False)
    dec_total = int((dec_global/360)*n) % n

    colors = {"CH1":"red","CH2":"blue","CH3":"green","CH4":"purple"}
    labels = {"CH1":"CH D1","CH2":"CH D2","CH3":"CH D3","CH4":"CH D4"}
    signals = {}
    for ch, dec in dec_ch.items():
        if show_signals[ch]:
            shift = (int((dec/360)*n) + dec_total) % n
            signals[ch] = np.roll(cycle[ch], shift)

    # --- FIGURE ---
    fig, axs = plt.subplots(3,1, figsize=(12,8), gridspec_kw={'height_ratios':[1,1,0.4]})

    # --- HAUT: courbes brutes ---
    for ch, sig in signals.items():
        axs[0].plot(cycle["Angle"], sig, label=labels[ch], color=colors[ch])
    axs[0].legend()
    axs[0].set_xlim(-10,390)
    axs[0].set_ylabel("Pression (bar)")
    axs[0].grid(True)

    # --- MILIEU: compression / decompression ---
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

    # --- BAS: stats ---
    stats_txt = ""
    couples = [("CH1","CH4"),("CH2","CH3")]
    for c1,c2 in couples:
        sig1, sig2 = signals.get(c1), signals.get(c2)
        if sig1 is not None and sig2 is not None:
            max1,max2 = sig1.max(), sig2.max()
            min1,min2 = sig1.min(), sig2.min()
            mean1,mean2 = sig1.mean(), sig2.mean()
            # déphasage approx: angle du max
            idx_max1, idx_max2 = np.argmax(sig1), np.argmax(sig2)
            deph = ((idx_max2-idx_max1)/n)*360
            stats_txt += (f"{labels[c1]}+{labels[c2]} | Max:{max1:.1f}/{max2:.1f} "
                          f"Min:{min1:.1f}/{min2:.1f} "
                          f"Moy:{mean1:.1f}/{mean2:.1f} "
                          f"Déphasage:{deph:.1f}°\n")
    axs[2].axis("off")
    axs[2].text(0.5,0.5, stats_txt, ha="center", va="center", fontsize=10, family='monospace')

    # --- TITRE EN HAUT ---
    ppd_name, dt_str = parse_filename_info(uploaded_file_name)
    fig.suptitle(f"Pompe: {ppd_name} | Heure: {dt_str}", fontsize=16, color="#800020")

    return fig

# --- SINGLE CSV ---
if mode == "Single CSV":
    uploaded_file = st.file_uploader("📂 Charger un fichier CSV", type=["csv"])
    if uploaded_file:
        df, filename = process_csv(uploaded_file)
        if df is not None:
            detected_ppd = next((ppd for ppd in ppd_options if uploaded_file.name.startswith(ppd)), None)
            ppd_selected = st.sidebar.selectbox("Sélection PPD", ppd_options, index=ppd_options.index(detected_ppd) if detected_ppd else 0)
            preset_vals = presets[ppd_selected]
            dec_global = st.sidebar.slider("Décalage global", 0, 360, preset_vals["dec_global"])
            dec_ch = {ch: st.sidebar.slider(ch, 0, 360, preset_vals[ch]) for ch in ["CH1","CH2","CH3","CH4"]}
            st.sidebar.header("Affichage des signaux")
            show_signals = {ch: st.sidebar.checkbox(ch, True) for ch in ["CH1","CH2","CH3","CH4"]}
            fig = create_figure(df, ppd_selected, dec_global, dec_ch, show_signals, filename)
            if fig:
                st.pyplot(fig)
    else:
        st.info("Chargez un fichier CSV")

# --- BATCH CSV ---
else:
    uploaded_files = st.file_uploader("📂 Charger plusieurs CSV", type=["csv"], accept_multiple_files=True)
    if uploaded_files:
        st.info("Traitement batch en cours...")
        figs = []
        for uploaded_file in uploaded_files:
            df, filename = process_csv(uploaded_file)
            if df is not None:
                detected_ppd = next((ppd for ppd in ppd_options if uploaded_file.name.startswith(ppd)), None)
                ppd_selected = st.sidebar.selectbox(f"PPD pour {filename}", ppd_options, index=ppd_options.index(detected_ppd) if detected_ppd else 0)
                preset_vals = presets[ppd_selected]
                dec_global = st.sidebar.slider(f"Décalage global {filename}", 0, 360, preset_vals["dec_global"])
                dec_ch = {ch: st.sidebar.slider(f"{ch} {filename}", 0, 360, preset_vals[ch]) for ch in ["CH1","CH2","CH3","CH4"]}
                st.sidebar.header(f"Affichage des signaux {filename}")
                show_signals = {ch: st.sidebar.checkbox(f"{ch} {filename}", True) for ch in ["CH1","CH2","CH3","CH4"]}
                fig = create_figure(df, ppd_selected, dec_global, dec_ch, show_signals, filename)
                if fig:
                    figs.append(fig)
        # PDF batch
        if figs:
            pdf_bytes = io.BytesIO()
            with PdfPages(pdf_bytes) as pdf:
                for fig in figs:
                    pdf.savefig(fig)
                    plt.close(fig)
            pdf_bytes.seek(0)
            st.download_button("Télécharger PDF batch", pdf_bytes, file_name="WPMS_batch.pdf")
    else:
        st.info("Chargez au moins un fichier CSV pour le mode batch")
