
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import io
import re
from datetime import datetime
from matplotlib.backends.backend_pdf import PdfPages

# ============================================================
# CONFIGURATION PAGE
# ============================================================

st.set_page_config(
    page_title="Le WPMS de Nouzote V3",
    layout="wide"
)

# ============================================================
# TITRE + LOGO
# ============================================================

col1, col2 = st.columns([2, 5])

with col1:
    st.image("logo2.jpeg", width=800)

with col2:
    st.markdown(
        "<h1 style='text-align:left; color:#800020;'>"
        "💨 WPMS NZ V3</h1>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<p style='text-align:left;'>"
        "Sélectionner un ou plusieurs CSV (mode batch) "
        "dans I:\\400-Echange_OT\\03-Rapports\\WPMS"
        "</p>",
        unsafe_allow_html=True
    )

# ============================================================
# MODE
# ============================================================

mode = st.radio(
    "Mode",
    ["Single CSV", "Batch CSV"]
)

# ============================================================
# PRESETS ANGULAIRES
# ============================================================

ppd_options = [
    "PPD101", "PPD102",
    "PPD201", "PPD202",
    "PPD301", "PPD302"
]

presets = {
    "PPD101": {
        "dec_global": 45,
        "CH1": 270, "CH2": 90,
        "CH3": 0, "CH4": 180
    },
    "PPD102": {
        "dec_global": 48,
        "CH1": 0, "CH2": 180,
        "CH3": 90, "CH4": 270
    },
    "PPD201": {
        "dec_global": 345,
        "CH1": 0, "CH2": 180,
        "CH3": 90, "CH4": 270
    },
    "PPD202": {
        "dec_global": 68,
        "CH1": 0, "CH2": 180,
        "CH3": 90, "CH4": 270
    },
    "PPD301": {
        "dec_global": 70,
        "CH1": 270, "CH2": 90,
        "CH3": 0, "CH4": 180
    },
    "PPD302": {
        "dec_global": 165,
        "CH1": 270, "CH2": 90,
        "CH3": 0, "CH4": 180
    },
}

# ============================================================
# TAGS
# ============================================================

tag_names = {
    "PPD101": {
        "CH1": "D1 - 220P10284",
        "CH2": "D2 - 220P10285",
        "CH3": "D3 - 220P10286",
        "CH4": "D4 - 220P10287"
    },
    "PPD102": {
        "CH1": "D1 - 220P10384",
        "CH2": "D2 - 220P10385",
        "CH3": "D3 - 220P10386",
        "CH4": "D4 - 220P10387"
    },
    "PPD201": {
        "CH1": "D1 - 220P20284",
        "CH2": "D2 - 220P20285",
        "CH3": "D3 - 220P20286",
        "CH4": "D4 - 220P20287"
    },
    "PPD202": {
        "CH1": "D1 - 220P20384",
        "CH2": "D2 - 220P20385",
        "CH3": "D3 - 220P20386",
        "CH4": "D4 - 220P20387"
    },
    "PPD301": {
        "CH1": "D1 - 220P30284",
        "CH2": "D2 - 220P30285",
        "CH3": "D3 - 220P30286",
        "CH4": "D4 - 220P30287"
    },
    "PPD302": {
        "CH1": "D1 - 220P30384",
        "CH2": "D2 - 220P30385",
        "CH3": "D3 - 220P30386",
        "CH4": "D4 - 220P30387"
    },
}

CHANNELS = ["CH1", "CH2", "CH3", "CH4"]

# ============================================================
# EXTRACTION NOM + DATE
# ============================================================

def parse_filename_info(filename):

    ppd_match = re.search(r"(PPD\d{3})", filename)

    ppd = (
        ppd_match.group(1)
        if ppd_match
        else "PPD_unknown"
    )

    date_match = re.search(
        r"_(\d{6})-(\d{6})",
        filename
    )

    if date_match:

        date_str, time_str = date_match.groups()

        dt = datetime.strptime(
            date_str + time_str,
            "%y%m%d%H%M%S"
        )

        dt_display = dt.strftime(
            "%d/%m/%y %H:%M:%S"
        )

        dt_file = dt.strftime(
            "%y%m%d_%H%M%S"
        )

    else:
        dt_display = "Date inconnue"
        dt_file = "unknown"

    return ppd, dt_display, dt_file


