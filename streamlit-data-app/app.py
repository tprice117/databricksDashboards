import os
from databricks import sql
from databricks.sdk.core import Config
import streamlit as st
import pandas as pd

from dotenv import load_dotenv
# uncomment to run locally

from datetime import datetime, timedelta
from streamlit_date_picker import date_range_picker, date_picker, PickerType
from pyspark import SparkConf, SparkContext
from pyspark.sql import SQLContext
import altair as alt
from streamlit_echarts import st_echarts


dotenv_path = '.databricks/.databricks.env'

os.makedirs(os.path.dirname(dotenv_path), exist_ok=True)

if not os.path.exists(dotenv_path):
    with open(dotenv_path, 'w') as file:
        file.write('DATABRICKS_WAREHOUSE_ID=d34494d1343c5722\n')

# Load the .env file
load_dotenv(dotenv_path=dotenv_path)

# Ensure environment variable is set correctly (running locally)
warehouse_id = os.getenv('DATABRICKS_WAREHOUSE_ID')
print(f"DATABRICKS_WAREHOUSE_ID: {warehouse_id}")
assert warehouse_id, "DATABRICKS_WAREHOUSE_ID must be set in app.yaml."

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

# Extract distinct values of main_product_category
distinct_categories = cli['main_product_category'].dropna().unique().tolist()

# Add a button to select all categories
if st.button("Select All Categories"):
    st.session_state.selected_categories = distinct_categories

# Add a multiselect box for main_product_category
selected_categories = st.multiselect("Select Main Product Categories", options=distinct_categories, default=distinct_categories, key='selected_categories')

# Filter data based on the selected categories
if 'All Categories' in selected_categories or not selected_categories:
    filtered_data = cli
else:
    filtered_data = cli[cli['main_product_category'].isin(selected_categories)].copy()

# Filter data based on the selected categories
if 'All Categories' in selected_categories or not selected_categories:
    filtered_data = cli
else:
    filtered_data = cli[cli['main_product_category'].isin(selected_categories)].copy()

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

#net Revenue
net_revenue = filtered_data['order_line_total'].sum() - filtered_data['supplier_amount'].sum() if 'supplier_amount' in filtered_data.columns else filtered_data['order_line_total'].sum()

# Calculate the sum of total_line_amount
total_line_amount_sum = filtered_data['order_line_total'].sum()

# Count the distinct order_id values
distinct_order_count = filtered_data['order_id'].nunique()

#Calculate Average Order Value
average_order_value = filtered_data.groupby('order_id').apply(
    lambda x: (x['orderline_rate'] * x['orderline_quantity'] * (1 + x['orderline_platform_fee_percent'] * 0.01)).sum()
).mean()

#Calculate Take Rate
customer_amount = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE'].apply(
    lambda row: float(row['orderline_rate']) * float(row['orderline_quantity']) * (1 + float(row['orderline_platform_fee_percent']) * 0.01), axis=1
).sum()
supplier_amount_complete = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE'].apply(
    lambda row: float(row['orderline_rate']) * float(row['orderline_quantity']), axis=1
).sum()
take_rate = float((customer_amount - supplier_amount_complete) / customer_amount) if customer_amount != 0 else 0

