import os
from databricks import sql 
from databricks.sdk.core import Config
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_date_picker import date_range_picker, date_picker, PickerType
from pyspark import SparkConf, SparkContext
from pyspark.sql import SQLContext
import altair as alt
from streamlit_echarts import st_echarts


# Ensure environment variable is set correctly

assert "DATABRICKS_SERVER_HOSTNAME" in st.secrets, "DATABRICKS_SERVER_HOSTNAME must be set"
assert "DATABRICKS_HTTP_PATH" in st.secrets, "DATABRICKS_HTTP_PATH must be set"
assert "DATABRICKS_ACCESS_TOKEN" in st.secrets, "DATABRICKS_ACCESS_TOKEN must be set"
assert "DATABRICKS_WAREHOUSE_ID" in st.secrets, "DATABRICKS_WAREHOUSE_ID must be set"

def sqlQuery(query: str) -> pd.DataFrame:
    """Runs a SQL query on Databricks and returns the result as a Pandas DataFrame."""

    # Fetch credentials from Streamlit secrets
    server_hostname = st.secrets["DATABRICKS_SERVER_HOSTNAME"]
    http_path = st.secrets["DATABRICKS_HTTP_PATH"]
    access_token = st.secrets["DATABRICKS_ACCESS_TOKEN"]

    try:
        with sql.connect(
            server_hostname=server_hostname,
            http_path=http_path,
            access_token=access_token
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                return cursor.fetchall_arrow().to_pandas()

    except Exception as e:
        st.error(f"Databricks connection error: {e}")
        return pd.DataFrame()

# Streamlit App UI
st.set_page_config(layout="wide")

@st.cache_data(ttl=30)  # only re-query if it's been 30 seconds
def getData():
    start_date = "2025-01-01"
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    query = f"""
        select 
            ug.id as user_group_id,
            og.id as ordergroup_id,
            og.project_id,
            og.agreement as order_group_agreement,
            og.code as order_group_code,
            og.end_date as order_group_end_date,
            og.is_delivery as order_group_is_delivery,
            og.placement_details as order_group_placement_details,
            og.removal_fee as order_group_removal_fee,
            og.shift_count as order_group_shift_count,
            og.start_date as order_group_start_date,

            --order
            o.id as order_id,
            o.accepted_on as order_accepted_on,
            o.billing_comments_internal_use as order_billing_comments_internal_use,
            o.code as order_code,
            o.completed_on as order_completed_on,
            o.created_on as order_created_on,
            o.end_date as order_end_date,
            o.schedule_window as order_schedule_window,
            o.status as order_status,
            o.submitted_on as order_submitted_on,
            o.created_by_id as order_created_by,
            o.submitted_by_id as submitted_by_id,

            --orderline
            oli.id as orderline_id,
            oli.backbill as orderline_backbill,
            oli.is_flat_rate as orderline_is_flat_rate,
            oli.paid as orderline_paid,
            oli.quantity as orderline_quantity,
            oli.rate as orderline_rate,
            oli.rate * oli.quantity as order_line_total,
            oli.platform_fee_percent as orderline_platform_fee_percent,
            oli.tax as orderline_tax,
            oli.stripe_invoice_line_item_id as stripe_invoice_line_item_id,
            oli.order_line_item_type_id as orderline_type,

            --main product
            mp.name as main_product,
            --main product category
            mpc.name as main_product_category,

            --main product category group
            mpcg.name as main_product_category_group,

            --user address 
            ua.state as user_address_state,

            --user
            u.is_staff as user_is_staff,
            u.first_name as user_first_name,
            u.last_name as user_last_name,

            --industry
            i.name as industry_name,

            --user group
            ug.name as user_group_name,
            ug.account_owner_id as user_group_account_owner_id,

            -- account owner
            uo.first_name as account_owner_first_name,
            uo.last_name as account_owner_last_name,

            --seller
            s.name as seller_name,

            --seller location
            sl.name as seller_location_name,

            --orderline item type
            olit.name as orderline_item_type_name

        from bronze_prod.postgres_prod_restricted_bronze_public.api_orderlineitem oli
        left join bronze_prod.postgres_prod_restricted_bronze_public.api_order o 
            on oli.order_id = o.id
        left join bronze_prod.postgres_prod_restricted_bronze_public.api_ordergroup og 
            on o.order_group_id = og.id
        left join bronze_prod.postgres_prod_restricted_bronze_public.api_sellerproductsellerlocation spsl
            on og.seller_product_seller_location_id = spsl.id
        left join bronze_prod.postgres_prod_restricted_bronze_public.api_sellerproduct sp
            on spsl.seller_product_id = sp.id
        left join bronze_prod.postgres_prod_restricted_bronze_public.api_product p 
            on sp.product_id = p.id
        left join bronze_prod.postgres_prod_restricted_bronze_public.api_mainproduct mp 
            on p.main_product_id = mp.id
        left join bronze_prod.postgres_prod_restricted_bronze_public.api_mainproductcategory mpc
            on mp.main_product_category_id = mpc.id
        left join bronze_prod.postgres_prod_restricted_bronze_public.api_mainproductcategorygroup mpcg
            on mpc.group_id = mpcg.id
        left join bronze_prod.postgres_prod_restricted_bronze_public.api_useraddress ua
            on og.user_address_id = ua.id
        left join bronze_prod.postgres_prod_restricted_bronze_public.api_user u
            on o.created_by_id = u.id
        left join bronze_prod.postgres_prod_restricted_bronze_public.api_usergroup ug
            on u.user_group_id = ug.id
        left join bronze_prod.postgres_prod_restricted_bronze_public.api_seller s
            on sp.seller_id = s.id
        left join bronze_prod.postgres_prod_restricted_bronze_public.api_usergroup ug_seller
            on s.id = ug_seller.seller_id
        left join bronze_prod.postgres_prod_restricted_bronze_public.api_user uo
            on ug.account_owner_id = uo.id
        left join bronze_prod.postgres_prod_restricted_bronze_public.api_industry i
            on ug.industry_id = i.id
        left join bronze_prod.postgres_prod_restricted_bronze_public.api_sellerlocation sl
            on spsl.seller_location_id = sl.id
        left join bronze_prod.postgres_prod_restricted_bronze_public.api_orderlineitemtype olit
            on oli.order_line_item_type_id = olit.id
        where o.end_date between '{start_date}' and '{end_date}'
        and o.status in ('COMPLETE', 'PENDING', 'SCHEDULED') 
        and o.status != 'CANCELLED'
    """
    
    return sqlQuery(query)
cli = getData()

st.header("Sales Performance Dashboard")

# Function to detect dark mode
def is_dark_mode():
    return st.get_option("theme.base") == "dark"

css_file_path = os.path.join(os.path.dirname(__file__), "css/style.css")
# Load custom CSS from file
if os.path.exists(css_file_path):
    with open(css_file_path, "r") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
else:
    st.warning("⚠️ CSS file not found! Make sure `css/style.css` is in the correct location.")

# Determine text color based on theme
text_color = "white" if is_dark_mode() else "black"

# Extract distinct values of main_product_category
distinct_categories = cli['main_product_category'].dropna().unique().tolist()

# Add a button to select all categories
if st.button("Select All Categories"):
    st.session_state.selected_categories = distinct_categories

# Add a multiselect box for main_product_category
selected_categories = st.multiselect(
    "Select Main Product Categories",
    options=distinct_categories,
    default=distinct_categories,
    key='selected_categories'
)

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

# Drop duplicates based on 'order_id' and 'orderline_id'
unique_data = filtered_data.drop_duplicates(subset=['order_id', 'orderline_id'])

##METRICS START HERE

# Calculate GMV (Customer Amount Complete)
gmv = unique_data.loc[unique_data['order_status'] == 'COMPLETE'].apply(
    lambda row: float(row['orderline_rate']) * float(row['orderline_quantity']) * (1 + float(row['orderline_platform_fee_percent']) * 0.01), axis=1
).sum()

# Net Revenue
net_revenue = unique_data.loc[unique_data['order_status'] == 'COMPLETE'].apply(
    lambda row: float(row['orderline_rate']) * float(row['orderline_quantity']) * (1 + float(row['orderline_platform_fee_percent']) * 0.01), axis=1
).sum() - unique_data.loc[unique_data['order_status'] == 'COMPLETE'].apply(
    lambda row: float(row['orderline_rate']) * float(row['orderline_quantity']), axis=1
).sum()
# Calculate the sum of total_line_amount
total_line_amount_sum = unique_data['order_line_total'].sum()

# Count the distinct order_id values
distinct_order_count = unique_data['order_id'].nunique()

# Calculate Average Order Value
average_order_value = unique_data.groupby('order_id').apply(
    lambda x: (x['orderline_rate'] * x['orderline_quantity'] * (1 + x['orderline_platform_fee_percent'] * 0.01)).sum()
).mean()

# Calculate Take Rate
customer_amount = unique_data.loc[unique_data['order_status'] == 'COMPLETE'].apply(
    lambda row: float(row['orderline_rate']) * float(row['orderline_quantity']) * (1 + float(row['orderline_platform_fee_percent'] * 0.01)), axis=1
).sum()
supplier_amount_complete = unique_data.loc[unique_data['order_status'] == 'COMPLETE'].apply(
    lambda row: float(row['orderline_rate']) * float(row['orderline_quantity']), axis=1
).sum()
take_rate = float((customer_amount - supplier_amount_complete) / customer_amount) if customer_amount != 0 else 0

# Net Revenue Complete
customer_amount_complete = unique_data.loc[unique_data['order_status'] == 'COMPLETE'].apply(
    lambda row: float(row['orderline_rate']) * float(row['orderline_quantity']) * (1 + float(row['orderline_platform_fee_percent']) * 0.01), axis=1
).sum()
supplier_amount_complete = unique_data.loc[unique_data['order_status'] == 'COMPLETE'].apply(
    lambda row: float(row['orderline_rate']) * float(row['orderline_quantity']), axis=1
).sum()
net_revenue_complete = customer_amount_complete - supplier_amount_complete
##METRICS END HERE

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    st.markdown("Select Date Range")
    default_start = datetime(2025, 1, 1)  # Start of 2025
    default_end = datetime.now()  # Today's date
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
            <div class="card-amount" style="color: {text_color};">{filtered_data.drop_duplicates(subset=['order_id'])['order_id'].nunique()}</div>
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
    customer_amount_complete_filtered = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE'].apply(
        lambda row: float(row['orderline_rate']) * float(row['orderline_quantity']) * (1 + float(row['orderline_platform_fee_percent']) * 0.01), axis=1
    ).sum()
    supplier_amount_complete_filtered = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE'].apply(
        lambda row: float(row['orderline_rate']) * float(row['orderline_quantity']), axis=1
    ).sum()
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
    # Prepare data for the bar chart showcasing GMV Completed and Net Revenue Completed month over month
    filtered_data['order_end_date'] = pd.to_datetime(filtered_data['order_end_date'], errors='coerce')
    filtered_data['month'] = filtered_data['order_end_date'].dt.to_period('M')

    gmv_completed_monthly = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE'].groupby('month').apply(
        lambda x: (x['orderline_rate'] * x['orderline_quantity'] * (1 + x['orderline_platform_fee_percent'] * 0.01)).sum()
    ).reset_index(name='gmv_completed')

    net_revenue_completed_monthly = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE'].groupby('month').apply(
        lambda x: (x['orderline_rate'] * x['orderline_quantity'] * (1 + x['orderline_platform_fee_percent'] * 0.01)).sum() - 
                  (x['orderline_rate'] * x['orderline_quantity']).sum()
    ).reset_index(name='net_revenue_completed')

    # Calculate target line values (10% above GMV for each month)
    gmv_completed_monthly['target'] = gmv_completed_monthly['gmv_completed'] * 1.1

    # Define the ECharts bar chart options
    gmv_chart_combination = {
        "title": {"text": "GMV Completed and Net Revenue Completed Month over Month", "left": "center", "top": "10%"},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"data": ["GMV Completed", "Net Revenue Completed", "Target"], "left": "left", "top": "20%"},
        "grid": {"top": "35%"},
        "xAxis": {
            "type": "category",
            "data": gmv_completed_monthly['month'].astype(str).tolist()
        },
        "yAxis": {"type": "value", "name": "Amount"},
        "series": [
            {
                "name": "GMV Completed",
                "type": "bar",
                "data": gmv_completed_monthly['gmv_completed'].tolist()
            },
            {
                "name": "Net Revenue Completed",
                "type": "bar",
                "data": net_revenue_completed_monthly['net_revenue_completed'].tolist()
            },
            {
                "name": "Target",
                "type": "line",
                "data": gmv_completed_monthly['target'].tolist(),
                "lineStyle": {"type": "solid", "color": "yellow"}
            }
        ]
    }

    # Render the ECharts bar chart
    st_echarts(options=gmv_chart_combination, height="400px")