# ============================================================
# LECTURE CSV
# ============================================================

def process_csv(uploaded_file):

    try:

        content = uploaded_file.getvalue().decode(
            "utf-8",
            errors="ignore"
        )

        lines = content.splitlines()

        start_line = next(
            (
                i for i, line in enumerate(lines)
                if line.startswith("Number,Date,Time")
            ),
            None
        )

        if start_line is None:

            st.warning(
                f"Header introuvable dans {uploaded_file.name}"
            )

            return None, None

        df = pd.read_csv(
            io.StringIO(content),
            skiprows=start_line
        )

        required_columns = [
            "Number", "Date", "Time", "us",
            "CH1", "CH2", "CH3", "CH4", "CH5"
        ]

        missing = [
            col for col in required_columns
            if col not in df.columns
        ]

        if missing:

            st.warning(
                f"Colonnes manquantes dans "
                f"{uploaded_file.name} : {missing}"
            )

            return None, None

        df = df[required_columns].copy()

        df = df[df["Number"] != "NO."]

        for col in CHANNELS + ["CH5"]:

            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(
                    " ", "", regex=False
                ),
                errors="coerce"
            )

        df = df.dropna().reset_index(drop=True)

        return df, uploaded_file.name

    except Exception as e:

        st.warning(
            f"Erreur fichier {uploaded_file.name} : {e}"
        )

        return None, None


# ============================================================
# OFFSETS DE PRESSION
# ============================================================

def pressure_offsets_ui(prefix=""):

    st.sidebar.subheader(
        "Offset pression (bars)"
    )

    st.sidebar.caption(
        "Correction individuelle de chaque voie."
    )

    offsets = {}

    for ch in CHANNELS:

        offsets[ch] = st.sidebar.number_input(
            f"Offset {ch} (bars)",
            min_value=-100.0,
            max_value=100.0,
            value=0.0,
            step=1.0,
            key=f"{prefix}offset_{ch}"
        )

    return offsets


# ============================================================
# CREATION DES GRAPHIQUES
# ============================================================

