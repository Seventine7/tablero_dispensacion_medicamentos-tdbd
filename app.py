import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, Input, Output, dash_table, callback
import dash_bootstrap_components as dbc
import sqlite3

# Cargar desde SQLite
conn = sqlite3.connect("medicamentos.db")  # Asegúrate de la ruta correcta si usas Drive
disp = pd.read_sql_query("SELECT * FROM dispensacion", conn)
conn.close()

# Preprocesamiento de datos
disp["fecha_entrega"] = pd.to_datetime(disp["fecha_entrega"], errors="coerce")
disp["mes_dt"] = disp["fecha_entrega"].dt.to_period("M").dt.to_timestamp()
disp["año"] = disp["fecha_entrega"].dt.year
disp["mes"] = disp["fecha_entrega"].dt.month

fecha_min = disp["fecha_entrega"].min()
fecha_max = disp["fecha_entrega"].max()

departamentos = sorted(disp["departamento_caf"].dropna().unique().tolist())
familias = sorted(disp["familia"].dropna().unique().tolist())
regionales = sorted(disp["regional_caf"].dropna().unique().tolist())
grupos_fco = sorted(disp["grupo_fco_economico"].dropna().unique().tolist())
anios = sorted(disp["año"].dropna().unique().tolist())
meses = sorted(disp["mes"].dropna().unique().tolist())

# Inicializar app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME])

