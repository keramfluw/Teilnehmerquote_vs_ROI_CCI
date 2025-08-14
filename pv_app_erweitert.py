
import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt

st.set_page_config(page_title="PV-Projekt-Kalkulation", layout="wide")

st.title("☀️ PV-Projekt-Kalkulation Dashboard V1.0 Qrauts AG")

# Eingabemaske
st.sidebar.header("🔧 Eingabeparameter")

# Technisch-wirtschaftliche Parameter
size_kwp = st.sidebar.number_input("Anlagengröße (kWp)", min_value=1.0, value=100.0)
yield_kwh_kwp = st.sidebar.number_input("Spezifischer Ertrag (kWh/kWp)", min_value=500.0, value=950.0)
self_consumption_rate = st.sidebar.slider("Eigenverbrauchsanteil (%)", 0, 100, 60)
system_efficiency = st.sidebar.slider("Systemnutzungsgrad (%)", 50, 100, 90)
lifetime_years = st.sidebar.slider("Lebensdauer der Anlage (Jahre)", 10, 30, 25)

# Investitionskosten
capex_pv = st.sidebar.number_input("PV-Anlage (€)", min_value=0.0, value=100000.0)
capex_storage = st.sidebar.number_input("Speicher (€)", min_value=0.0, value=20000.0)
capex_other = st.sidebar.number_input("Weitere Kosten (€)", min_value=0.0, value=30000.0)
capex_total = capex_pv + capex_storage + capex_other

# Betriebskosten
opex_annual = st.sidebar.number_input("Jährliche Betriebskosten (€)", min_value=0.0, value=5000.0)

# Finanzierung
loan_share = st.sidebar.slider("Fremdkapitalanteil (%)", 0, 100, 70)
interest_rate = st.sidebar.slider("Kreditzins (%)", 0.0, 10.0, 3.0)
repayment_years = st.sidebar.slider("Tilgungsdauer (Jahre)", 1, 30, 20)

# Einnahmen
price_self_consumption = st.sidebar.number_input("Mieterstromerlös (ct/kWh)", min_value=0.0, value=25.0) / 100
price_feed_in = st.sidebar.number_input("Einspeisevergütung (ct/kWh)", min_value=0.0, value=8.0) / 100
inflation_rate = st.sidebar.slider("Strompreissteigerung (%)", 0.0, 10.0, 2.0) / 100

# Szenarien
scenarios = {
    "Bundesdurchschnitt": 1.0,
    "Optimistisch": 1.1,
    "Pessimistisch": 0.9
}

# Berechnung
def calculate_cashflow(scenario_factor):
    annual_production = size_kwp * yield_kwh_kwp * system_efficiency / 100 * scenario_factor
    self_consumed = annual_production * self_consumption_rate / 100
    fed_into_grid = annual_production - self_consumed

    cashflows = []
    cumulative = []
    for year in range(1, lifetime_years + 1):
        price_self = price_self_consumption * ((1 + inflation_rate) ** (year - 1))
        price_feed = price_feed_in * ((1 + inflation_rate) ** (year - 1))
        revenue = self_consumed * price_self + fed_into_grid * price_feed
        cost = opex_annual
        net_cashflow = revenue - cost
        cashflows.append(net_cashflow)
        cumulative.append(sum(cashflows))

    return cashflows, cumulative

# Dashboard
st.subheader("📊 Szenarienvergleich: Cashflow & Break-even")

fig, ax = plt.subplots(figsize=(10, 5))
for name, factor in scenarios.items():
    cf, cum_cf = calculate_cashflow(factor)
    ax.plot(range(1, lifetime_years + 1), cum_cf, label=name)
    for i, val in enumerate(cum_cf):
        if val >= capex_total:
            ax.axvline(i + 1, linestyle='--', color='gray', alpha=0.3)
            break