# sort by group
# Create a row that spans both columns for sales dist and sales flow
col2_3 = st.columns([2, 2])
with col2_3[0]:
    # Define the ECharts nested pie chart options
    # Prepare data for the nested pie chart
    gmv_data = filtered_data.groupby('main_product_category_group').apply(
        lambda x: (x['orderline_rate'] * x['orderline_quantity'] * (1 + x['orderline_platform_fee_percent'] * 0.01)).sum()
    ).reset_index(name='gmv')

    net_revenue_data = filtered_data.groupby('main_product_category_group').apply(
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
                "data": [{"value": row['net_revenue'], "name": row['main_product_category_group']} for _, row in net_revenue_data.iterrows()],
            },
            {
                "name": "GMV",
                "type": "pie",
                "radius": ['60%', '75%'],
                "labelLine": {"length": 10, "length2": 10},
                "label": {"formatter": '{b}: {c} ({d}%)', "overflow": "truncate", "width": 100},
                "data": [{"value": row['gmv'], "name": row['main_product_category_group']} for _, row in gmv_data.iterrows()],
            },
        ],
    }

    # Render the ECharts nested pie chart
    st_echarts(options=nested_pie_options, height="400px")

with col2_3[1]:
    # Prepare data for the Sankey diagram
    sankey_data = filtered_data.groupby(['main_product_category', 'main_product_category_group']).apply(
        lambda x: (x['orderline_rate'] * x['orderline_quantity'] * (1 + x['orderline_platform_fee_percent'] * 0.01)).sum()
    ).reset_index(name='gmv')

    # Filter out small values to reduce clutter
    threshold = sankey_data['gmv'].quantile(0.60)  # Keep only the top 40% of values
    sankey_data_filtered = sankey_data[sankey_data['gmv'] >= threshold]

    # Define the ECharts Sankey diagram options
    sankey_options = {
        "title": {"text": "Sales Flow by GMV", "left": "center"},
        "tooltip": {"trigger": "item", "formatter": "{b}: {c}", "triggerOn": "mousemove"},
        "series": [
            {
                "type": "sankey",
                "layout": "none",
                "data": [{"name": name} for name in pd.concat([sankey_data_filtered['main_product_category'], sankey_data_filtered['main_product_category_group']]).unique()],
                "links": [
                    {"source": row['main_product_category'], "target": row['main_product_category_group'], "value": row['gmv']}
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
    # Placeholder for the USA heatmap
    st.markdown(
        """
        <div style="height: 400px; display: flex; align-items: center; justify-content: center;">
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
    # Ensure 'month' column is in period format
    filtered_data['month'] = filtered_data['order_end_date'].dt.to_period('M')

    # Group data by month and user group to calculate GMV and Net Revenue
    monthly_user_group_data = filtered_data.groupby(['month', 'user_group_id']).apply(
        lambda x: pd.Series({
            'gmv': (x['orderline_rate'] * x['orderline_quantity'] * (1 + x['orderline_platform_fee_percent'] * 0.01)).sum(),
            'net_revenue': x['order_line_total'].sum() - x['supplier_amount'].sum() if 'supplier_amount' in x.columns else x['order_line_total'].sum()
        })
    ).reset_index()

    # Calculate average GMV and Net Revenue per active buyer (user group) by month
    monthly_avg_gmv = monthly_user_group_data.groupby('month')['gmv'].mean().reset_index(name='avg_gmv')
    monthly_avg_net_revenue = monthly_user_group_data.groupby('month')['net_revenue'].mean().reset_index(name='avg_net_revenue')

    # Calculate the number of user groups per month
    user_groups_per_month = monthly_user_group_data.groupby('month')['user_group_id'].nunique().reset_index(name='user_group_count')

    # Define the ECharts combination bar chart options
    combo_bar_chart_options = {
        "title": {"text": "Avg GMV and Net Revenue per Active Buyer by Month", "left": "center"},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["Avg GMV", "Avg Net Revenue", "User Groups"], "left": "left"},
        "xAxis": {
            "type": "category",
            "data": monthly_avg_gmv['month'].astype(str).tolist()
        },
        "yAxis": [
            {"type": "value", "name": "Amount"},
            {"type": "value", "name": "User Groups", "position": "right"}
        ],
        "series": [
            {
                "name": "Avg GMV",
                "type": "bar",
                "data": monthly_avg_gmv['avg_gmv'].tolist()
            },
            {
                "name": "Avg Net Revenue",
                "type": "bar",
                "data": monthly_avg_net_revenue['avg_net_revenue'].tolist()
            },
            {
                "name": "User Groups",
                "type": "line",
                "yAxisIndex": 1,
                "data": user_groups_per_month['user_group_count'].tolist()
            }
        ]
    }

    # Render the ECharts combination bar chart
    st_echarts(options=combo_bar_chart_options, height="400px")

with col3_4[1]:
    # Ensure 'month' column is in period format
    filtered_data['month'] = filtered_data['order_end_date'].dt.to_period('M')

    # Group data by month and seller location to calculate GMV and Net Revenue
    monthly_seller_location_data = filtered_data.groupby(['month', 'seller_location_name']).apply(
        lambda x: pd.Series({
            'gmv': (x['orderline_rate'] * x['orderline_quantity'] * (1 + x['orderline_platform_fee_percent'] * 0.01)).sum(),
            'net_revenue': x['order_line_total'].sum() - x['supplier_amount'].sum() if 'supplier_amount' in x.columns else x['order_line_total'].sum()
        })
    ).reset_index()

    # Calculate average GMV and Net Revenue per active seller location by month
    monthly_avg_gmv_seller = monthly_seller_location_data.groupby('month')['gmv'].mean().reset_index(name='avg_gmv')
    monthly_avg_net_revenue_seller = monthly_seller_location_data.groupby('month')['net_revenue'].mean().reset_index(name='avg_net_revenue')

    # Calculate the number of active seller locations per month
    seller_locations_per_month = monthly_seller_location_data.groupby('month')['seller_location_name'].nunique().reset_index(name='seller_location_count')

    # Define the ECharts combination bar chart options for active seller locations
    combo_bar_chart_options_seller = {
        "title": {"text": "Avg GMV and Net Revenue per Active Seller Location by Month", "left": "center"},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["Avg GMV", "Avg Net Revenue", "Seller Locations"], "left": "left"},
        "xAxis": {
            "type": "category",
            "data": monthly_avg_gmv_seller['month'].astype(str).tolist()
        },
        "yAxis": [
            {"type": "value", "name": "Amount"},
            {"type": "value", "name": "Seller Locations", "position": "right", "axisLabel": {"show": False}, "axisLine": {"show": False}, "axisTick": {"show": False}}
        ],
        "series": [
            {
                "name": "Avg GMV",
                "type": "bar",
                "data": monthly_avg_gmv_seller['avg_gmv'].tolist()
            },
            {
                "name": "Avg Net Revenue",
                "type": "bar",
                "data": monthly_avg_net_revenue_seller['avg_net_revenue'].tolist()
            },
            {
                "name": "Seller Locations",
                "type": "line",
                "yAxisIndex": 1,
                "data": seller_locations_per_month['seller_location_count'].tolist(),

            }
        ]
    }

    # Render the ECharts combination bar chart for active seller locations
    st_echarts(options=combo_bar_chart_options_seller, height="400px")

col_full = st.columns([1])
with col_full[0]:
    # Placeholder for a full-width chart or visualization
    st.markdown(
        """
        <div style="height: 400px; display: flex; align-items: center; justify-content: center;">
            <p style="color: #888;">Order.AutoOrderType Chart Placeholder</p>
        </div>
        """,
        unsafe_allow_html=True
    )
col_full_2 = st.columns([1])
with col_full_2[0]:
    # Prepare data for the treemap
    treemap_data = filtered_data.groupby(['industry_name', 'main_product_category']).agg({
        'orderline_rate': 'sum',
        'orderline_quantity': 'sum',
        'orderline_platform_fee_percent': 'mean'
    }).reset_index()

    treemap_data['gmv'] = treemap_data.apply(
        lambda row: round(row['orderline_rate'] * row['orderline_quantity'] * (1 + row['orderline_platform_fee_percent'] * 0.01), 2), axis=1
    )

    # Prepare data for the treemap
    treemap_data_grouped = treemap_data.groupby('industry_name').apply(
        lambda x: [{"name": row['main_product_category'], "value": row['gmv']} for _, row in x.iterrows()]
    ).reset_index(name='children')

    treemap_data_final = [
        {"name": industry, "children": children}
        for industry, children in treemap_data_grouped.values
    ]

    # Define the ECharts treemap options
    treemap_options = {
        "title": {"text": "GMV by Industry and Product Category", "left": "center"},
        "tooltip": {"trigger": "item", "formatter": "{b}: ${c}"},
        "series": [
            {
                "type": "treemap",
                "data": treemap_data_final,
                "label": {
                    "show": True,
                    "formatter": "{b}",
                    "fontSize": 16  # Increase the font size for better readability
                },
                "upperLabel": {
                    "show": True,
                    "height": 30
                },
                "levels": [
                    {
                        "itemStyle": {
                            "borderColor": "#555",
                            "borderWidth": 4,
                            "gapWidth": 4
                        }
                    },
                    {
                        "colorSaturation": [0.3, 0.6],
                        "itemStyle": {
                            "borderColorSaturation": 0.7,
                            "gapWidth": 2,
                            "borderWidth": 2
                        }
                    },
                    {
                        "colorSaturation": [0.3, 0.5],
                        "itemStyle": {
                            "borderColorSaturation": 0.6,
                            "gapWidth": 1
                        }
                    }
                ]
            }
        ]
    }

    # Render the ECharts treemap
    st_echarts(options=treemap_options, height="600px")

col_new = st.columns([2, 2])
with col_new[0]:
    # Prepare data for the bubble chart
    bubble_data = filtered_data.groupby('industry_name').agg({
        'order_id': 'nunique',
        'orderline_rate': 'sum',
        'orderline_quantity': 'sum',
        'orderline_platform_fee_percent': 'mean'
    }).reset_index()

    bubble_data['gmv'] = bubble_data.apply(
        lambda row: round(row['orderline_rate'] * row['orderline_quantity'] * (1 + row['orderline_platform_fee_percent'] * 0.01), 2), axis=1
    )

    bubble_chart_options = {
        "title": {"text": "Total GMV vs User Count by Industry", "left": "center"},
        "tooltip": {"trigger": "item", "formatter": "{a} <br/>{b} : {c}"},
        "xAxis": {"type": "category", "data": bubble_data['industry_name'].tolist()},
        "yAxis": {"type": "value", "name": "Total GMV"},
        "series": [
            {
                "name": "GMV vs User Count",
                "type": "scatter",
                "symbolSize": 20,
                "data": bubble_data.apply(lambda row: [row['industry_name'], row['gmv'], row['order_id']], axis=1).tolist()
            }
        ]
    }

    # Render the ECharts bubble chart
    st_echarts(options=bubble_chart_options, height="400px")

with col_new[1]:
    # Prepare data for the bubble chart
    bubble_data = filtered_data.groupby(['industry_name', 'seller_location_name']).agg({
        'order_id': 'nunique',
        'orderline_rate': 'sum',
        'orderline_quantity': 'sum',
        'orderline_platform_fee_percent': 'mean'
    }).reset_index()

    bubble_data['gmv'] = bubble_data.apply(
        lambda row: round(row['orderline_rate'] * row['orderline_quantity'] * (1 + row['orderline_platform_fee_percent'] * 0.01), 2), axis=1
    )

    bubble_chart_options = {
        "title": {"text": "Total GMV vs Seller Location Count by User Group Industry", "left": "center"},
        "tooltip": {"trigger": "item", "formatter": "{a} <br/>{b} : {c}"},
        "xAxis": {"type": "category", "data": bubble_data['industry_name'].tolist()},
        "yAxis": {"type": "value", "name": "Total GMV"},
        "series": [
            {
                "name": "GMV vs Seller Location Count",
                "type": "scatter",
                "symbolSize": 20,
                "data": bubble_data.apply(lambda row: [row['industry_name'], row['gmv'], row['order_id']], axis=1).tolist()
            }
        ]
    }

    # Render the ECharts bubble chart
    st_echarts(options=bubble_chart_options, height="400px")
    
    
col_new_row = st.columns([1, 1, 1])
with col_new_row[0]:
    # Prepare data for the donut chart
    donut_data = filtered_data.groupby('orderline_item_type_name').apply(
        lambda x: (x['orderline_rate'] * x['orderline_quantity'] * (1 + x['orderline_platform_fee_percent'] * 0.01)).sum()
    ).reset_index(name='gmv')

    # Define the ECharts donut chart options
    donut_chart_options = {
        "title": {"text": "GMV by Order Line Item Type", "left": "center"},
        "tooltip": {"trigger": "item", "formatter": "{a} <br/>{b} : {c} ({d}%)"},
        "legend": {"orient": "vertical", "left": "left", "data": donut_data['orderline_item_type_name'].tolist()},
        "series": [
            {
                "name": "Order Line Item Type",
                "type": "pie",
                "radius": ["40%", "70%"],
                "avoidLabelOverlap": False,
                "label": {"show": False, "position": "center"},
                "emphasis": {
                    "label": {"show": True, "fontSize": "20", "fontWeight": "bold"}
                },
                "labelLine": {"show": False},
                "data": [{"value": row['gmv'], "name": row['orderline_item_type_name']} for _, row in donut_data.iterrows()]
            }
        ]
    }

    # Render the ECharts donut chart
    st_echarts(options=donut_chart_options, height="400px")

with col_new_row[1]:
    # Prepare data for the donut chart showcasing orderline_type by count
    orderline_type_count = filtered_data['orderline_item_type_name'].value_counts().reset_index()
    orderline_type_count.columns = ['orderline_item_type_name', 'count']

    # Define the ECharts donut chart options
    donut_chart_options_orderline_type = {
        "title": {"text": "Order Line Item Type by Count", "left": "center"},
        "tooltip": {"trigger": "item", "formatter": "{a} <br/>{b} : {c} ({d}%)"},
        "legend": {"orient": "vertical", "left": "left", "data": orderline_type_count['orderline_item_type_name'].tolist()},
        "series": [
            {
                "name": "Order Line Item Type",
                "type": "pie",
                "radius": ["40%", "70%"],
                "avoidLabelOverlap": False,
                "label": {"show": False, "position": "center"},
                "emphasis": {
                    "label": {"show": True, "fontSize": "20", "fontWeight": "bold"}
                },
                "labelLine": {"show": False},
                "data": [{"value": row['count'], "name": row['orderline_item_type_name']} for _, row in orderline_type_count.iterrows()]
            }
        ]
    }

    # Render the ECharts donut chart
    st_echarts(options=donut_chart_options_orderline_type, height="400px")

with col_new_row[2]:
    # Prepare data for the donut chart showcasing orderline_item by net revenue
    orderline_net_revenue = filtered_data.groupby('orderline_item_type_name').apply(
        lambda x: x['order_line_total'].sum() - x['supplier_amount'].sum() if 'supplier_amount' in x.columns else x['order_line_total'].sum()
    ).reset_index(name='net_revenue')

    # Define the ECharts donut chart options
    donut_chart_options_orderline_net_revenue = {
        "title": {"text": "Net Revenue by Order Line Item Type", "left": "center"},
        "tooltip": {"trigger": "item", "formatter": "{a} <br/>{b} : {c} ({d}%)"},
        "legend": {"orient": "vertical", "left": "left", "data": orderline_net_revenue['orderline_item_type_name'].tolist()},
        "series": [
            {
                "name": "Order Line Item Type",
                "type": "pie",
                "radius": ["40%", "70%"],
                "avoidLabelOverlap": False,
                "label": {"show": False, "position": "center"},
                "emphasis": {
                    "label": {"show": True, "fontSize": "20", "fontWeight": "bold"}
                },
                "labelLine": {"show": False},
                "data": [{"value": row['net_revenue'], "name": row['orderline_item_type_name']} for _, row in orderline_net_revenue.iterrows()]
            }
        ]
    }

    # Render the ECharts donut chart
    st_echarts(options=donut_chart_options_orderline_net_revenue, height="400px")
    
col_last_row = st.columns([1, 1])
with col_last_row[0]:
    # Group by account_owner_id and year_month, then sum customer_amount_complete
    gmv_per_sales_rep = filtered_data.loc[filtered_data['order_status'] == 'COMPLETE'].groupby(['user_group_account_owner_id', 'month'], as_index=False)['order_line_total'].sum()

    # Translate account_owner_id to actual name
    gmv_per_sales_rep = gmv_per_sales_rep.merge(filtered_data[['user_group_account_owner_id', 'account_owner_first_name', 'account_owner_last_name']].drop_duplicates(), left_on='user_group_account_owner_id', right_on='user_group_account_owner_id', how='left')
    gmv_per_sales_rep['full_name'] = gmv_per_sales_rep['account_owner_first_name'] + ' ' + gmv_per_sales_rep['account_owner_last_name']
    gmv_per_sales_rep.drop(columns=['user_group_account_owner_id', 'account_owner_first_name', 'account_owner_last_name'], inplace=True)
    gmv_per_sales_rep.rename(columns={'order_line_total': 'gmv'}, inplace=True)

    # Define the ECharts bar chart options
    bar_chart_options_sales_rep = {
        "title": {"text": "GMV per Sales-Rep Month by Month", "left": "center", "top": "5%"},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"data": gmv_per_sales_rep['full_name'].unique().tolist(), "left": "left"},
        "xAxis": {
            "type": "category",
            "data": gmv_per_sales_rep['month'].astype(str).unique().tolist()
        },
        "yAxis": {"type": "value", "name": "GMV"},
        "series": [
            {
                "name": sales_rep,
                "type": "bar",
                "stack": "total",
                "data": gmv_per_sales_rep[gmv_per_sales_rep['full_name'] == sales_rep]['gmv'].round(2).tolist()
            } for sales_rep in gmv_per_sales_rep['full_name'].unique()
        ]
    }

    # Render the ECharts bar chart
    st_echarts(options=bar_chart_options_sales_rep, height="400px")

with col_last_row[1]:
    # Prepare data for the bar chart showcasing Net Revenue per sales-rep month by month
    net_revenue_per_sales_rep = filtered_data.groupby(['month', 'account_owner_first_name', 'account_owner_last_name']).apply(
        lambda x: x['order_line_total'].sum() - x['supplier_amount'].sum() if 'supplier_amount' in x.columns else x['order_line_total'].sum()
    ).reset_index(name='net_revenue')

    # Combine first and last names to create full names
    net_revenue_per_sales_rep['full_name'] = net_revenue_per_sales_rep['account_owner_first_name'] + ' ' + net_revenue_per_sales_rep['account_owner_last_name']

    # Define the ECharts bar chart options
    bar_chart_options_net_revenue = {
        "title": {"text": "Net Revenue per Sales-Rep Month by Month", "left": "center", "top": "5%"},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"data": net_revenue_per_sales_rep['full_name'].unique().tolist(), "left": "left"},
        "xAxis": {
            "type": "category",
            "data": net_revenue_per_sales_rep['month'].astype(str).unique().tolist()
        },
        "yAxis": {"type": "value", "name": "Net Revenue"},
        "series": [
            {
                "name": sales_rep,
                "type": "bar",
                "stack": "total",
                "data": net_revenue_per_sales_rep[net_revenue_per_sales_rep['full_name'] == sales_rep]['net_revenue'].round(2).tolist()
            } for sales_rep in net_revenue_per_sales_rep['full_name'].unique()
        ]
    }

    # Render the ECharts bar chart
    st_echarts(options=bar_chart_options_net_revenue, height="400px")
# Limit the number of rows displayed in the DataFrame
st.dataframe(data=cli, height=600, use_container_width=True)