def create_figure(
    df,
    ppd_selected,
    dec_global,
    dec_ch,
    show_signals,
    uploaded_file_name,
    offset_bars
):

    # --------------------------------------------------------
    # DETECTION DES CYCLES PAR CH5
    # CH5 reste en valeur brute
    # --------------------------------------------------------

    seuil_ch5 = 20

    fronts = (
        (df["CH5"] > seuil_ch5)
        & (df["CH5"].shift(1) <= seuil_ch5)
    )

    indices_fronts = df.index[fronts].tolist()

    if len(indices_fronts) < 2:

        st.warning(
            f"Aucun cycle détecté pour {uploaded_file_name}"
        )

        return None

    # --------------------------------------------------------
    # CONVERSION 4-20 mA -> VOLTS -> BARS
    #
    # Resistance equivalente : 270 ohms
    # 4 mA  = 1.08 V = 0 bar
    # 20 mA = 5.40 V = 100 bars
    #
    # L'offset est applique APRES la conversion.
    # --------------------------------------------------------

    df = df.copy()

    for ch in CHANNELS:

        df[ch] = (
            (df[ch] - 1.08) * 23.148148
            + offset_bars[ch]
        )

    # --------------------------------------------------------
    # EXTRACTION DU CYCLE
    # --------------------------------------------------------

    start = indices_fronts[0]
    end = indices_fronts[1]

    cycle = df.iloc[start:end].reset_index(drop=True)

    n = len(cycle)

    if n < 2:

        st.warning(
            f"Cycle trop court pour {uploaded_file_name}"
        )

        return None

    cycle["Angle"] = np.linspace(
        0, 360, n, endpoint=False
    )

    dec_total = int(
        (dec_global / 360) * n
    ) % n

    # --------------------------------------------------------
    # COULEURS ET LABELS
    # --------------------------------------------------------

    colors = {
        "CH1": "red",
        "CH2": "blue",
        "CH3": "green",
        "CH4": "purple"
    }

    labels = {
        "CH1": "CH D1",
        "CH2": "CH D2",
        "CH3": "CH D3",
        "CH4": "CH D4"
    }

    # --------------------------------------------------------
    # APPLICATION DES DECALAGES ANGULAIRES
    # --------------------------------------------------------

    signals = {}

    for ch, dec in dec_ch.items():

        if show_signals.get(ch, False):

            shift = (
                int((dec / 360) * n)
                + dec_total
            ) % n

            signals[ch] = np.roll(
                cycle[ch].to_numpy(),
                shift
            )

    # --------------------------------------------------------
    # FIGURE
    # --------------------------------------------------------

    fig, axs = plt.subplots(
        3,
        1,
        figsize=(12, 8),
        gridspec_kw={
            "height_ratios": [1, 1, 0.8]
        }
    )

    # --------------------------------------------------------
    # GRAPHIQUE HAUT
    # --------------------------------------------------------

    for ch, sig in signals.items():

        axs[0].plot(
            cycle["Angle"],
            sig,
            label=labels[ch],
            color=colors[ch]
        )

    axs[0].legend()
    axs[0].set_xlim(-10, 390)
    axs[0].set_ylabel("Pression (bars)")
    axs[0].grid(True)

    # --------------------------------------------------------
    # GRAPHIQUE MILIEU : COMPARAISON DES DEMI-CYCLES
    # --------------------------------------------------------

    mid = n // 2

    angles_half = np.linspace(
        0, 180, mid, endpoint=False
    )

    for ch, sig in signals.items():

        comp = sig[:mid]
        decomp = sig[-mid:][::-1]

        axs[1].plot(
            angles_half,
            comp,
            color=colors[ch]
        )

        axs[1].plot(
            angles_half,
            decomp,
            "--",
            color=colors[ch]
        )

    axs[1].set_xlim(-10, 190)
    axs[1].set_xlabel("Angle")
    axs[1].set_ylabel("Pression (bars)")
    axs[1].grid(True)

    # --------------------------------------------------------
    # GRAPHIQUE BAS : TAGS ET STATISTIQUES
    # --------------------------------------------------------

    tags = tag_names.get(
        ppd_selected, {}
    )

    axs[2].axis("off")

    ppd_name, dt_display, _ = parse_filename_info(
        uploaded_file_name
    )

    rpm = 60000 / n

    axs[2].text(
        0.5,
        0.9,
        f"PPD: {ppd_selected} | "
        f"Durée {n} ms | {rpm:.1f} RPM",
        ha="center",
        va="center",
        fontsize=10,
        family="monospace"
    )

    ypos = 0.7

    for ch in CHANNELS:

        sig = signals.get(ch)

        if sig is not None:

            tag = tags.get(ch, ch)

            stats_str = (
                f"{tag} | "
                f"Max:{sig.max():.1f} bars  "
                f"Min:{sig.min():.1f} bars  "
                f"Moy:{sig.mean():.1f} bars  "
                f"Offset:{offset_bars[ch]:+.1f} bars"
            )

            axs[2].text(
                0.5,
                ypos,
                stats_str,
                ha="center",
                va="center",
                fontsize=9,
                color=colors[ch],
                family="monospace"
            )

            ypos -= 0.18

    fig.suptitle(
        f"Pompe: {ppd_name} | Heure: {dt_display}",
        fontsize=16,
        color="#800020"
    )

    fig.tight_layout(
        rect=[0, 0, 1, 0.96]
    )

    return fig


# ============================================================
# MODE SINGLE CSV
# ============================================================