#Net Revenue Complete: 
# Calculate Net Revenue Complete
customer_amount_complete = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE', 'order_line_total'].sum()
supplier_amount_complete = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE', 'supplier_amount'].sum() if 'supplier_amount' in filtered_data.columns else 0
net_revenue_complete = customer_amount_complete - supplier_amount_complete
##METRICS END HERE

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    st.markdown("Select Date Range")
    default_start = datetime.now().replace(year=datetime.now().year - 1, day=1)  # Start of the previous year's current calendar month
    default_end = datetime.now()
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
            <div class="card-amount" style="color: {text_color};">${filtered_data['order_line_total'].sum():,.2f}</div>
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
    customer_amount_filtered = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE'].apply(
        lambda row: float(row['orderline_rate']) * float(row['orderline_quantity']) * (1 + float(row['orderline_platform_fee_percent']) * 0.01), axis=1
    ).sum()
    supplier_amount_filtered = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE'].apply(
        lambda row: float(row['orderline_rate']) * float(row['orderline_quantity']), axis=1
    ).sum()
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
    # Prepare data for the combo line bar chart
    filtered_data['order_end_date'] = pd.to_datetime(filtered_data['order_end_date'])
    filtered_data['month'] = filtered_data['order_end_date'].dt.to_period('M')

    monthly_data = filtered_data.groupby('month').agg({
        'order_line_total': 'sum',
        }).reset_index()
    
    if 'supplier_amount' in filtered_data.columns:
        monthly_data['supplier_amount'] = filtered_data.groupby('month')['supplier_amount'].sum()
    else:
        monthly_data['supplier_amount'] = 0

    monthly_data['net_revenue'] = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE'].groupby('month').apply(
        lambda x: x['order_line_total'].sum() - x['supplier_amount'].sum() if 'supplier_amount' in x.columns else x['order_line_total'].sum()
    ).reset_index(drop=True).round(2)
    monthly_data['gmv'] = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE'].groupby('month').apply(
        lambda x: (x['orderline_rate'] * x['orderline_quantity'] * (1 + x['orderline_platform_fee_percent'] * 0.01)).sum()
    ).reset_index(drop=True).round(2)
    monthly_data = monthly_data.fillna(0)

    # Define the ECharts combo line bar chart options
    combo_chart_options = {
        "title": {"text": "Monthly GMV and Net Revenue", "left": "center"},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["GMV", "Net Revenue", "Target"], "left": "left"},
        "xAxis": {
            "type": "category",
            "data": monthly_data['month'].astype(str).tolist()
        },
        "yAxis": [
            {"type": "value", "name": "Amount"},
            {"type": "value", "name": "Target", "position": "right", "offset": 80}
        ],
        "series": [
            {
                "name": "GMV",
                "type": "bar",
                "data": monthly_data['gmv'].tolist()
            },
            {
                "name": "Net Revenue",
                "type": "bar",
                "data": monthly_data['net_revenue'].tolist()
            },
            {
                "name": "Target",
                "type": "line",
                "data": (monthly_data['gmv'] * 1.1).tolist()  # Target line 10% higher than GMV as PLACEHOLDER
            }
        ]
    }

    # Render the ECharts combo line bar chart
    st_echarts(options=combo_chart_options, height="400px")


# Create a row that spans both columns for the Sankey diagram and nested pie chart
col2_3 = st.columns([2, 2])
with col2_3[0]:
    # Define the ECharts nested pie chart options
    # Prepare data for the nested pie chart
    gmv_data = filtered_data.groupby('main_product_category').apply(
        lambda x: (x['orderline_rate'] * x['orderline_quantity'] * (1 + x['orderline_platform_fee_percent'] * 0.01)).sum()
    ).reset_index(name='gmv')

    net_revenue_data = filtered_data.groupby('main_product_category').apply(
        lambda x: x['order_line_total'].sum() - x['supplier_amount'].sum() if 'supplier_amount' in x.columns else x['order_line_total'].sum()
    ).reset_index(name='net_revenue')

    nested_pie_options = {
        "title": {"text": "Sales Distribution", "left": "center"},
        "tooltip": {"trigger": "item"},
        "series": [
            {
                "name": "Net Revenue",
                "type": "pie",
                "selectedMode": "single",
                "radius": [0, '50%'],
                "label": {"position": "inner"},
                "data": [{"value": row['net_revenue'], "name": row['main_product_category']} for _, row in net_revenue_data.iterrows()],
            },
            {
                "name": "GMV",
                "type": "pie",
                "radius": ['60%', '75%'],
                "labelLine": {"length": 10, "length2": 10},
                "label": {"formatter": '{b}: {c} ({d}%)', "overflow": "truncate", "width": 100},
                "data": [{"value": row['gmv'], "name": row['main_product_category']} for _, row in gmv_data.iterrows()],
            },
        ],
    }

    # Render the ECharts nested pie chart
    st_echarts(options=nested_pie_options, height="400px")

