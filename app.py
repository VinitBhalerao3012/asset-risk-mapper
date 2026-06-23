import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from groq import Groq
from fpdf import FPDF
import datetime
import io
import os

# Initialise session state
if 'analyse_asset' not in st.session_state:
    st.session_state['analyse_asset'] = None

if 'generate_zone_report' not in st.session_state:
    st.session_state['generate_zone_report'] = None

# Clean text for PDF
def clean_for_pdf(text):
    replacements = {
        '\u2014': '-',
        '\u2013': '-',
        '\u2018': "'",
        '\u2019': "'",
        '\u201c': '"',
        '\u201d': '"',
        '\u2022': '*',
        '\u2026': '...',
        '\u00e2': '',
        '\u0080': '',
        '\u0099': "'",
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode('latin-1', 'replace').decode('latin-1')

# Page config
st.set_page_config(
    page_title="AI Asset Risk Mapper",
    page_icon="🗺️",
    layout="wide"
)

# Load data functions
@st.cache_data
def load_default_data():
    return pd.read_csv('assets.csv')

@st.cache_data
def load_uploaded_data(file):
    return pd.read_csv(file)

def calculate_risk(df):
    if 'risk_score' not in df.columns:
        df['risk_score'] = (
            (df['age_years'] / 80 * 40) +
            (df['last_inspection_years_ago'] / 10 * 30) +
            ((10 - df['condition_score']) / 10 * 30)
        ).round(2)
    if 'risk_category' not in df.columns:
        def categorise_risk(score):
            if score >= 60:
                return 'High'
            elif score >= 35:
                return 'Medium'
            else:
                return 'Low'
        df['risk_category'] = df['risk_score'].apply(categorise_risk)
    return df

# Header
st.title("AI-Powered Water Infrastructure Risk Mapper")
st.markdown("**Severn Trent Style Asset Intelligence Tool** - Spatial risk analysis powered by GIS and Groq/Llama 3.3 AI")
st.divider()

# Main tabs
tab1, tab2 = st.tabs(["📊 Risk Dashboard", "🗺️ QGIS Integration"])

with tab1:

    # Data source selection
    st.subheader("Data Source")
    data_mode = st.radio(
        "Choose data source:",
        ["Use default dataset (200 Midlands assets)", "Upload your own asset CSV"],
        horizontal=True
    )

    if data_mode == "Upload your own asset CSV":
        uploaded_file = st.file_uploader(
            "Upload Asset Register CSV",
            type=['csv'],
            help="CSV must contain: asset_id, asset_type, latitude, longitude, age_years, last_inspection_years_ago, condition_score, zone"
        )
        if uploaded_file:
            df = load_uploaded_data(uploaded_file)
            df = calculate_risk(df)
            st.success(f"Uploaded successfully - {len(df)} assets loaded!")
        else:
            st.info("Upload a CSV file above, or switch to the default dataset.")
            st.stop()
    else:
        df = load_default_data()
        st.success(f"Default dataset loaded - {len(df)} assets across Severn Trent Midlands service area.")

    # Download sample CSV template
    sample_df = pd.DataFrame({
        'asset_id': ['ST-0001', 'ST-0002'],
        'asset_type': ['Water Pipe', 'Pumping Station'],
        'latitude': [52.4, 52.5],
        'longitude': [-1.5, -1.6],
        'age_years': [45, 30],
        'last_inspection_years_ago': [3, 1],
        'condition_score': [4, 7],
        'material': ['Cast Iron', 'Steel'],
        'zone': ['North', 'South']
    })
    st.download_button(
        label="Download Sample CSV Template",
        data=sample_df.to_csv(index=False),
        file_name="asset_template.csv",
        mime="text/csv"
    )

    st.divider()

    # Sidebar filters
    st.sidebar.header("Filter Assets")
    selected_zone = st.sidebar.multiselect(
        "Zone",
        options=df['zone'].unique(),
        default=df['zone'].unique()
    )
    selected_type = st.sidebar.multiselect(
        "Asset Type",
        options=df['asset_type'].unique(),
        default=df['asset_type'].unique()
    )
    selected_risk = st.sidebar.multiselect(
        "Risk Category",
        options=['High', 'Medium', 'Low'],
        default=['High', 'Medium', 'Low']
    )

    # Filter dataframe
    filtered_df = df[
        (df['zone'].isin(selected_zone)) &
        (df['asset_type'].isin(selected_type)) &
        (df['risk_category'].isin(selected_risk))
    ]

    # KPI metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Assets", len(filtered_df))
    with col2:
        high = len(filtered_df[filtered_df['risk_category'] == 'High'])
        st.metric("High Risk", high)
    with col3:
        med = len(filtered_df[filtered_df['risk_category'] == 'Medium'])
        st.metric("Medium Risk", med)
    with col4:
        low = len(filtered_df[filtered_df['risk_category'] == 'Low'])
        st.metric("Low Risk", low)

    st.divider()

    # Map and charts
    col_map, col_charts = st.columns([3, 2])

    with col_map:
        st.subheader("Asset Risk Map")
        m = folium.Map(
            location=[filtered_df['latitude'].mean(), filtered_df['longitude'].mean()],
            zoom_start=9,
            tiles='OpenStreetMap'
        )
        colour_map = {'High': 'red', 'Medium': 'orange', 'Low': 'green'}
        for _, row in filtered_df.iterrows():
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=6,
                color=colour_map[row['risk_category']],
                fill=True,
                fill_opacity=0.8,
                popup=folium.Popup(
                    f"<b>{row['asset_id']}</b><br>Type: {row['asset_type']}<br>Zone: {row['zone']}<br>Age: {row['age_years']} years<br>Condition: {row['condition_score']}/10<br>Risk: {row['risk_category']}<br>Risk Score: {row['risk_score']}",
                    max_width=200
                )
            ).add_to(m)
        st_folium(m, width=700, height=450)

    with col_charts:
        st.subheader("Risk Distribution")
        risk_counts = filtered_df['risk_category'].value_counts().reset_index()
        risk_counts.columns = ['Risk Category', 'Count']
        fig1 = px.pie(
            risk_counts,
            values='Count',
            names='Risk Category',
            color='Risk Category',
            color_discrete_map={'High': '#FF4B4B', 'Medium': '#FFA500', 'Low': '#00CC44'},
            hole=0.4
        )
        st.plotly_chart(fig1, use_container_width=True)

        st.subheader("Risk by Zone")
        zone_risk = filtered_df.groupby(['zone', 'risk_category']).size().reset_index(name='count')
        fig2 = px.bar(
            zone_risk,
            x='zone',
            y='count',
            color='risk_category',
            color_discrete_map={'High': '#FF4B4B', 'Medium': '#FFA500', 'Low': '#00CC44'},
            barmode='stack'
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # Asset Register
    st.subheader("Asset Register")
    st.dataframe(
        filtered_df.sort_values('risk_score', ascending=False),
        use_container_width=True,
        height=300
    )

    st.divider()

    # ============================================================
    # SECTION 1 - AI ZONE RISK ANALYSIS
    # ============================================================
    st.subheader("AI Risk Analysis - Powered by Groq/Llama 3.3")
    st.markdown("Generate a plain-English risk assessment for stakeholders and decision-makers.")

    selected_zone_ai = st.selectbox(
        "Select Zone for AI Analysis:",
        options=df['zone'].unique()
    )

    if st.button("Generate AI Risk Report", type="primary"):
        st.session_state['generate_zone_report'] = selected_zone_ai

    if st.session_state.get('generate_zone_report'):
        selected_zone_ai = st.session_state['generate_zone_report']
        zone_data = df[df['zone'] == selected_zone_ai]
        high_count = len(zone_data[zone_data['risk_category'] == 'High'])
        med_count = len(zone_data[zone_data['risk_category'] == 'Medium'])
        low_count = len(zone_data[zone_data['risk_category'] == 'Low'])
        avg_age = zone_data['age_years'].mean().round(1)
        avg_condition = zone_data['condition_score'].mean().round(1)
        avg_risk = zone_data['risk_score'].mean().round(1)
        oldest = zone_data['age_years'].max()
        most_common_type = zone_data['asset_type'].value_counts().index[0]

        prompt = f"""
        You are an Asset Intelligence Analyst for a UK water utility company similar to Severn Trent.
        Analyse the following asset data for the {selected_zone_ai} zone and write a clear,
        professional risk assessment report for senior stakeholders and decision-makers.
        The report should be in plain English with no special characters like dashes or smart quotes.

        Zone: {selected_zone_ai}
        Total Assets: {len(zone_data)}
        High Risk Assets: {high_count}
        Medium Risk Assets: {med_count}
        Low Risk Assets: {low_count}
        Average Asset Age: {avg_age} years
        Oldest Asset: {oldest} years
        Average Condition Score: {avg_condition}/10
        Average Risk Score: {avg_risk}/100
        Most Common Asset Type: {most_common_type}

        Write a 3-paragraph report covering:
        1. Overall risk summary for this zone
        2. Key concerns and priority assets requiring attention
        3. Recommended actions for the asset management team

        Keep it professional, clear, and actionable. Use only standard ASCII characters.
        """

        with st.spinner("Generating AI risk assessment..."):
            try:
                client = Groq(api_key=st.secrets["GROQ_API_KEY"])
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=600
                )
                ai_report = response.choices[0].message.content
                st.success("AI Risk Report Generated")
                st.markdown("---")
                st.markdown(ai_report)
                st.markdown("---")

                # Generate PDF
                class PDFReport(FPDF):
                    def header(self):
                        self.set_font('Helvetica', 'B', 16)
                        self.set_text_color(0, 102, 204)
                        self.cell(0, 10, 'AI-Powered Water Infrastructure Risk Report', align='C', new_x='LMARGIN', new_y='NEXT')
                        self.set_font('Helvetica', '', 10)
                        self.set_text_color(100, 100, 100)
                        self.cell(0, 6, clean_for_pdf(f'Generated: {datetime.datetime.now().strftime("%d %B %Y %H:%M")}'), align='C', new_x='LMARGIN', new_y='NEXT')
                        self.ln(4)
                        self.set_draw_color(0, 102, 204)
                        self.set_line_width(0.5)
                        self.line(10, self.get_y(), 200, self.get_y())
                        self.ln(4)

                    def footer(self):
                        self.set_y(-15)
                        self.set_font('Helvetica', 'I', 8)
                        self.set_text_color(150, 150, 150)
                        self.cell(0, 10, f'AI-Powered Water Infrastructure Risk Mapper | Page {self.page_no()}', align='C')

                pdf = PDFReport()
                pdf.add_page()

                # Zone summary section
                pdf.set_font('Helvetica', 'B', 13)
                pdf.set_text_color(0, 102, 204)
                pdf.cell(0, 10, clean_for_pdf(f'Zone Risk Summary: {selected_zone_ai}'), new_x='LMARGIN', new_y='NEXT')
                pdf.ln(2)

                # Summary metrics table
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_fill_color(0, 102, 204)
                pdf.set_text_color(255, 255, 255)
                col_w = [60, 60, 60]
                pdf.cell(col_w[0], 8, 'Metric', border=1, fill=True)
                pdf.cell(col_w[1], 8, 'Value', border=1, fill=True)
                pdf.cell(col_w[2], 8, 'Status', border=1, fill=True, new_x='LMARGIN', new_y='NEXT')

                metrics = [
                    ('Total Assets', str(len(zone_data)), 'Monitored'),
                    ('High Risk Assets', str(high_count), 'Immediate Attention'),
                    ('Medium Risk Assets', str(med_count), 'Monitor Closely'),
                    ('Low Risk Assets', str(low_count), 'Routine Maintenance'),
                    ('Average Asset Age', f'{avg_age} years', 'Infrastructure Age'),
                    ('Average Condition Score', f'{avg_condition}/10', 'Condition Rating'),
                    ('Average Risk Score', f'{avg_risk}/100', 'Overall Risk Level'),
                    ('Most Common Asset Type', clean_for_pdf(most_common_type), 'Primary Asset'),
                ]

                pdf.set_font('Helvetica', '', 9)
                for i, (metric, value, status) in enumerate(metrics):
                    if i % 2 == 0:
                        pdf.set_fill_color(240, 245, 255)
                    else:
                        pdf.set_fill_color(255, 255, 255)
                    pdf.set_text_color(0, 0, 0)
                    pdf.cell(col_w[0], 7, clean_for_pdf(metric), border=1, fill=True)
                    pdf.cell(col_w[1], 7, clean_for_pdf(value), border=1, fill=True)
                    pdf.cell(col_w[2], 7, clean_for_pdf(status), border=1, fill=True, new_x='LMARGIN', new_y='NEXT')

                pdf.ln(6)

                # Charts section
                import matplotlib
                matplotlib.use('Agg')
                import matplotlib.pyplot as plt
                import tempfile

                # Chart 1 - Risk Distribution Pie Chart
                fig1, ax1 = plt.subplots(figsize=(6, 4))
                risk_labels = ['High Risk', 'Medium Risk', 'Low Risk']
                risk_values = [high_count, med_count, low_count]
                risk_colors = ['#FF4B4B', '#FFA500', '#00CC44']
                wedges, texts, autotexts = ax1.pie(
                    risk_values,
                    labels=risk_labels,
                    colors=risk_colors,
                    autopct='%1.1f%%',
                    startangle=90,
                    textprops={'fontsize': 11}
                )
                ax1.set_title(f'Risk Distribution - {selected_zone_ai} Zone', fontsize=13, fontweight='bold', color='#0066CC')
                plt.tight_layout()
                chart1_path = tempfile.mktemp(suffix='.png')
                plt.savefig(chart1_path, dpi=150, bbox_inches='tight', facecolor='white')
                plt.close()

                # Chart 2 - Asset Type Bar Chart
                fig2, ax2 = plt.subplots(figsize=(6, 4))
                type_counts = zone_data['asset_type'].value_counts()
                bars = ax2.bar(
                    type_counts.index,
                    type_counts.values,
                    color=['#FF4B4B' if v == type_counts.max() else '#0066CC' for v in type_counts.values]
                )
                ax2.set_title(f'Asset Types - {selected_zone_ai} Zone', fontsize=13, fontweight='bold', color='#0066CC')
                ax2.set_xlabel('Asset Type', fontsize=10)
                ax2.set_ylabel('Count', fontsize=10)
                plt.xticks(rotation=30, ha='right', fontsize=9)
                for bar, val in zip(bars, type_counts.values):
                    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, str(val), ha='center', va='bottom', fontsize=9)
                plt.tight_layout()
                chart2_path = tempfile.mktemp(suffix='.png')
                plt.savefig(chart2_path, dpi=150, bbox_inches='tight', facecolor='white')
                plt.close()

                # Chart 3 - Age Distribution Histogram
                fig3, ax3 = plt.subplots(figsize=(6, 4))
                ax3.hist(
                    zone_data['age_years'],
                    bins=10,
                    color='#0066CC',
                    edgecolor='white',
                    alpha=0.85
                )
                ax3.set_title(f'Asset Age Distribution - {selected_zone_ai} Zone', fontsize=13, fontweight='bold', color='#0066CC')
                ax3.set_xlabel('Age (Years)', fontsize=10)
                ax3.set_ylabel('Number of Assets', fontsize=10)
                plt.tight_layout()
                chart3_path = tempfile.mktemp(suffix='.png')
                plt.savefig(chart3_path, dpi=150, bbox_inches='tight', facecolor='white')
                plt.close()

                # Add charts page to PDF
                pdf.add_page()
                pdf.set_font('Helvetica', 'B', 13)
                pdf.set_text_color(0, 102, 204)
                pdf.cell(0, 10, clean_for_pdf(f'Zone Analytics - {selected_zone_ai}'), new_x='LMARGIN', new_y='NEXT')
                pdf.set_draw_color(0, 102, 204)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(4)

                # Add pie chart and bar chart side by side
                chart_y = pdf.get_y()
                pdf.image(chart1_path, x=10, y=chart_y, w=92)
                pdf.image(chart2_path, x=107, y=chart_y, w=92)
                pdf.ln(85)

                # Add age histogram full width
                pdf.image(chart3_path, x=20, y=pdf.get_y(), w=170)
                pdf.ln(95)

                # Add QGIS map if available
                qgis_map_path = "qgis_asset_map.png"
                if os.path.exists(qgis_map_path):
                    pdf.add_page()
                    pdf.set_font('Helvetica', 'B', 13)
                    pdf.set_text_color(0, 102, 204)
                    pdf.cell(0, 10, 'QGIS Spatial Analysis Map - Water Infrastructure Assets', new_x='LMARGIN', new_y='NEXT')
                    pdf.set_draw_color(0, 102, 204)
                    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                    pdf.ln(4)
                    pdf.set_font('Helvetica', '', 9)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(0, 6, 'Generated using QGIS - 200 assets plotted across Severn Trent Midlands service area', new_x='LMARGIN', new_y='NEXT')
                    pdf.cell(0, 6, 'Red = High Risk | Orange = Medium Risk | Green = Low Risk', new_x='LMARGIN', new_y='NEXT')
                    pdf.ln(4)
                    pdf.image(qgis_map_path, x=10, y=pdf.get_y(), w=190)
                    pdf.ln(120)

                # Clean up temp files
                os.remove(chart1_path)
                os.remove(chart2_path)
                os.remove(chart3_path)

                # AI Report section
                pdf.add_page()
                pdf.set_font('Helvetica', 'B', 13)
                pdf.set_text_color(0, 102, 204)
                pdf.cell(0, 10, 'AI Risk Assessment', new_x='LMARGIN', new_y='NEXT')
                pdf.set_draw_color(0, 102, 204)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(4)

                pdf.set_font('Helvetica', '', 10)
                pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(0, 6, clean_for_pdf(ai_report))
                pdf.ln(4)

                # High risk assets table
                pdf.add_page()
                pdf.set_font('Helvetica', 'B', 13)
                pdf.set_text_color(0, 102, 204)
                pdf.cell(0, 10, clean_for_pdf(f'High Risk Asset Register - {selected_zone_ai} Zone'), new_x='LMARGIN', new_y='NEXT')
                pdf.ln(2)

                high_risk_assets = zone_data[zone_data['risk_category'] == 'High'].sort_values('risk_score', ascending=False)

                if len(high_risk_assets) > 0:
                    pdf.set_font('Helvetica', 'B', 8)
                    pdf.set_fill_color(0, 102, 204)
                    pdf.set_text_color(255, 255, 255)
                    headers = ['Asset ID', 'Type', 'Age', 'Condition', 'Risk Score', 'Material']
                    widths = [25, 35, 20, 25, 25, 30]
                    for h, w in zip(headers, widths):
                        pdf.cell(w, 7, h, border=1, fill=True)
                    pdf.ln()

                    pdf.set_font('Helvetica', '', 8)
                    for i, (_, row) in enumerate(high_risk_assets.iterrows()):
                        if i % 2 == 0:
                            pdf.set_fill_color(255, 235, 235)
                        else:
                            pdf.set_fill_color(255, 255, 255)
                        pdf.set_text_color(0, 0, 0)
                        pdf.cell(25, 6, clean_for_pdf(str(row['asset_id'])), border=1, fill=True)
                        pdf.cell(35, 6, clean_for_pdf(str(row['asset_type'])), border=1, fill=True)
                        pdf.cell(20, 6, f"{row['age_years']}y", border=1, fill=True)
                        pdf.cell(25, 6, f"{row['condition_score']}/10", border=1, fill=True)
                        pdf.cell(25, 6, str(row['risk_score']), border=1, fill=True)
                        pdf.cell(30, 6, clean_for_pdf(str(row['material'])), border=1, fill=True)
                        pdf.ln()
                else:
                    pdf.set_font('Helvetica', '', 10)
                    pdf.set_text_color(0, 0, 0)
                    pdf.cell(0, 8, 'No high risk assets in this zone.', new_x='LMARGIN', new_y='NEXT')

                # Footer note
                pdf.ln(6)
                pdf.set_font('Helvetica', 'I', 9)
                pdf.set_text_color(100, 100, 100)
                pdf.multi_cell(0, 5, 'This report was generated by the AI-Powered Water Infrastructure Risk Mapper using Groq/Llama 3.3 AI. All risk scores are calculated based on asset age, inspection history, and condition data. This report is intended to support - not replace - professional engineering assessment.')

                # Output PDF
                pdf_bytes = bytes(pdf.output())

                st.download_button(
                    label="Download Full PDF Report",
                    data=pdf_bytes,
                    file_name=f"risk_report_{selected_zone_ai}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"Error generating report: {e}")

    st.divider()

    # ============================================================
    # SECTION 2 - INDIVIDUAL ASSET AI DRILL-DOWN
    # ============================================================
    st.subheader("Individual Asset AI Drill-Down")
    st.markdown("Select any single asset for a detailed AI-powered inspection report.")

    col_select, col_filter = st.columns([2, 2])

    with col_select:
        selected_asset_id = st.selectbox(
            "Select Asset ID:",
            options=filtered_df.sort_values('risk_score', ascending=False)['asset_id'].tolist(),
            help="Assets sorted by highest risk first"
        )

    with col_filter:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Analyse This Asset", type="primary"):
            st.session_state['analyse_asset'] = selected_asset_id

    if st.session_state.get('analyse_asset'):
        selected_asset_id = st.session_state['analyse_asset']
        asset = df[df['asset_id'] == selected_asset_id].iloc[0]

        st.markdown("---")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Asset Type", asset['asset_type'])
        with col2:
            st.metric("Zone", asset['zone'])
        with col3:
            st.metric("Age", f"{asset['age_years']} years")
        with col4:
            st.metric("Condition", f"{asset['condition_score']}/10")
        with col5:
            st.metric("Risk", asset['risk_category'])

        col_mini_map, col_ai = st.columns([1, 2])

        with col_mini_map:
            st.markdown("**Asset Location**")
            mini_map = folium.Map(
                location=[asset['latitude'], asset['longitude']],
                zoom_start=13,
                tiles='OpenStreetMap'
            )
            colour_map = {'High': 'red', 'Medium': 'orange', 'Low': 'green'}
            folium.Marker(
                location=[asset['latitude'], asset['longitude']],
                popup=folium.Popup(
                    f"<b>{asset['asset_id']}</b><br>{asset['asset_type']}<br>Risk: {asset['risk_category']}",
                    max_width=150
                ),
                icon=folium.Icon(
                    color=colour_map[asset['risk_category']],
                    icon='info-sign'
                )
            ).add_to(mini_map)
            st_folium(mini_map, width=350, height=300)

        with col_ai:
            st.markdown("**AI Asset Inspection Report**")

            if asset['last_inspection_years_ago'] >= 7:
                inspection_status = "OVERDUE - not inspected in over 7 years"
            elif asset['last_inspection_years_ago'] >= 4:
                inspection_status = f"Due soon - last inspected {asset['last_inspection_years_ago']} years ago"
            else:
                inspection_status = f"Recently inspected - {asset['last_inspection_years_ago']} years ago"

            asset_prompt = f"""
            You are a senior Asset Engineer at a UK water utility company similar to Severn Trent.

            Write a concise, professional inspection report for the following individual asset.
            Keep it in plain English suitable for both technical and non-technical stakeholders.
            Use only standard ASCII characters - no dashes, smart quotes, or special characters.

            Asset ID: {asset['asset_id']}
            Asset Type: {asset['asset_type']}
            Zone: {asset['zone']}
            Age: {asset['age_years']} years old
            Material: {asset['material']}
            Condition Score: {asset['condition_score']} out of 10
            Last Inspection: {inspection_status}
            Risk Score: {asset['risk_score']} out of 100
            Risk Category: {asset['risk_category']}
            Area Deprivation Score: {asset['area_deprivation_score']}

            Write a 3-paragraph report covering:
            1. Current condition and risk assessment for this specific asset
            2. Key risk factors driving the risk score
            3. Specific recommended actions with urgency level (Immediate / Within 3 months / Within 12 months)

            Be specific to this asset type - a valve needs different maintenance to a reservoir.
            """

            with st.spinner(f"Analysing asset {selected_asset_id}..."):
                try:
                    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": asset_prompt}],
                        max_tokens=500
                    )
                    asset_report = response.choices[0].message.content
                    st.markdown(asset_report)

                    st.download_button(
                        label=f"Download Report for {selected_asset_id}",
                        data=f"ASSET INSPECTION REPORT\n\nAsset ID: {asset['asset_id']}\nType: {asset['asset_type']}\nZone: {asset['zone']}\nRisk: {asset['risk_category']}\n\n{asset_report}",
                        file_name=f"inspection_{selected_asset_id}.txt",
                        mime="text/plain"
                    )

                except Exception as e:
                    st.error(f"Error generating report: {e}")