# Layout con Pestañas (General, Detallado y Antidiabéticos)
app.layout = dbc.Container([
    html.H1("Dispensación de medicamentos", className="my-3"),

    dbc.Row([
        # Sidebar con Filtros
        dbc.Col([
            html.Div([
                html.Label("Rango de fechas"),
                dcc.DatePickerRange(
                    id="fecha_rango",
                    min_date_allowed=fecha_min,
                    max_date_allowed=fecha_max,
                    start_date=fecha_min,
                    end_date=fecha_max,
                    className="d-block mb-3",
                ),

                html.Label("Año de dispensación"),
                dcc.Dropdown(id="anio", options=[{"label": str(a), "value": a} for a in anios], value=[], multi=True, placeholder="Todos"),
                html.Br(),

                html.Label("Mes de dispensación"),
                dcc.Dropdown(id="mes_filtro", options=[{"label": str(m), "value": m} for m in meses], value=[], multi=True, placeholder="Todos"),
                html.Br(),

                html.Label("Regional CAF"),
                dcc.Dropdown(id="regional", options=[{"label": r, "value": r} for r in regionales], value=[], multi=True, placeholder="Todas"),
                html.Br(),

                html.Label("Departamento"),
                dcc.Dropdown(id="departamento", options=[{"label": d, "value": d} for d in departamentos], value=[], multi=True, placeholder="Todos"),
                html.Br(),

                html.Label("Familia farmacológica"),
                dcc.Dropdown(id="familia", options=[{"label": f, "value": f} for f in familias], value=[], multi=True, placeholder="Todas"),
                html.Br(),

                html.Label("Grupo farmacológico"),
                dcc.Dropdown(id="grupo_fco", options=[{"label": g, "value": g} for g in grupos_fco], value=[], multi=True, placeholder="Todos"),
                html.Br(),

                dbc.Button("Reset filter", id="reset", color="secondary", outline=True, className="w-100")
            ], className="p-3 bg-light border rounded")
        ], width=3),

        # Contenido
        dbc.Col([
            dbc.Tabs([
                # Pestaña: Resumen General
                dbc.Tab(label="Resumen General", tab_id="tab-1", children=[
                    html.Br(),
                    dbc.Row([
                        dbc.Col(dbc.Card(dbc.CardBody([
                            html.H5(html.I(className="fas fa-users me-2")), html.H6("Personas con dispensaciones"), html.H2(id="n_personas")
                        ]), color="primary", outline=True), width=4),
                        dbc.Col(dbc.Card(dbc.CardBody([
                            html.H5(html.I(className="fas fa-file-prescription me-2")), html.H6("Fórmulas distintas"), html.H2(id="n_formulas")
                        ]), color="info", outline=True), width=4),
                        dbc.Col(dbc.Card(dbc.CardBody([
                            html.H5(html.I(className="fas fa-dollar-sign me-2")), html.H6("Costo promedio por fórmula"), html.H2(id="costo_promedio")
                        ]), color="success", outline=True), width=4),
                    ], className="mb-3"),

                    dbc.Row([
                        dbc.Col(dbc.Card([
                            dbc.CardHeader("Dispensación de medicamentos en el tiempo"),
                            dbc.CardBody(dcc.Graph(id="grafico_tiempo"))
                        ]), width=12),
                    ], className="mb-3"),

                    dbc.Row([
                        dbc.Col(dbc.Card([
                            dbc.CardHeader("Top medicamentos"),
                            dbc.CardBody(html.Div(id="tabla_top_medicamentos"), style={"maxHeight": "400px", "overflowY": "auto"})
                        ]), width=6),
                        dbc.Col(dbc.Card([
                            dbc.CardHeader([
                                "Top 10 medicamentos",
                                dbc.Button(html.I(className="fas fa-ellipsis-v"), id="open_popover", color="link", size="sm", className="float-end"),
                                dbc.Popover([
                                    dbc.PopoverHeader("Ordenar por"),
                                    dbc.PopoverBody(dbc.RadioItems(
                                        id="top_metrica", options=[{"label": "Costo total", "value": "costo_total"}, {"label": "Cantidad dispensada", "value": "cantidad"}], value="costo_total", inline=True
                                    ))
                                ], target="open_popover", trigger="click", placement="top")
                            ]),
                            dbc.CardBody(dcc.Graph(id="grafico_top_medicamentos"))
                        ]), width=6),
                    ], className="mb-3"),
                ]),

                # Pestaña 2: Análisis Detallado
                dbc.Tab(label="Análisis Detallado", tab_id="tab-2", children=[
                    html.Br(),
                    dbc.Row([
                        dbc.Col(dbc.Card([
                            dbc.CardHeader("Costo según PBS / No PBS"),
                            dbc.CardBody(dcc.Graph(id="grafico_pbs"))
                        ]), width=6),
                        dbc.Col(dbc.Card([
                            dbc.CardHeader("Costo según Tipo de Entrega"),
                            dbc.CardBody(dcc.Graph(id="grafico_tipo_entrega"))
                        ]), width=6),
                    ], className="mb-3"),

                    dbc.Row([
                        dbc.Col(dbc.Card([
                            dbc.CardHeader("Costo por Municipio de Dispensación"),
                            dbc.CardBody(dcc.Graph(id="grafico_municipio"))
                        ]), width=12),
                    ]),
                ]),

                # Pestaña 3: Antidiabéticos
                dbc.Tab(label="Análisis Antidiabéticos", tab_id="tab-3", children=[
                    html.Br(),
                    dbc.Row([
                        dbc.Col(dbc.Card(dbc.CardBody([
                            html.H5(html.I(className="fas fa-file-invoice-dollar me-2")),
                            html.H6("Costo prom. por fórmula (Antidiabéticos)"),
                            html.H3(id="costo_prom_anti", className="text-warning")
                        ]), outline=True), width=6),
                        dbc.Col(dbc.Card(dbc.CardBody([
                            html.H5(html.I(className="fas fa-pills me-2")),
                            html.H6("Medicamento más costoso (Total facturado)"),
                            html.H4(id="med_top_anti", className="text-danger")
                        ]), outline=True), width=6),
                    ], className="mb-3"),

                    dbc.Row([
                        dbc.Col(dbc.Card([
                            dbc.CardHeader("Evolución del costo de Antidiabéticos en el tiempo"),
                            dbc.CardBody(dcc.Graph(id="grafico_tiempo_anti"))
                        ]), width=12),
                    ]),
                ])
            ], id="tabs", active_tab="tab-1")
        ], width=9)
    ])
], fluid=True)


# 5. Funciones auxiliares de filtrado
def filtrar(fecha_ini, fecha_fin, departamentos_sel, familias_sel, anios_sel, meses_sel, regionales_sel, grupos_sel):
    dff = disp
    if fecha_ini: dff = dff[dff["fecha_entrega"] >= pd.to_datetime(fecha_ini)]
    if fecha_fin: dff = dff[dff["fecha_entrega"] <= pd.to_datetime(fecha_fin)]
    if departamentos_sel: dff = dff[dff["departamento_caf"].isin(departamentos_sel)]
    if familias_sel: dff = dff[dff["familia"].isin(familias_sel)]
    if anios_sel: dff = dff[dff["año"].isin(anios_sel)]
    if meses_sel: dff = dff[dff["mes"].isin(meses_sel)]
    if regionales_sel: dff = dff[dff["regional_caf"].isin(regionales_sel)]
    if grupos_sel: dff = dff[dff["grupo_fco_economico"].isin(grupos_sel)]
    return dff

