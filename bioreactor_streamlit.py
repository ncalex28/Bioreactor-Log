# streamlit_app.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
from datetime import datetime, timedelta

st.title("Bioreactor Process Data Viewer")
st.markdown("Upload multiple bioreactor CSV files to plot process data aligned by experiment day.")

# ---- File Upload Section ----
uploaded_files = st.file_uploader(
    "Upload CSV files (you can select multiple files)",
    type=["csv"],
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"Uploaded {len(uploaded_files)} file(s)")

    # ---- Configuration for each file ----
    st.subheader("Experiment Configuration")
    st.markdown("Configure each experiment's timeline and display name:")

    file_configs = []

    for idx, uploaded_file in enumerate(uploaded_files):
        with st.expander(f"📄 {uploaded_file.name}", expanded=(idx == 0)):
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                alias = st.text_input(
                    "Experiment Alias:",
                    value=uploaded_file.name.replace(".csv", ""),
                    key=f"alias_{idx}"
                )

            with col2:
                day_minus_2_date = st.date_input(
                    "Day -2 Date:",
                    value=datetime(2026, 2, 16),
                    key=f"date_{idx}"
                )

            with col3:
                max_day = st.number_input(
                    "Plot Through Day:",
                    min_value=-2,
                    max_value=30,
                    value=5,
                    step=1,
                    key=f"maxday_{idx}"
                )

            file_configs.append({
                'file': uploaded_file,
                'alias': alias,
                'day_minus_2': day_minus_2_date,
                'max_day': max_day
            })

    # ---- Process each uploaded file with its configuration ----
    all_tidy_data = []

    for config in file_configs:
        uploaded_file = config['file']
        report_id = config['alias']
        day_minus_2_date = config['day_minus_2']
        max_day = config['max_day']

        # Read CSV
        df = pd.read_csv(uploaded_file)

        # ---- Tidy data ----
        tidy_list = []
        for col in df.columns:
            if col.endswith(".1"):
                continue
            value_col = f"{col}.1"
            if value_col in df.columns:
                temp = df[[col, value_col]].dropna()
                temp.columns = ["time", "value"]
                temp["variable"] = col
                temp["time"] = pd.to_datetime(temp["time"], errors='coerce')
                tidy_list.append(temp)

        if tidy_list:
            tidy = pd.concat(tidy_list, ignore_index=True)
            tidy["report_id"] = report_id

            # Calculate experiment day
            day_minus_2_datetime = pd.to_datetime(day_minus_2_date)
            tidy["experiment_day"] = (tidy["time"] - day_minus_2_datetime).dt.total_seconds() / (24 * 3600)

            # Filter by day range for this specific experiment
            tidy = tidy[
                (tidy["experiment_day"] >= -2) &
                (tidy["experiment_day"] <= max_day)
            ]

            all_tidy_data.append(tidy)

    if all_tidy_data:
        # Combine all data
        combined_data = pd.concat(all_tidy_data, ignore_index=True)

        # ---- Variable Selection ----
        st.subheader("Variable Selection")
        all_vars = sorted(combined_data["variable"].unique().tolist())
        default_vars = ['pHPV', 'DOPV(%)', 'pHCO2User(%)', 'MainGasUser(LPM)',
                       'TempPV(C)', 'LevelPV(L)', 'AgPV(RPM)',
                       'DOO2FlowControllerRequestLimited(%)']

        # Only use defaults that exist in the data
        default_vars = [v for v in default_vars if v in all_vars]

        selected_vars = st.multiselect(
            "Select variables to plot:",
            all_vars,
            default=default_vars if default_vars else all_vars[:8]
        )

        if selected_vars:
            plot_df = combined_data[combined_data["variable"].isin(selected_vars)]

            # ---- Create Faceted Plot ----
            st.subheader("Process Data Plots")

            fig = px.line(
                plot_df,
                x="experiment_day",
                y="value",
                color="report_id",
                facet_row="variable",
                height=300 * len(selected_vars),
                labels={"experiment_day": "Experiment Day", "value": "Value", "report_id": "Report"},
                title="Bioreactor Process Data Over Time",
                color_discrete_sequence=px.colors.qualitative.Plotly
            )

            # Update y-axes to be independent
            fig.update_yaxes(matches=None, showticklabels=True)
            fig.update_xaxes(matches="x")

            # Add vertical line at Day 0
            for i in range(len(selected_vars)):
                fig.add_vline(x=0, line_dash="dash", line_color="gray",
                            opacity=0.5, row=i+1, col=1)

            st.plotly_chart(fig, use_container_width=True)

            # ---- Download Section ----
            st.subheader("Download")

            safe_name = f"bioreactor_plot_{datetime.now().strftime('%Y%m%d_%H%M')}"

            html_buffer = io.StringIO()
            fig.write_html(html_buffer, full_html=True)

            st.download_button(
                label="Download Interactive HTML",
                data=html_buffer.getvalue(),
                file_name=f"{safe_name}.html",
                mime="text/html"
            )
        else:
            st.info("Please select at least one variable to plot.")
    else:
        st.warning("No valid data found in the uploaded files.")
else:
    st.info("Please upload CSV files to get started.")