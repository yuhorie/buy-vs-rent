import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
import altair as alt

def pmt(rate, periods, principal):
    return rate * principal / (1 - (1 + rate) ** -periods)

def fv_annuity(rate, periods, pmt):
    if rate == 0.0:
        return pmt * periods
    else:
        return pmt * ((1 + rate) ** periods - 1) / rate
        # return pmt * ((1 + rate) ** (periods + 1) - (1 + rate)) / rate

st.sidebar.title("Home")
# mode = st.sidebar.selectbox("Select", ["Buy vs Rent"])

home_value = 1e6 * st.sidebar.slider("Home Value (M$)", value=1.5, min_value=0.5, max_value=3.0, step=0.01)
down_payment_percent = 1e-2 * st.sidebar.slider("Down Payment (%)", value=20, min_value=0, max_value=100, step=5)
HOA = st.sidebar.slider("Monthly HOA ($)", value=0, min_value=0, max_value=500, step=10)
apr = 1e-2 * st.sidebar.slider("Interest (%)", value=2.875, min_value=0.0, max_value=5.0, step=0.001)
home_inflation = 1e-2 * st.sidebar.slider("Yearly Home Inflation (%)", value=5.0, min_value=0.0, max_value=20.0, step=0.1)
selling_fee = 1e-2 * st.sidebar.slider("Selling Cost (%)", value=6.0, min_value=0.0, max_value=10.0, step=0.1)

rent = st.sidebar.slider("Monthly Rent ($)", value=4000, min_value=500, max_value=10000, step=100)
stock_inflation = 1e-2 * st.sidebar.slider("Yearly Stock Inflation (%)", value=5.0, min_value=0.0, max_value=50.0, step=1.0)



tax_rate = 0.0077
property_tax = np.round(home_value * tax_rate / 12)
home_insurance = 100
principal = home_value * (1 - down_payment_percent)
down_payment = home_value * down_payment_percent
years = 30
months = 12
periods = years * months
interest = apr / months
start_date = date(2021, 1, 1)

df_summary = pd.DataFrame({"A": [1.0]})

st.markdown(f"""
You're comparing...

{int(home_value):,}
    """)

st.dataframe(df_summary)

mortgage = np.round(pmt(interest, periods, principal), 2)
total_payment = mortgage + property_tax + HOA + home_insurance
if total_payment - rent > 0:
    saving = total_payment - rent
else:
    saving = 0

rng = pd.date_range(start_date, periods=periods, freq="MS")
rng.name = "Payment Date"
keys = ["Payment", "P&I", "Fees", "Principal Paid", "Interest Paid", "Starting Balance", "Ending Balance", "Cumulative Principal", "Cumulative Payment"]
df = pd.DataFrame(index=rng, columns=keys, dtype="float")
df.reset_index(inplace=True)
df.index += 1
df.index.name = "Period"

df["P&I"] = mortgage
df["Fees"] = property_tax + HOA + home_insurance
df["Payment"] = total_payment
for period in range(1, periods+1):
    if period == 1:
        df.loc[period, "Starting Balance"] = principal
    else:
        df.loc[period, "Starting Balance"] = df.loc[period-1, "Ending Balance"]

    df.loc[period, "Interest Paid"] = np.round(df.loc[period, "Starting Balance"] * interest, 2)
    df.loc[period, "Principal Paid"] = mortgage - df.loc[period, "Interest Paid"]
    df.loc[period, "Ending Balance"] = df.loc[period, "Starting Balance"] - df.loc[period, "Principal Paid"]

df["Cumulative Principal"] = df["Principal Paid"].cumsum()
df["Cumulative Payment"] = df["Payment"].cumsum()


rng = pd.date_range(start=start_date, periods=years, freq="AS")
rng.name = "Payment Year"
keys = ["Payment", "P&I", "Fees", "Principal Paid", "Interest Paid", "Starting Balance", "Ending Balance", "Cumulative Principal", "Cumulative Payment", "Home Value", "Net"]
df_year = pd.DataFrame(index=rng, columns=keys, dtype="float")
df_year.reset_index(inplace=True)
df_year.index += 1
df_year.index.name = "Period"

df_year["P&I"] = mortgage * months
df_year["Fees"] = (property_tax + HOA + home_insurance) * months
df_year["Payment"] = (mortgage + property_tax + HOA + home_insurance) * months
for year in range(1, years+1):
    df_year.loc[year, "Interest Paid"] = np.sum(df.loc[1+months*(year-1):months * year, "Interest Paid"])
    df_year.loc[year, "Principal Paid"] = np.sum(df.loc[1+months*(year-1):months * year, "Principal Paid"])
    df_year.loc[year, "Starting Balance"] = df.loc[1+months*(year-1), "Starting Balance"]
    df_year.loc[year, "Ending Balance"] = df.loc[months * year, "Ending Balance"]
df_year["Cumulative Principal"] = df_year["Principal Paid"].cumsum()
df_year["Cumulative Payment"] = df_year["Payment"].cumsum()
df_year["Home Value"] = np.round((home_value * (1 + home_inflation) ** (df_year.index - 1)) * (1 - selling_fee), 2)
df_year["Net"] = df_year["Home Value"] - df_year["Ending Balance"] - df_year["Cumulative Payment"] - down_payment

keys = ["Rent", "Cumulative Rent", "Saving", "Asset", "Net"]
df_year_rent = pd.DataFrame(index=rng, columns=keys, dtype="float")
df_year_rent.reset_index(inplace=True)
df_year_rent.index += 1
df_year_rent.index.name = "Period"
df_year_rent["Rent"] = rent * 12
df_year_rent["Cumulative Rent"] = df_year_rent["Rent"].cumsum()
df_year_rent["Saving"] = saving * 12
df_year_rent["Asset"] = np.round(fv_annuity(stock_inflation, df_year_rent.index, saving * 12), 2)
df_year_rent["Net"] = df_year_rent["Asset"] - df_year_rent["Cumulative Rent"]

source = pd.DataFrame(np.array([df_year.loc[1:20, "Net"], df_year_rent.loc[1:20, "Net"]]).T,
                    columns=['Buy', 'Rent'], index=pd.RangeIndex(20, name='Year'))
source = source.reset_index().melt('Year', var_name='category', value_name='Net Balance ($)')

# Create a selection that chooses the nearest point & selects based on x-value
nearest = alt.selection(type='single', nearest=True, on='mouseover',
                        fields=['Year'], empty='none')

# The basic line
line = alt.Chart(source).mark_line(interpolate='basis', point=True).encode(
    x='Year:Q',
    y='Net Balance ($):Q',
    color='category:N'
)

# Transparent selectors across the chart. This is what tells us
# the x-value of the cursor
selectors = alt.Chart(source).mark_point().encode(
    x='Year:Q',
    opacity=alt.value(0),
).add_selection(
    nearest
)

# Draw points on the line, and highlight based on selection
points = line.mark_point().encode(
    opacity=alt.condition(nearest, alt.value(1), alt.value(0))
)

# Draw text labels near the points, and highlight based on selection
text = line.mark_text(align='right', dx=-10, dy=-10).encode(
    text=alt.condition(nearest, 'Net Balance ($):Q', alt.value(''))
)

# Draw a rule at the location of the selection
rules = alt.Chart(source).mark_rule(color='gray').encode(
    x='Year:Q',
).transform_filter(
    nearest
)

# Put the five layers into a chart and bind the data
c = alt.layer(
    line, selectors, points, rules, text
).properties(height=400)

with st.container():
    st.header("Net Balance over Years (Buy vs Rent)")
    st.altair_chart(c, use_container_width=True)