with col2_3[1]:
    # Prepare data for the Sankey diagram
    sankey_data = filtered_data.groupby(['main_product', 'main_product_category']).apply(
        lambda x: (x['orderline_rate'] * x['orderline_quantity'] * (1 + x['orderline_platform_fee_percent'] * 0.01)).sum()
    ).reset_index(name='gmv')

    # Filter out small values to reduce clutter
    threshold = sankey_data['gmv'].quantile(0.90)  # Keep only the top 10% of values
    sankey_data_filtered = sankey_data[sankey_data['gmv'] >= threshold]

    # Define the ECharts Sankey diagram options
    sankey_options = {
        "title": {"text": "Sales Flow", "left": "center"},
        "tooltip": {"trigger": "item", "triggerOn": "mousemove"},
        "series": [
            {
                "type": "sankey",
                "layout": "none",
                "data": [{"name": name} for name in pd.concat([sankey_data_filtered['main_product'], sankey_data_filtered['main_product_category']]).unique()],
                "links": [
                    {"source": row['main_product'], "target": row['main_product_category'], "value": row['gmv']}
                    for _, row in sankey_data_filtered.iterrows()
                ],
                "label": {"show": True},  # Show labels to reduce clutter
                "emphasis": {
                    "focus": "adjacency",
                    "label": {"show": True, "position": "right"}  # Show labels on hover
                }
            }
        ],
    }

    # Render the ECharts Sankey diagram
    st_echarts(options=sankey_options, height="400px")
    
    
col1_2 = st.columns([2, 2])
with col1_2[0]:
    # Placeholder for USA heatmap
    st.markdown(
        """
        <div style="height: 400px; display: flex; align-items: center; justify-content: center; border: 1px solid #ddd;">
            <p style="color: #888;">USA Heatmap Placeholder</p>
        </div>
        """,
        unsafe_allow_html=True
    )

with col1_2[1]:
    # Calculate the percentage of orders made by non-staff users
    total_orders = filtered_data['order_id'].nunique()
    non_staff_orders = filtered_data[filtered_data['user_is_staff'] == False]['order_id'].nunique()
    non_staff_order_percentage = (non_staff_orders / total_orders) * 100 if total_orders != 0 else 0

    # Define the ECharts radial gauge options for Non-Staff Orders
    non_staff_orders_gauge_options = {
        "title": {"text": "Non-Staff Orders", "left": "center"},
        "tooltip": {"formatter": "{a} <br/>{b} : {c}%"},
        "series": [
            {
                "name": "Non-Staff Orders",
                "type": "gauge",
                "detail": {"formatter": "{value}%"},
                "data": [{"value": round(non_staff_order_percentage, 2), "name": "Non-Staff Orders"}],
                "axisLine": {
                    "lineStyle": {
                        "width": 10,
                        "color": [[0.2, '#FF6F61'], [0.8, '#FFEB3B'], [1, '#4CAF50']]
                    }
                }
            }
        ]
    }

    # Render the ECharts radial gauge for Non-Staff Orders
    st_echarts(options=non_staff_orders_gauge_options, height="400px")
    
# Prepare data for the line charts


monthly_avg_order_value = filtered_data.groupby('month').apply(
    lambda x: round(x['order_line_total'].sum() / x['order_id'].nunique(), 2) if x['order_id'].nunique() != 0 else 0
).reset_index(name='avg_order_value')

monthly_avg_order_value['avg_order_value'] = monthly_avg_order_value['avg_order_value'].apply(lambda x: round(x, 2))

monthly_avg_take_rate = filtered_data.groupby('month').apply(
    lambda x: round((
        x.apply(lambda row: float(row['orderline_rate']) * float(row['orderline_quantity']) * (1 + float(row['orderline_platform_fee_percent']) * 0.01), axis=1).sum() -
        x.apply(lambda row: float(row['orderline_rate']) * float(row['orderline_quantity']), axis=1).sum()
    ) / x.apply(lambda row: float(row['orderline_rate']) * float(row['orderline_quantity']) * (1 + float(row['orderline_platform_fee_percent']) * 0.01), axis=1).sum() if x.shape[0] > 0 else 0, 2)
).reset_index(name='avg_take_rate')

col1_2 = st.columns([2, 2])
with col1_2[0]:
    # Define the ECharts line chart options for Avg Take Rate by Month
    avg_take_rate_options = {
        "title": {"text": "Avg Take Rate by Month", "left": "center"},
        "tooltip": {"trigger": "axis", "formatter": "{a} <br/>{b} : {c}%"},
        "xAxis": {"type": "category", "data": monthly_avg_take_rate['month'].astype(str).tolist()},
        "yAxis": {"type": "value", "axisLabel": {"formatter": "{value}%"}},
        "series": [
            {
                "name": "Avg Take Rate",
                "type": "line",
                "data": (monthly_avg_take_rate['avg_take_rate'] * 100).tolist()
            }
        ]
    }

    # Render the ECharts line chart for Avg Take Rate by Month
    st_echarts(options=avg_take_rate_options, height="400px")

