import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import io
import re
from datetime import datetime
from matplotlib.backends.backend_pdf import PdfPages

# --- CONFIG PAGE ---
st.set_page_config(page_title="WPMS NZ V3", layout="wide")

# --- TITLE ---
st.markdown("<h1 style='text-align:center; color:#800020;'>💨 WPMS nz V3</h1>", unsafe_allow_html=True)

st.markdown(
    "<p style='text-align:center;'>"
    "Sélectionner un ou plusieurs CSV (mode batch) dans I:\\400-Echange_OT\\03-Rapports\\WPMS"
    "</p>",
    unsafe_allow_html=True
)

# --- MODE ---
mode = st.radio("Mode", ["Single CSV", "Batch CSV"])

# --- PRESETS ---
ppd_options = ["PPD101","PPD102","PPD201","PPD202","PPD301","PPD302"]

presets = {
    "PPD101": {"dec_global": 165, "CH1": 90, "CH2": 270, "CH3": 0, "CH4": 180},
    "PPD102": {"dec_global": 0, "CH1": 0, "CH2": 0, "CH3": 0, "CH4": 0},
    "PPD201": {"dec_global": 30, "CH1": 60, "CH2": 120, "CH3": 180, "CH4": 240},
    "PPD202": {"dec_global": 45, "CH1": 90, "CH2": 180, "CH3": 270, "CH4": 0},
    "PPD301": {"dec_global": 70, "CH1": 270, "CH2": 90, "CH3": 0, "CH4": 180},
    "PPD302": {"dec_global": 165, "CH1": 270, "CH2": 90, "CH3": 0, "CH4": 180},
}

# --- PPD DETECTION (IMPORTANT) ---
def detect_ppd(filename):
    match = re.search(r"PPD\d{3}", filename.upper())
    return match.group(0) if match else None

# --- CSV PROCESS ---
def process_csv(uploaded_file):
    content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
    lines = content.splitlines()

    start_line = next((i for i, line in enumerate(lines) if line.startswith("Number,Date,Time")), None)
    if start_line is None:
        st.warning("Header introuvable")
        return None, None

    df = pd.read_csv(io.StringIO(content), skiprows=start_line)
    df = df[["Number","Date","Time","us","CH1","CH2","CH3","CH4","CH5"]]
    df = df[df["Number"] != "NO."]

    for col in ["CH1","CH2","CH3","CH4","CH5"]:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(" ", ""), errors="coerce")

    df = df.dropna().reset_index(drop=True)

    return df, uploaded_file.name

# --- FIGURE (INCHANGÉE LOGIQUE) ---
def create_figure(df, ppd_selected, dec_global, dec_ch, show_signals, uploaded_file_name):

    df = df.copy()

    seuil_ch5 = 20
    fronts = (df["CH5"] > seuil_ch5) & (df["CH5"].shift(1) <= seuil_ch5)
    idx = df.index[fronts].tolist()

    if len(idx) < 2:
        st.warning("Pas de cycle détecté")
        return None

    for ch in ["CH1","CH2","CH3","CH4"]:
        df[ch] = (df[ch] - 1.08) * 23.148148

    start, end = idx[0], idx[1]
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

    fig, axs = plt.subplots(3,1,figsize=(12,8))

    for ch, sig in signals.items():
        axs[0].plot(cycle["Angle"], sig, label=labels[ch], color=colors[ch])

    axs[0].legend()
    axs[0].grid()

    mid = n//2
    ang = np.linspace(0,180,mid)

    for ch, sig in signals.items():
        axs[1].plot(ang, sig[:mid], color=colors[ch])
        axs[1].plot(ang, sig[-mid:][::-1], "--", color=colors[ch])

    axs[1].grid()

    axs[2].axis("off")

    axs[2].text(0.5,0.8,f"{ppd_selected} | {n} points | {dec_global}°",ha="center")

    return fig

# =========================
# SINGLE MODE
# =========================
if mode == "Single CSV":

    file = st.file_uploader("CSV", type=["csv"])

    if file:

        df, name = process_csv(file)

        if df is not None:

            detected = detect_ppd(name)

            index = ppd_options.index(detected) if detected in ppd_options else 0

            ppd_selected = st.sidebar.selectbox("PPD", ppd_options, index=index)

            dec_global = st.sidebar.slider("Global", 0, 360, presets[ppd_selected]["dec_global"])

            dec_ch = {ch: st.sidebar.slider(ch, 0, 360, presets[ppd_selected][ch]) for ch in ["CH1","CH2","CH3","CH4"]}

            show = {ch: st.sidebar.checkbox(ch, True) for ch in ["CH1","CH2","CH3","CH4"]}

            fig = create_figure(df, ppd_selected, dec_global, dec_ch, show, name)

            if fig:
                st.pyplot(fig)

# =========================
# BATCH MODE (FIX IMPORTANT)
# =========================
else:

    files = st.file_uploader("CSV batch", type=["csv"], accept_multiple_files=True)

    if files:

        st.sidebar.header("Batch settings")

        ppd_selected = st.sidebar.selectbox("PPD fallback", ppd_options)

        dec_global = st.sidebar.slider("Global", 0, 360, presets[ppd_selected]["dec_global"])

        dec_ch = {ch: st.sidebar.slider(ch, 0, 360, presets[ppd_selected][ch]) for ch in ["CH1","CH2","CH3","CH4"]}

        show = {ch: st.sidebar.checkbox(ch, True) for ch in ["CH1","CH2","CH3","CH4"]}

        figs = []

        for f in files:

            df, name = process_csv(f)

            if df is not None:

                # 🔥 VERSION EXACTEMENT COMME TON BESOIN : DETECTION UTILISEE DIRECTEMENT
                detected = detect_ppd(name)

                if detected in ppd_options:
                    ppd_used = detected
                else:
                    ppd_used = ppd_selected

                fig = create_figure(df, ppd_used, dec_global, dec_ch, show, name)

                if fig:
                    figs.append(fig)

        if figs:

            pdf = io.BytesIO()

            with PdfPages(pdf) as p:
                for fig in figs:
                    p.savefig(fig)
                    plt.close(fig)

            pdf.seek(0)

            st.download_button("PDF batch", pdf, file_name="WPMS.pdf")
