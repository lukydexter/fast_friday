import streamlit as st
import pandas as pd
import datetime
from io import StringIO, BytesIO
import plotly.express as px
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

st.set_page_config(layout="wide", page_title="Expense Tracker")
st.title("Expense Tracker")

CATEGORIES = [
    "Food", "Transportation", "Utilities", "Entertainment",
    "Other", "Healthcare", "Insurance", "Subscription", "Travel"
]

CATEGORY_COLORS = {
    "Food": "#636EFA",
    "Transportation": "#EF553B",
    "Utilities": "#00CC96",
    "Entertainment": "#AB63FA",
    "Other": "#FFA15A",
    "Healthcare": "#19D3F3",
    "Insurance": "#FF6692",
    "Subscription": "#B6E880",
    "Travel": "#FF97FF"
}

def load_data():
    try:
        df_temp = pd.read_csv("expenses_data.csv")
        df_temp["Date"] = pd.to_datetime(df_temp["Date"]).dt.date
        return df_temp
    except FileNotFoundError:
        return pd.DataFrame(columns=["Date", "Title", "Description", "Amount", "Category"])

def save_data(df):
    df.to_csv("expenses_data.csv", index=False)

df = load_data()

# Sidebar filters
st.sidebar.header("Filters")
start_date = st.sidebar.date_input("Start Date", datetime.date.today().replace(day=1))
end_date = st.sidebar.date_input("End Date", datetime.date.today())
category_filter = st.sidebar.multiselect("Filter by Category", options=CATEGORIES, default=None)
sort_order = st.sidebar.radio("Sort by Date", ["Newest First", "Oldest First"])

filtered_df = df.copy()
if not filtered_df.empty:
    filtered_df["Date"] = pd.to_datetime(filtered_df["Date"])
    filtered_df = filtered_df[
        (filtered_df["Date"] >= pd.to_datetime(start_date)) &
        (filtered_df["Date"] <= pd.to_datetime(end_date))
    ]
    if category_filter:
        filtered_df = filtered_df[filtered_df["Category"].isin(category_filter)]
    ascending_sort = (sort_order == "Oldest First")
    filtered_df = filtered_df.sort_values("Date", ascending=ascending_sort)
    filtered_df["Date"] = filtered_df["Date"].dt.date

st.subheader("Quick Stats")
current_total = filtered_df["Amount"].sum() if not filtered_df.empty else 0
st.write(f"**Total (Filtered):** {current_total:.2f}")

if not filtered_df.empty:
    filtered_dates = pd.to_datetime(filtered_df["Date"])
    current_month = filtered_dates.dt.month.max()
    current_year = filtered_dates.dt.year.max()
    last_month_data = df.copy()
    last_month_data["Date"] = pd.to_datetime(last_month_data["Date"])
    last_month_data = last_month_data[
        (last_month_data["Date"].dt.year == current_year) &
        (last_month_data["Date"].dt.month == (current_month - 1))
    ]
    last_month_total = last_month_data["Amount"].sum() if not last_month_data.empty else 0
    st.write(f"**Last Month's Total:** {last_month_total:.2f}")

col1, col2 = st.columns([3,1])

with col1:
    st.subheader("Filtered Expense Records")
    st.dataframe(filtered_df)

    st.subheader("Delete Expense")
    selected_index = st.selectbox("Select an expense to delete", filtered_df.index)
    if selected_index is not None:
        selected_expense = filtered_df.loc[selected_index]
        if st.button("Delete Expense"):
            df = df.drop(selected_index)
            save_data(df)
            st.success("Expense deleted successfully!")
            st.rerun()

with col2:
    st.subheader("Add New Expense")
    with st.form("expense_form"):
        date = st.date_input("Date", datetime.date.today())
        title = st.text_input("Title")
        description = st.text_area("Description")
        amount_str = st.text_input("Amount (EUR)")
        category = st.selectbox("Category", CATEGORIES)
        submitted = st.form_submit_button("Add Expense")

    if submitted:
        try:
            amount_val = float(amount_str)
        except ValueError:
            amount_val = 0.0

        new_entry = pd.DataFrame({
            "Date": [date],
            "Title": [title],
            "Description": [description],
            "Amount": [amount_val],
            "Category": [category]
        })
        df = pd.concat([df, new_entry], ignore_index=True)
        save_data(df)
        st.success("Expense added successfully!")
        st.rerun()

if not filtered_df.empty:
    st.subheader("Charts")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        by_category = filtered_df.groupby("Category")["Amount"].sum().reset_index()
        total_expenses = by_category["Amount"].sum()
        fig_ring = px.pie(
            by_category,
            values="Amount",
            names="Category",
            hole=0.4,
            title=f"Expenses by Category (Total={total_expenses:.2f})",
            color="Category",
            color_discrete_map=CATEGORY_COLORS
        )
        fig_ring.update_traces(textinfo="label+value+percent")
        st.plotly_chart(fig_ring, use_container_width=True)

    with chart_col2:
        daily_cat_df = filtered_df.groupby(["Date", "Category"])["Amount"].sum().unstack(fill_value=0)
        daily_cat_df.index = pd.to_datetime(daily_cat_df.index)
        daily_cat_df = daily_cat_df.sort_index()
        st.line_chart(daily_cat_df)

    st.subheader("Compare Totals Over Time")
    group_option = st.selectbox("Group totals by", ("Day", "Month", "Year"))
    temp_df = filtered_df.copy()
    temp_df["Date"] = pd.to_datetime(temp_df["Date"])

    if group_option == "Day":
        grouped = temp_df.groupby([pd.Grouper(key="Date", freq="D"), "Category"])["Amount"].sum().unstack(fill_value=0)
    elif group_option == "Month":
        grouped = temp_df.groupby([pd.Grouper(key="Date", freq="M"), "Category"])["Amount"].sum().unstack(fill_value=0)
    else:
        grouped = temp_df.groupby([pd.Grouper(key="Date", freq="Y"), "Category"])["Amount"].sum().unstack(fill_value=0)

    grouped = grouped.sort_index()
    fig_bar = px.bar(grouped, barmode='stack', color_discrete_map=CATEGORY_COLORS)
    fig_bar.update_traces(marker_line_color="black", marker_line_width=0.5)
    fig_bar.update_layout(bargap=0.2)  # Make bars wider
    st.plotly_chart(fig_bar, use_container_width=True)

st.subheader("Download CSV file")
csv_buffer = StringIO()
df.to_csv(csv_buffer, index=False)
st.download_button(
    label="Download CSV",
    data=csv_buffer.getvalue(),
    file_name="expenses_data.csv",
    mime="text/csv"
)

# st.subheader("Download PDF of This Page")
# pdf_export = st.button("Create PDF")
# if pdf_export:
#     buffer = BytesIO()
#     p = canvas.Canvas(buffer, pagesize=letter)
#     p.drawString(100, 750, "Expense Tracker Report")
#     p.drawString(100, 730, df.to_string(index=False))
#     p.showPage()
#     p.save()
#     buffer.seek(0)
#     st.download_button(label="Export_Report",
#                        data=buffer,
#                        file_name="expense_report.pdf",
#                        mime='application/pdf')