def filtrar_antidiabeticos(f_ini, f_fin, dep, anio, mes, reg):
    dff = disp[(disp["familia"] == "ANTIDIABETICOS") | (disp["grupo_fco_economico"] == "ANTIDIABETICOS")]
    if f_ini: dff = dff[dff["fecha_entrega"] >= pd.to_datetime(f_ini)]
    if f_fin: dff = dff[dff["fecha_entrega"] <= pd.to_datetime(f_fin)]
    if dep: dff = dff[dff["departamento_caf"].isin(dep)]
    if anio: dff = dff[dff["año"].isin(anio)]
    if mes: dff = dff[dff["mes"].isin(mes)]
    if reg: dff = dff[dff["regional_caf"].isin(reg)]
    return dff

filtros_inputs = [
    Input("fecha_rango", "start_date"), Input("fecha_rango", "end_date"),
    Input("departamento", "value"), Input("familia", "value"),
    Input("anio", "value"), Input("mes_filtro", "value"),
    Input("regional", "value"), Input("grupo_fco", "value")
]

filtros_anti_inputs = [
    Input("fecha_rango", "start_date"), Input("fecha_rango", "end_date"),
    Input("departamento", "value"), Input("anio", "value"),
    Input("mes_filtro", "value"), Input("regional", "value")
]

# 6. Callbacks Pestañas 1 y 2
@callback(Output("n_personas", "children"), filtros_inputs)
def actualizar_n_personas(f_ini, f_fin, dep, fam, anio, mes, reg, gfco):
    return f"{filtrar(f_ini, f_fin, dep, fam, anio, mes, reg, gfco)['id'].nunique():,}"

@callback(Output("n_formulas", "children"), filtros_inputs)
def actualizar_n_formulas(f_ini, f_fin, dep, fam, anio, mes, reg, gfco):
    return f"{filtrar(f_ini, f_fin, dep, fam, anio, mes, reg, gfco)['formula'].nunique():,}"

@callback(Output("costo_promedio", "children"), filtros_inputs)
def actualizar_costo_promedio(f_ini, f_fin, dep, fam, anio, mes, reg, gfco):
    dff = filtrar(f_ini, f_fin, dep, fam, anio, mes, reg, gfco)
    if dff["formula"].nunique() == 0: return "N/A"
    return f"${dff.groupby('formula')['costo_total'].sum().mean():,.0f}"

@callback(Output("grafico_tiempo", "figure"), filtros_inputs)
def actualizar_grafico_tiempo(f_ini, f_fin, dep, fam, anio, mes, reg, gfco):
    dff = filtrar(f_ini, f_fin, dep, fam, anio, mes, reg, gfco)
    serie = dff.groupby("mes_dt").agg(dispensaciones=("id", "count")).reset_index().sort_values("mes_dt")
    fig = px.line(serie, x="mes_dt", y="dispensaciones", markers=True, labels={"mes_dt": "Mes", "dispensaciones": "Número de dispensaciones"})
    fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))
    return fig

@callback(Output("tabla_top_medicamentos", "children"), Output("grafico_top_medicamentos", "figure"), filtros_inputs + [Input("top_metrica", "value")])
def actualizar_top_medicamentos(f_ini, f_fin, dep, fam, anio, mes, reg, gfco, top_metrica):
    dff = filtrar(f_ini, f_fin, dep, fam, anio, mes, reg, gfco)
    top = dff.groupby("descripcion").agg(costo_total=("costo_total", "sum"), cantidad=("cantidad", "sum")).sort_values(top_metrica, ascending=False).head(10).reset_index()
    tabla = dash_table.DataTable(data=top.to_dict("records"), columns=[{"name": "Medicamento", "id": "descripcion"}, {"name": "Costo total", "id": "costo_total", "type": "numeric", "format": {"specifier": ",.0f"}}, {"name": "Cantidad", "id": "cantidad", "type": "numeric"}], page_size=10, style_table={"overflowX": "auto"}, style_cell={"fontSize": 12, "whiteSpace": "normal", "height": "auto"})
    fig = px.bar(top.sort_values(top_metrica), x=top_metrica, y="descripcion", orientation="h", labels={"costo_total": "Costo total ($)", "cantidad": "Cantidad", "descripcion": ""})
    fig.update_layout(margin=dict(l=10, r=10, t=20, b=20), yaxis={"tickfont": {"size": 10}})
    return tabla, fig