ax.axhline(capex_total, color='red', linestyle=':', label='Investitionskosten')
ax.set_xlabel("Jahr")
ax.set_ylabel("Kumulierter Cashflow (€)")
ax.set_title("Cashflow-Verlauf und Break-even")
ax.legend()
st.pyplot(fig)

# KPI-Dashboard
st.subheader("📈 Projekt-Kennzahlen")

base_cf, base_cum = calculate_cashflow(1.0)
amort_year = next((i + 1 for i, val in enumerate(base_cum) if val >= capex_total), "nicht erreicht")
irr_estimate = npf.irr([-capex_total] + base_cf)
lcoe = capex_total / (size_kwp * yield_kwh_kwp * system_efficiency / 100 * lifetime_years)

col1, col2, col3 = st.columns(3)
col1.metric("Amortisationsjahr", amort_year)
col2.metric("geschätzte IRR-Interne Rendite", f"{irr_estimate:.2%}" if irr_estimate else "n/a")
col3.metric("LCOE-Stromgestehungskosten (€/kWh)", f"{lcoe:.4f}")

st.caption("Hinweis: Die Berechnungen basieren auf vereinfachten Annahmen und dienen der Projektbewertung. Autor:Marek Wulff")



# Neue Analyse: Strompreis in Abhängigkeit von Nutzerquote

st.header("📊 Analyse: Strompreis abhängig von PV-Nutzerquote")

min_quote = 10
max_quote = 100
step = 10
quotes = np.arange(min_quote, max_quote + 1, step)

# Jahresstromertrag (netto)
annual_yield_total = size_kwp * yield_kwh_kwp * (system_efficiency / 100)

# Speicherbare Fixkosten pro Jahr
loan_amount = capex_total * (loan_share / 100)
equity_amount = capex_total - loan_amount
annuity = npf.pmt(interest_rate / 100, repayment_years, -loan_amount)
total_annual_costs = annuity + opex_annual

# Simulation
effective_prices = []
profits = []

for quote in quotes:
    user_share = quote / 100
    pv_for_users = annual_yield_total * (self_consumption_rate / 100) * user_share
    pv_feed_in = annual_yield_total - pv_for_users

    revenue_users = pv_for_users * price_self_consumption
    revenue_feed_in = pv_feed_in * price_feed_in
    total_revenue = revenue_users + revenue_feed_in

    profit = total_revenue - total_annual_costs

    if pv_for_users > 0:
        price_per_kwh = (total_annual_costs - revenue_feed_in) / pv_for_users
    else:
        price_per_kwh = np.nan

    effective_prices.append(price_per_kwh)
    profits.append(profit)

# Plotting
fig1, ax1 = plt.subplots()
ax1.plot(quotes, np.array(effective_prices)*100, marker="o", label="Effektiver Mieterstrompreis (ct/kWh)")
for x, y in zip(quotes, np.array(effective_prices)*100):
    ax1.annotate(f"{y:.1f}", (x, y), textcoords="offset points", xytext=(0, 5), ha='center', fontsize=8)
ax1.set_xlabel("PV-Nutzerquote (%)")
ax1.set_ylabel("Preis (ct/kWh)")
ax1.set_title("Effektiver Mieterstrompreis je nach Nutzerquote")
ax1.grid(True)
ax1.legend()
st.pyplot(fig1)

fig2, ax2 = plt.subplots()
ax2.plot(quotes, profits, marker="s", color="green", label="Jährlicher Gewinn (€)")
for x, y in zip(quotes, profits):
    ax2.annotate(f"{y:.0f}", (x, y), textcoords="offset points", xytext=(0, 5), ha='center', fontsize=8)
ax2.set_xlabel("PV-Nutzerquote (%)")
ax2.set_ylabel("Jährlicher Gewinn (€)")
ax2.set_title("Wirtschaftlichkeit der PV-Anlage je nach Nutzerquote")
ax2.grid(True)
ax2.legend()
st.pyplot(fig2)