with col1_2[1]:
    # Define the ECharts line chart options for Avg Order Value by Month
    avg_order_value_options = {
        "title": {"text": "Avg Order Value by Month", "left": "center"},
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "data": monthly_avg_order_value['month'].astype(str).tolist()},
        "yAxis": {"type": "value"},
        "series": [
            {
                "name": "Avg Order Value",
                "type": "line",
                "data": monthly_avg_order_value['avg_order_value'].tolist()
            }
        ]
    }

    # Render the ECharts line chart for Avg Order Value by Month
    st_echarts(options=avg_order_value_options, height="400px")

col3_4 = st.columns([2, 2])
with col3_4[0]:
    # Placeholder for a new chart or visualization
    st.markdown(
        """
        <div style="height: 400px; display: flex; align-items: center; justify-content: center; border: 1px solid #ddd;">
            <p style="color: #888;">New Chart Placeholder</p>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3_4[1]:
    # Placeholder for another new chart or visualization
    st.markdown(
        """
        <div style="height: 400px; display: flex; align-items: center; justify-content: center; border: 1px solid #ddd;">
            <p style="color: #888;">Another New Chart Placeholder</p>
        </div>
        """,
        unsafe_allow_html=True
    )

col_full = st.columns([1])
with col_full[0]:
    # Placeholder for a full-width chart or visualization
    st.markdown(
        """
        <div style="height: 400px; display: flex; align-items: center; justify-content: center; border: 1px solid #ddd;">
            <p style="color: #888;">Full-Width Chart Placeholder</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
col_full_2 = st.columns([1])
with col_full_2[0]:
    # Prepare data for the treemap
    treemap_data = filtered_data.groupby('industry_name').agg({
        'orderline_rate': 'sum',
        'orderline_quantity': 'sum',
        'orderline_platform_fee_percent': 'mean'
    }).reset_index()

    treemap_data['gmv'] = treemap_data.apply(
        lambda row: round(row['orderline_rate'] * row['orderline_quantity'] * (1 + row['orderline_platform_fee_percent'] * 0.01), 2), axis=1
    )

    treemap_options = {
        "title": {"text": "Total GMV by Industry", "left": "center"},
        "tooltip": {"trigger": "item", "formatter": "{b}: ${c:,.2f}"},
        "series": [
            {
                "type": "treemap",
                "data": [{"name": row['industry_name'], "value": row['gmv']} for _, row in treemap_data.iterrows()],
                "label": {"show": True, "formatter": "{b}\n${c:,.2f}"}
            }
        ]
    }


    st_echarts(options=treemap_options, height="800px", key="treemap-container")
    

col_new = st.columns([2, 2])
with col_new[0]:
    # Prepare data for the bubble chart
    bubble_data = filtered_data.groupby('main_product_category').agg({
        'order_id': 'nunique',
        'orderline_rate': 'sum',
        'orderline_quantity': 'sum',
        'orderline_platform_fee_percent': 'mean'
    }).reset_index()

    bubble_data['gmv'] = bubble_data.apply(
        lambda row: round(row['orderline_rate'] * row['orderline_quantity'] * (1 + row['orderline_platform_fee_percent'] * 0.01), 2), axis=1
    )

    bubble_chart_options = {
        "title": {"text": "Total GMV vs User Count", "left": "center"},
        "tooltip": {"trigger": "item", "formatter": "{a} <br/>{b} : {c}"},
        "xAxis": {"type": "category", "data": bubble_data['main_product_category'].tolist()},
        "yAxis": {"type": "value", "name": "Total GMV"},
        "series": [
            {
                "name": "GMV vs User Count",
                "type": "scatter",
                "symbolSize": 20,
                "data": bubble_data.apply(lambda row: [row['main_product_category'], row['gmv'], row['order_id']], axis=1).tolist()
            }
        ]
    }

    # Render the ECharts bubble chart
    st_echarts(options=bubble_chart_options, height="400px")

with col_new[1]:
    # Placeholder for another new chart or visualization
    st.markdown(
        """
        <div style="height: 400px; display: flex; align-items: center; justify-content: center; border: 1px solid #ddd;">
            <p style="color: #888;">Another New Chart Placeholder</p>
        </div>
        """,
        unsafe_allow_html=True
    )
st.dataframe(data=cli, height=600, use_container_width=True)