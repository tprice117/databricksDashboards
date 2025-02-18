import os
from databricks import sql
from databricks.sdk.core import Config
import streamlit as st
import pandas as pd
# --uncomment to run locally
from dotenv import load_dotenv 
from datetime import datetime, timedelta
from streamlit_date_picker import date_range_picker, date_picker, PickerType
from pyspark import SparkConf, SparkContext
from pyspark.sql import SQLContext
import altair as alt
import decimal
from streamlit_echarts import st_echarts

load_dotenv(dotenv_path='.databricks/.databricks.env') 
# uncomment to run locally

# Ensure environment variable is set correctly (running locally)
warehouse_id = os.getenv('DATABRICKS_WAREHOUSE_ID')
print(f"DATABRICKS_WAREHOUSE_ID: {warehouse_id}")
# assert warehouse_id, "DATABRICKS_WAREHOUSE_ID must be set in app.yaml."

# Ensure environment variable is set correctly (run in databricks)
assert os.getenv('DATABRICKS_WAREHOUSE_ID'), "DATABRICKS_WAREHOUSE_ID must be set in app.yaml."

def read_sql_file(filepath: str)-> str:
    with open(filepath, 'r') as file:
        return file.read()
    
def sqlQuery(query: str) -> pd.DataFrame:
    cfg = Config() # Pull environment variables for auth
    with sql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{os.getenv('DATABRICKS_WAREHOUSE_ID')}",
        credentials_provider=lambda: cfg.authenticate
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall_arrow().to_pandas()

st.set_page_config(layout="wide")

@st.cache_data(ttl=30)  # only re-query if it's been 30 seconds
def getData():
    #return sqlQuery("SELECT * FROM nyctaxi.taxi_parquet LIMIT 1000")
    query=read_sql_file("sql_queries/orderlineproducts.sql")
    return sqlQuery(query)

cli = getData()

st.header("Sales Performance Dashboard")

# Function to detect dark mode
def is_dark_mode():
    return st.get_option("theme.base") == "dark"

# Load custom CSS from file
with open('css/style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Determine text color based on theme
text_color = "white" if is_dark_mode() else "black"

# Extract distinct values of mainproductcategory
distinct_categories = ['All Categories'] + cli['main_product_category'].dropna().unique().tolist()

# Add a selectbox for mainproductcategory
selected_category = st.selectbox("Select Main Product Category", options=distinct_categories)

# Filter data based on the selected category
if selected_category == 'All Categories':
    filtered_data = cli
else:
    filtered_data = cli[cli['main_product_category'] == selected_category].copy()

# Ensure 'order_line_total', 'supplier_amount', 'orderline_rate', 'orderline_quantity', and 'orderline_platform_fee_percent' are numeric
filtered_data.loc[:, 'order_line_total'] = pd.to_numeric(filtered_data['order_line_total'], errors='coerce')
if 'supplier_amount' in filtered_data.columns:
    filtered_data.loc[:, 'supplier_amount'] = pd.to_numeric(filtered_data['supplier_amount'], errors='coerce')
filtered_data.loc[:, 'orderline_rate'] = pd.to_numeric(filtered_data['orderline_rate'], errors='coerce')
filtered_data.loc[:, 'orderline_quantity'] = pd.to_numeric(filtered_data['orderline_quantity'], errors='coerce')
filtered_data.loc[:, 'orderline_platform_fee_percent'] = pd.to_numeric(filtered_data['orderline_platform_fee_percent'], errors='coerce')

# Ensure 'order_end_date' is datetime
filtered_data.loc[:, 'order_end_date'] = pd.to_datetime(filtered_data['order_end_date'], errors='coerce')

##METRICS START HERE

# Calculate GMV (Customer Amount Complete)
gmv = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE'].apply(
    lambda row: float(row['orderline_rate']) * float(row['orderline_quantity']) * (1 + float(row['orderline_platform_fee_percent']) * 0.01), axis=1
).sum()

# Calculate the sum of total_line_amount
total_line_amount_sum = filtered_data['order_line_total'].sum()

# Count the distinct order_id values
distinct_order_count = filtered_data['order_id'].nunique()

#Calculate Average Order Value
average_order_value = filtered_data.groupby('order_id').apply(
    lambda x: (x['orderline_rate'] * x['orderline_quantity'] * (1 + x['orderline_platform_fee_percent'] * 0.01)).sum()
).mean()