@callback(Output("grafico_pbs", "figure"), filtros_inputs)
def actualizar_grafico_pbs(f_ini, f_fin, dep, fam, anio, mes, reg, gfco):
    dff = filtrar(f_ini, f_fin, dep, fam, anio, mes, reg, gfco)
    resumen = dff.groupby("pbs").agg(costo_total=("costo_total", "sum")).reset_index().sort_values("costo_total", ascending=False)
    fig = px.pie(resumen, values="costo_total", names="pbs", hole=0.4, labels={"pbs": "PBS", "costo_total": "Costo total"})
    fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))
    return fig

@callback(Output("grafico_tipo_entrega", "figure"), filtros_inputs)
def actualizar_grafico_tipo_entrega(f_ini, f_fin, dep, fam, anio, mes, reg, gfco):
    dff = filtrar(f_ini, f_fin, dep, fam, anio, mes, reg, gfco)
    resumen = dff.groupby("tipo_entrega").agg(costo_total=("costo_total", "sum")).reset_index().sort_values("costo_total", ascending=False)
    fig = px.pie(resumen, values="costo_total", names="tipo_entrega", hole=0.4, labels={"tipo_entrega": "Tipo Entrega", "costo_total": "Costo total"})
    fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))
    return fig

@callback(Output("grafico_municipio", "figure"), filtros_inputs)
def actualizar_grafico_municipio(f_ini, f_fin, dep, fam, anio, mes, reg, gfco):
    dff = filtrar(f_ini, f_fin, dep, fam, anio, mes, reg, gfco)
    resumen = dff.groupby("municipio_caf").agg(costo_total=("costo_total", "sum")).reset_index().sort_values("costo_total", ascending=True)
    fig = px.bar(resumen, x="costo_total", y="municipio_caf", orientation="h", labels={"municipio_caf": "Municipio CAF", "costo_total": "Costo total ($)"})
    fig.update_layout(margin=dict(l=10, r=10, t=20, b=20))
    return fig

# 7. Callbacks Pestaña 3 (Antidiabéticos)
@callback(Output("costo_prom_anti", "children"), filtros_anti_inputs)
def kpi_costo_anti(f_ini, f_fin, dep, anio, mes, reg):
    dff = filtrar_antidiabeticos(f_ini, f_fin, dep, anio, mes, reg)
    if dff["formula"].nunique() == 0: return "N/A"
    return f"${dff.groupby('formula')['costo_total'].sum().mean():,.0f}"

@callback(Output("med_top_anti", "children"), filtros_anti_inputs)
def kpi_top_med_anti(f_ini, f_fin, dep, anio, mes, reg):
    dff = filtrar_antidiabeticos(f_ini, f_fin, dep, anio, mes, reg)
    if dff.empty: return "N/A"
    med_top = dff.groupby("descripcion")["costo_total"].sum().idxmax()
    costo_top = dff.groupby("descripcion")["costo_total"].sum().max()
    return f"{med_top} (${costo_top:,.0f})"

@callback(Output("grafico_tiempo_anti", "figure"), filtros_anti_inputs)
def grafico_tendencia_anti(f_ini, f_fin, dep, anio, mes, reg):
    dff = filtrar_antidiabeticos(f_ini, f_fin, dep, anio, mes, reg)
    if dff.empty: return px.line(title="No hay datos disponibles")
    serie = dff.groupby("mes_dt").agg(costo_total=("costo_total", "sum")).reset_index().sort_values("mes_dt")
    fig = px.line(serie, x="mes_dt", y="costo_total", markers=True, labels={"mes_dt": "Mes", "costo_total": "Costo Total ($)"})
    fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))
    fig.update_traces(line_color="#ff7f0e")
    return fig

# Callback de Reset
@callback(
    Output("fecha_rango", "start_date"), Output("fecha_rango", "end_date"),
    Output("departamento", "value"), Output("familia", "value"),
    Output("anio", "value"), Output("mes_filtro", "value"),
    Output("regional", "value"), Output("grupo_fco", "value"),
    Input("reset", "n_clicks"), prevent_initial_call=True
)
def reset_filters(n):
    return fecha_min, fecha_max, [], [], [], [], [], []


if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0", port=8050)