# ============================================================
# TAB 2 - QGIS INTEGRATION
# ============================================================
with tab2:
    st.subheader("QGIS Spatial Analysis Integration")
    st.markdown("This tab demonstrates how professional GIS software (QGIS) integrates with AI-powered asset analytics.")

    st.divider()

    col_info, col_steps = st.columns([1, 1])

    with col_info:
        st.markdown("### What is QGIS?")
        st.markdown("""
        **QGIS** is a professional open-source Geographic Information System used by:
        - Water utility companies like Severn Trent
        - Local authorities and government
        - Infrastructure asset managers
        - Environmental agencies

        It allows analysts to:
        - Visualise assets geographically
        - Perform spatial overlay analysis
        - Apply buffer analysis around assets
        - Produce professional cartographic maps
        - Export data in multiple GIS formats
        """)

    with col_steps:
        st.markdown("### QGIS Workflow for Asset Mapping")
        st.markdown("""
        **Step 1:** Load asset register CSV as point layer

        **Step 2:** Set coordinate reference system (EPSG:4326 WGS84)

        **Step 3:** Apply categorised symbology by risk category:
        - High Risk = Red
        - Medium Risk = Orange
        - Low Risk = Green

        **Step 4:** Add OpenStreetMap background layer

        **Step 5:** Export map as PNG for reporting

        **Step 6:** Embed in AI-powered PDF report automatically
        """)

    st.divider()

    # QGIS Map section
    st.subheader("QGIS Exported Asset Risk Map")

    default_qgis_map = "qgis_asset_map.png"

    col_map, col_upload = st.columns([3, 1])

    with col_upload:
        st.markdown("**Upload QGIS Map**")
        uploaded_qgis = st.file_uploader(
            "Upload your QGIS exported map",
            type=['png', 'jpg', 'jpeg'],
            help="Export from QGIS: Project > Export Map to Image"
        )

        if uploaded_qgis:
            with open("qgis_asset_map.png", "wb") as f:
                f.write(uploaded_qgis.getbuffer())
            st.success("QGIS map uploaded successfully!")

        st.markdown("**QGIS Export Instructions:**")
        st.markdown("""
        1. Open QGIS
        2. Load assets.csv as point layer
        3. Style by risk_category column
        4. Add OSM background
        5. Project > Export Map to Image
        6. Save as qgis_asset_map.png
        7. Upload here
        """)

    with col_map:
        if os.path.exists(default_qgis_map):
            st.image(
                default_qgis_map,
                caption="QGIS Asset Risk Map - 200 Water Infrastructure Assets across the Midlands (Severn Trent Service Area). Red = High Risk | Orange = Medium Risk | Green = Low Risk",
                use_container_width=True
            )
            st.success("QGIS map loaded - 200 assets plotted across Birmingham, Coventry and the Midlands")
        else:
            st.info("Upload your QGIS exported map using the panel on the right")

    st.divider()

    # Spatial Analysis Techniques
    st.subheader("Spatial Analysis Techniques Used")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Spatial Overlay Analysis**")
        st.markdown("""
        Layering multiple geographic datasets to identify spatial relationships between asset locations, risk scores, and area deprivation indices.
        """)

    with col2:
        st.markdown("**Buffer Analysis**")
        st.markdown("""
        Creating zones around high-risk assets to identify clusters and assess spillover effects on neighbouring infrastructure.
        """)

    with col3:
        st.markdown("**Graduated Symbology**")
        st.markdown("""
        Visualising risk scores using colour gradients - red for high risk, orange for medium, green for low - enabling instant spatial pattern recognition.
        """)

    st.divider()

    # QGIS + AI connection
    st.subheader("How QGIS + AI Work Together")
    st.markdown("""
    This tool combines the **spatial intelligence of QGIS** with the **analytical power of Groq/Llama 3.3 AI**:

    | QGIS Contribution | AI Contribution |
    |---|---|
    | Geographic asset plotting | Plain-English risk narratives |
    | Spatial pattern identification | Stakeholder-ready recommendations |
    | Professional cartographic maps | Executive summary generation |
    | Buffer and overlay analysis | Individual asset inspection reports |
    | Multi-format data export | Automated PDF report creation |

    Together they replicate the full **Asset Intelligence workflow** used by water utility companies like Severn Trent.
    """)