#Calculate Take Rate
customer_amount = filtered_data['order_line_total'].sum()
supplier_amount = filtered_data['supplier_amount'].sum() if 'supplier_amount' in filtered_data.columns else 0
take_rate = float((customer_amount - supplier_amount) / customer_amount) if customer_amount != 0 else 0

#Net Revenue Complete: 
# Calculate Net Revenue Complete
customer_amount_complete = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE', 'order_line_total'].sum()
supplier_amount_complete = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE', 'supplier_amount'].sum() if 'supplier_amount' in filtered_data.columns else 0
net_revenue_complete = customer_amount_complete - supplier_amount_complete
##METRICS END HERE

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    st.markdown("Select Date Range")
    default_start, default_end = datetime.now() - timedelta(days=1), datetime.now()
        
    date_range_string = date_range_picker(picker_type=PickerType.date,
                                        start=default_start, end=default_end,
                                        key='date_range_picker')

    if date_range_string:
        start, end = date_range_string
        filtered_data = filtered_data[(filtered_data['order_end_date'] >= pd.to_datetime(start)) & (filtered_data['order_end_date'] <= pd.to_datetime(end))]
    
    # Create a card for Order Count
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title" style="color: {text_color};">Total Order Count</div>
            <div class="card-amount" style="color: {text_color};">{filtered_data['order_id'].nunique()}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    # Create a card for Total Line Amount
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title" style="color: {text_color};">Total Line Amount</div>
            <div class="card-amount" style="color: {text_color};">${total_line_amount_sum:,.2f}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Create a card for Distinct Order Count
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title" style="color: {text_color};">Distinct Order Count</div>
            <div class="card-amount" style="color: {text_color};">{distinct_order_count}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