if mode == "Single CSV":

    uploaded_file = st.file_uploader(
        "📂 Charger un fichier CSV",
        type=["csv"]
    )

    if uploaded_file:

        df, filename = process_csv(uploaded_file)

        if df is not None:

            detected_ppd = next(
                (
                    ppd for ppd in ppd_options
                    if filename.startswith(ppd)
                ),
                None
            )

            st.sidebar.header("Réglages WPMS")

            ppd_selected = st.sidebar.selectbox(
                "Sélection PPD",
                ppd_options,
                index=(
                    ppd_options.index(detected_ppd)
                    if detected_ppd
                    else 0
                )
            )

            preset_vals = presets[ppd_selected]

            dec_global = st.sidebar.slider(
                "Décalage global",
                0,
                360,
                preset_vals["dec_global"]
            )

            dec_ch = {
                ch: st.sidebar.slider(
                    f"Décalage angulaire {ch}",
                    0,
                    360,
                    preset_vals[ch],
                    key=f"angle_{ch}"
                )
                for ch in CHANNELS
            }

            st.sidebar.subheader(
                "Affichage des signaux"
            )

            show_signals = {
                ch: st.sidebar.checkbox(
                    ch,
                    True,
                    key=f"show_{ch}"
                )
                for ch in CHANNELS
            }

            # OFFSETS INDEPENDANTS EN BARS
            offset_bars = pressure_offsets_ui(
                prefix="single_"
            )

            st.sidebar.caption(
                "Offset positif : augmente la pression affichée. "
                "Offset négatif : la diminue."
            )

            fig = create_figure(
                df,
                ppd_selected,
                dec_global,
                dec_ch,
                show_signals,
                filename,
                offset_bars
            )

            if fig is not None:

                st.pyplot(fig)

                # Telechargement de la figure seule
                img_buffer = io.BytesIO()

                fig.savefig(
                    img_buffer,
                    format="png",
                    dpi=200,
                    bbox_inches="tight"
                )

                img_buffer.seek(0)

                st.download_button(
                    "Télécharger le graphique PNG",
                    data=img_buffer,
                    file_name=f"{ppd_selected}_WPMS.png",
                    mime="image/png"
                )

                plt.close(fig)


# ============================================================
# MODE BATCH CSV
# ============================================================

else:

    uploaded_files = st.file_uploader(
        "📂 Charger plusieurs CSV",
        type=["csv"],
        accept_multiple_files=True
    )

    st.sidebar.header("Réglages Batch")

    # Les offsets du batch sont egalement reglables.
    # Valeurs initiales : 0 bar pour chaque voie.
    offset_bars = pressure_offsets_ui(
        prefix="batch_"
    )

    if uploaded_files:

        st.info(
            "Traitement batch en cours..."
        )

        figs = []

        for uploaded_file in uploaded_files:

            df, filename = process_csv(
                uploaded_file
            )

            if df is not None:

                detected_ppd = next(
                    (
                        ppd for ppd in ppd_options
                        if filename.startswith(ppd)
                    ),
                    None
                )

                ppd_selected = (
                    detected_ppd
                    if detected_ppd
                    else ppd_options[0]
                )

                preset_vals = presets[ppd_selected]

                dec_global = preset_vals["dec_global"]

                dec_ch = {
                    ch: preset_vals[ch]
                    for ch in CHANNELS
                }

                show_signals = {
                    ch: True
                    for ch in CHANNELS
                }

                fig = create_figure(
                    df,
                    ppd_selected,
                    dec_global,
                    dec_ch,
                    show_signals,
                    filename,
                    offset_bars
                )

                if fig is not None:

                    figs.append(
                        (fig, filename)
                    )

        # ----------------------------------------------------
        # EXPORT PDF BATCH
        # ----------------------------------------------------

        if figs:

            pdf_bytes = io.BytesIO()

            with PdfPages(pdf_bytes) as pdf:

                for fig, filename in figs:

                    pdf.savefig(
                        fig,
                        bbox_inches="tight"
                    )

                    plt.close(fig)

            pdf_bytes.seek(0)

            first_filename = uploaded_files[0].name

            ppd_name, _, dt_file = parse_filename_info(
                first_filename
            )

            pdf_name = (
                f"{ppd_name}_{dt_file}.pdf"
                if dt_file != "unknown"
                else f"{ppd_name}_batch.pdf"
            )

            st.success(
                f"{len(figs)} graphique(s) généré(s)."
            )

            st.download_button(
                "Télécharger PDF batch",
                data=pdf_bytes,
                file_name=pdf_name,
                mime="application/pdf"
            )

        else:

            st.warning(
                "Aucun graphique généré. "
                "Vérifie les fichiers CSV et la détection des cycles CH5."
            )
