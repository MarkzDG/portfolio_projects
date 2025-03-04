import pandas as pd
import plotly.graph_objects as go

# Load data from GitHub
url = "https://raw.githubusercontent.com/lupalon/Mareas2022/main/3_MDAjo.xlsx"
mda = pd.read_excel(url)

# Create a datetime index with hourly frequency
fechi = pd.date_range(mda.FECHA.iloc[0], periods=len(mda), freq='1H')
mda.set_index(fechi, inplace=True)

# Extract observation series
serie = mda.OBS.values

# Create interactive plot
fig = go.Figure()
fig.add_trace(
    go.Scatter(x=mda.index, y=serie, mode='lines', name='Sea Level (cm)', line=dict(color='blue', width=1))
)

# Configure layout
fig.update_layout(
    title='Raw Sea Level Recording - Mar de Ajó (Jan-May 1986)',
    xaxis_title='Date',
    yaxis_title='Sea Level (cm)',
    xaxis=dict(tickformat='%b %Y', tickmode='auto', nticks=5),
    template='plotly_white',
    width=800,
    height=400
)

# Save as interactive HTML
fig.write_html("raw_sea_level_recording.html")

# Display locally (optional)
fig.show()