with col2:
    # Create a card for Total GMV
    # Calculate GMV for the filtered data
    filtered_data.loc[:, 'orderline_rate'] = pd.to_numeric(filtered_data['orderline_rate'], errors='coerce')
    filtered_data.loc[:, 'orderline_quantity'] = pd.to_numeric(filtered_data['orderline_quantity'], errors='coerce')
    filtered_data.loc[:, 'orderline_platform_fee_percent'] = pd.to_numeric(filtered_data['orderline_platform_fee_percent'], errors='coerce')
    
    gmv_filtered = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE'].apply(
        lambda row: float(row['orderline_rate']) * float(row['orderline_quantity']) * (1 + float(row['orderline_platform_fee_percent']) * 0.01), axis=1
    ).sum()

    st.markdown(
        f"""
        <div class="card">
            <div class="card-title" style="color: {text_color};">Total GMV</div>
            <div class="card-amount" style="color: {text_color};">${gmv_filtered:,.2f}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Create a card for Total Revenue
    # Calculate Net Revenue Complete for the filtered data
    customer_amount_complete_filtered = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE', 'order_line_total'].sum()
    supplier_amount_complete_filtered = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE', 'supplier_amount'].sum() if 'supplier_amount' in filtered_data.columns else 0
    net_revenue_complete_filtered = customer_amount_complete_filtered - supplier_amount_complete_filtered

    st.markdown(
        f"""
        <div class="card">
            <div class="card-title" style="color: {text_color};">Total Revenue</div>
            <div class="card-amount" style="color: {text_color};">${net_revenue_complete_filtered:,.2f}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Calculate Take Rate for the filtered data
    customer_amount_filtered = filtered_data['order_line_total'].sum()
    supplier_amount_filtered = filtered_data['supplier_amount'].sum() if 'supplier_amount' in filtered_data.columns else 0
    take_rate_filtered = float((customer_amount_filtered - supplier_amount_filtered) / customer_amount_filtered) if customer_amount_filtered != 0 else 0

    # Create a card for Take Rate
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title" style="color: {text_color};">Take Rate</div>
            <div class="card-amount" style="color: {text_color};">{take_rate_filtered:.2%}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Create a card for Average Order Value
    average_order_value = filtered_data['order_line_total'].sum() / filtered_data['order_id'].nunique() if filtered_data['order_id'].nunique() != 0 else 0
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title" style="color: {text_color};">Average Order Value</div>
            <div class="card-amount" style="color: {text_color};">${"{:,.2f}".format(average_order_value)}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:
    # Create a combo chart using Altair
    base = alt.Chart(filtered_data).encode(
        alt.X('order_created_on:T', title='Order Date')
    )

    bar = base.mark_bar(color='blue').encode(
        alt.Y('order_line_total:Q', title='Total Line Amount')
    )

    line = base.mark_line(color='red').encode(
        alt.Y('order_line_total:Q', title='Average Order Value')
    )

    combo_chart = alt.layer(bar, line).resolve_scale(
        y='independent'
    ).properties(
        width=600,
        height=400,
        title='Total Line Amount and Average Order Value Over Time'
    )

    st.altair_chart(combo_chart, use_container_width=True)


# Create a row that spans both columns for the Sankey diagram and nested pie chart
col2_3 = st.columns([2, 2])
with col2_3[0]:
    # Define the ECharts nested pie chart options
    nested_pie_options = {
        "title": {"text": "Sales Distribution", "left": "center"},
        "tooltip": {"trigger": "item"},
        "series": [
            {
                "name": "Sales",
                "type": "pie",
                "selectedMode": "single",
                "radius": [0, '50%'],
                "label": {"position": "inner"},
                "data": [
                    {"value": 335, "name": "Category A"},
                    {"value": 679, "name": "Category B"},
                    {"value": 1548, "name": "Category C"},
                ],
            },
            {
                "name": "Products",
                "type": "pie",
                "radius": ['60%', '75%'],
                "labelLine": {"length": 30},
                "label": {"formatter": '{b}: {c} ({d}%)'},
                "data": [
                    {"value": 335, "name": "Product A1"},
                    {"value": 310, "name": "Product A2"},
                    {"value": 234, "name": "Product B1"},
                    {"value": 135, "name": "Product C1"},
                    {"value": 1048, "name": "Product C2"},
                ],
            },
        ],
    }

    # Render the ECharts nested pie chart
    st_echarts(options=nested_pie_options, height="400px")

with col2_3[1]:
    # Define the ECharts Sankey diagram options
    sankey_options = {
        "title": {"text": "Sales Flow", "left": "center"},
        "tooltip": {"trigger": "item", "triggerOn": "mousemove"},
        "series": [
            {
                "type": "sankey",
                "layout": "none",
                "data": [
                    {"name": "Category A"},
                    {"name": "Category B"},
                    {"name": "Category C"},
                    {"name": "Product A1"},
                    {"name": "Product A2"},
                    {"name": "Product B1"},
                    {"name": "Product C1"},
                    {"name": "Product C2"},
                ],
                "links": [
                    {"source": "Category A", "target": "Product A1", "value": 10},
                    {"source": "Category A", "target": "Product A2", "value": 15},
                    {"source": "Category B", "target": "Product B1", "value": 25},
                    {"source": "Category C", "target": "Product C1", "value": 20},
                    {"source": "Category C", "target": "Product C2", "value": 30},
                ],
            }
        ],
    }

    # Render the ECharts Sankey diagram
    st_echarts(options=sankey_options, height="400px")
    
# Create a row that spans both columns for the USA heatmap
col1_2 = st.columns([2, 2])
with col1_2[0]:
    # Define the ECharts USA heatmap options
    usa_heatmap_options = {
        "title": {"text": "Sales Heatmap", "left": "center"},
        "tooltip": {"trigger": "item"},
        "visualMap": {
            "min": 0,
            "max": 1000,
            "left": "left",
            "top": "bottom",
            "text": ["High", "Low"],
            "calculable": True
        },
        "geo": {
            "map": "USA",
            "label": {"emphasis": {"show": False}},
            "roam": True,
            "itemStyle": {
                "normal": {"areaColor": "#323c48", "borderColor": "#111"},
                "emphasis": {"areaColor": "#2a333d"}
            }
        },
        "series": [
            {
                "name": "Sales",
                "type": "map",
                "mapType": "USA",
                "roam": False,
                "label": {
                    "normal": {"show": True},
                    "emphasis": {"show": True}
                },
                "data": [
                    {"name": "California", "value": 1000},
                    {"name": "Texas", "value": 800},
                    {"name": "New York", "value": 600},
                    {"name": "Florida", "value": 400},
                    {"name": "Illinois", "value": 200},
                ]
            }
        ]
    }

    # Render the ECharts USA heatmap
    st_echarts(options=usa_heatmap_options, height="400px")
    

st.dataframe(data=cli, height=600, use_container_width=True)
