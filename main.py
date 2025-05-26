import dash
from dash import html, dcc, Input, Output, State, ctx, dash_table, MATCH
import pandas as pd
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table
import os, base64, io, json

# Настройка базы данных
DB_PATH = "MyPaintings2.db"
DROPDOWN_FILE = 'dropdown_options.json'
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
metadata = MetaData()

def load_dropdown_data():
    if os.path.exists(DROPDOWN_FILE):
        with open(DROPDOWN_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {'genres': [], 'materials': [], 'movements': []}

dropdown_data = load_dropdown_data()

paintings_table = Table('paintings', metadata,
    Column('id', Integer, primary_key=True),
    Column('title', String),
    Column('artist', String),
    Column('year', String),
    Column('materials', String),
    Column('movement', String),
    Column('image_url', String),
    Column('genre', String),
    Column('country', String),
    Column('location', String),
    Column('description', String)
)

if not os.path.exists(DB_PATH):
    metadata.create_all(engine)

# Инициализация Dash
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CERULEAN], suppress_callback_exceptions=True)
server = app.server

# Сопоставление местоположений с координатами
LOCATION_COORDS = {
    "Государственная Третьяковская галерея, Москва": (55.741556, 37.620028),
    "Государственный Русский музей, Санкт-Петербург": (59.938782, 30.332383),
    "Гамбургский Кунстхалле, Гамбург": (53.561200, 9.995740),
    "Библиотека Маруселлиана, Флоренция": (43.767609, 11.262650),
}

# Главный layout
app.layout = html.Div([

    html.H1('Галерея картин', style={'textAlign': 'center', 'marginBottom': '30px', 'marginTop': '30px'}),

    dcc.Tabs(id="tabs", value='view', children=[
        dcc.Tab(label='Просмотр', value='view'),
        dcc.Tab(label='Редактирование', value='edit'),
    ]),
    html.Div(id='tabs-content')
])

# Функция для создания карточки с подробным описанием картины и картой
def create_painting_card_with_map(row, location_coords=None):
    label_style = {'color': '#0056b3', 'fontWeight': 'bold', 'marginRight': '10px'}

    card = dbc.Card(
        dbc.Row([
            dbc.Col(
                html.Img(src=row['image_url'], style={'width': '100%', 'borderRadius': '8px'}),
                md=4
            ),
            dbc.Col([
                html.H3(row['title'], className='card-title'),
                html.P([html.Span("Художник:", style=label_style), row['artist']]),
                html.P([html.Span("Год:", style=label_style), row['year']]),
                html.P([html.Span("Материалы:", style=label_style), row['materials']]),
                html.P([html.Span("Жанр:", style=label_style), row['genre']]),
                html.P([html.Span("Течение:", style=label_style), row['movement']]),
                html.P([html.Span("Страна:", style=label_style), row['country']]),
                html.P([html.Span("Описание:", style=label_style), row['description']]),
                html.P([html.Span("Местонахождение:", style=label_style), row['location']]),
            ], md=8)
        ]),
        style={'padding': '20px', 'marginTop': '20px', 'boxShadow': '0 0 12px rgba(0,0,0,0.1)'}
    )

    map_block = html.Div()
    if location_coords:
        lat, lon = location_coords
        map_block = html.Div([
            html.H5("Расположение на карте:"),
            dl.Map(center=(lat, lon), zoom=18, children=[
                dl.TileLayer(),
                dl.Marker(position=(lat, lon)),
                dl.Popup(children=row['location'])
            ], style={'width': '100%', 'height': '400px', 'marginTop': '10px'})
        ])

    return html.Div([card, map_block])

# Контент по вкладкам
@app.callback(Output('tabs-content', 'children'), Input('tabs', 'value'))
def render_tab(tab):
    if tab == 'view':
        df = pd.read_sql(paintings_table.select(), engine)
        return html.Div([
            html.Div([
                html.Img(src=row['image_url'], style={'height': '300px', 'cursor': 'pointer'},
                         id={'type': 'image', 'index': row['id']})
                for _, row in df.iterrows()
            ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '15px'}),
            html.Div(id='painting-detail', style={'marginTop': '20px'})
        ])
    elif tab == 'edit':
        # Вкладка редактирования
        df = pd.read_sql(paintings_table.select(), engine)
        return html.Div([

        html.H4('Редактирование картин', className='mb-4'),

        dbc.Accordion([
            dbc.AccordionItem([
                dbc.Row([
                    dbc.Col(dbc.Input(id='title', placeholder='Название', type='text'), md=4),
                    dbc.Col(dbc.Input(id='artist', placeholder='Художник', type='text'), md=4),
                    dbc.Col(dbc.Input(id='year', placeholder='Год', type='text'), md=4),
                ], className='mb-3'),

                dbc.Row([
                    
                    dbc.Col([
                        dcc.Dropdown(
                            id='materials',
                            options=[{'label': m, 'value': m} for m in dropdown_data['materials']],
                            placeholder='Выберите материалы',
                            multi=True
                        ),
                        dbc.Input(id='new_material', placeholder='Добавить новый материал', type='text', className='mt-2')
                    ]),
                    dbc.Col([
                        dcc.Dropdown(
                            id='movement',
                            options=[{'label': m, 'value': m} for m in dropdown_data['movements']],
                            placeholder='Течение'
                        ), 
                        dbc.Input(id='new_movement', placeholder='Добавить новое течение', type='text', className='mt-2')
                    ], md=4),
                    dbc.Col(dbc.Input(id='image_url', placeholder='URL изображения', type='text'), md=4),
                ], className='mb-3'),

                dbc.Row([
                    dbc.Col([
                        dcc.Dropdown(
                            id='genre',
                            options=[{'label': g, 'value': g} for g in dropdown_data['genres']],
                            placeholder='Жанр картины'
                        ),
                        dbc.Input(id='new_genre', placeholder='Добавить новый жанр', type='text', className='mt-2'),
                    ],),
                    dbc.Col(dbc.Input(id='country', placeholder='Страна картины', type='text'), md=4),
                    dbc.Col(dbc.Input(id='location', placeholder='Местонахождение', type='text'), md=4),
                ], className='mb-3'),

                dbc.Row([
                    dbc.Col(dbc.Textarea(id='description', placeholder='Описание картины', style={'height': '100px'}), md=12),
                ], className='mb-3'),

                dbc.Button([
                    html.I(className="fas fa-plus-circle me-2"),
                    "Добавить"
                ], id='add-btn', n_clicks=0, color='primary', className='mb-3'),
            ], title="Добавить новую картину")
        ], start_collapsed=True),

        html.Hr(),

        html.H5("Редактировать существующие картины", className='mt-4 mb-3'),

        dash_table.DataTable(
            id='edit-table',
            columns=[
                {'name': 'id', 'id': 'id', 'editable': False},
                {'name': 'Название', 'id': 'title', 'editable': True},
                {'name': 'Художник', 'id': 'artist', 'editable': True},
                {'name': 'Год', 'id': 'year', 'editable': True},
                {'name': 'Материалы', 'id': 'materials', 'editable': True},
                {'name': 'Течение', 'id': 'movement', 'editable': True},
                {'name': 'URL изображения', 'id': 'image_url', 'editable': True},
                {'name': 'Жанр', 'id': 'genre', 'editable': True},
                {'name': 'Страна', 'id': 'country', 'editable': True},
                {'name': 'Местонахождение', 'id': 'location', 'editable': True},
                {'name': 'Описание', 'id': 'description', 'editable': True},
            ],
            data=df.to_dict('records'),
            editable=True,
            row_deletable=True,
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'minWidth': '100px', 'whiteSpace': 'normal'}
        ),

        dbc.Button([
            html.I(className="fas fa-save me-2"),
            "Сохранить изменения"
        ], id='save-btn', n_clicks=0, color='success', className='mt-3'),
        html.Hr(),

        dbc.Button("Сохранить в CSV", id='save-csv-btn', n_clicks=0, className='me-2'),
        dcc.Download(id="download-csv"),

        dcc.Upload(
            id='upload-csv',
            children=dbc.Button("Загрузить CSV", color="secondary", className="me-2"),
            accept='.csv'
        ),
        html.Div(id='upload-status')

    ], className='p-4')


# Обработчик нажатия на картинку
@app.callback(
    Output('painting-detail', 'children'),
    Input({'type': 'image', 'index': dash.ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def show_details(n_clicks_list):
    triggered = ctx.triggered_id
    if not triggered:
        return ""
    painting_id = triggered['index']
    df = pd.read_sql(paintings_table.select().where(paintings_table.c.id == painting_id), engine)
    if df.empty:
        return ""
    row = df.iloc[0]
    location_coords = LOCATION_COORDS.get(row['location'])
    return create_painting_card_with_map(row, location_coords)

@app.callback(
    Output('edit-table', 'data', allow_duplicate=True),
    Input('add-btn', 'n_clicks'),
    State('title', 'value'),
    State('artist', 'value'),
    State('year', 'value'),
    State('materials', 'value'),
    State('movement', 'value'),
    State('image_url', 'value'),
    State('genre', 'value'),
    State('country', 'value'),
    State('location', 'value'),
    State('description', 'value'),
    State('new_material', 'value'),
    State('new_movement', 'value'),
    State('new_genre', 'value'),
    prevent_initial_call='initial_duplicate'
)
def add_painting(n_clicks, title, artist, year, materials, movement, image_url, genre, country, location, description,
                 new_material, new_movement, new_genre):

    # Загружаем dropdown_data из файла
    if os.path.exists('dropdown_options.json'):
        with open('dropdown_options.json', 'r', encoding='utf-8') as f:
            dropdown_data = json.load(f)
    else:
        dropdown_data = {'materials': [], 'movements': [], 'genres': []}

    # Используем новые значения, если они указаны
    genre = new_genre if new_genre else genre
    movement = new_movement if new_movement else movement
    materials = materials or []
    if new_material and new_material not in materials:
        materials.append(new_material)

    # Добавляем в списки, если новых значений ещё нет
    updated = False
    if genre and genre not in dropdown_data['genres']:
        dropdown_data['genres'].append(genre)
        updated = True
    if movement and movement not in dropdown_data['movements']:
        dropdown_data['movements'].append(movement)
        updated = True
    if materials and materials not in dropdown_data['materials']:
        dropdown_data['materials'].append(materials)
        updated = True

    # Сохраняем, если были изменения
    if updated:
        with open('dropdown_options.json', 'w', encoding='utf-8') as f:
            json.dump(dropdown_data, f, ensure_ascii=False, indent=4)

    # Если нет данных для картины — не добавляем, но возвращаем таблицу как есть
    if not all([title, artist, year, image_url]):
        df = pd.read_sql(paintings_table.select(), engine)
        return df.to_dict('records')

    # Добавляем запись
    ins = paintings_table.insert().values(
        title=title,
        artist=artist,
        year=year,
        materials=', '.join(materials) if materials else "",
        movement=movement or new_movement,
        image_url=image_url,
        genre=genre or new_genre,
        country=country,
        location=location,
        description=description
    )

    with engine.begin() as conn:
        conn.execute(ins)
        df = pd.read_sql(paintings_table.select(), conn)

    return df.to_dict('records')


# Сохранение редактированных данных
@app.callback(
    Output('edit-table', 'data', allow_duplicate=True),
    Input('save-btn', 'n_clicks'),
    State('edit-table', 'data'),
    prevent_initial_call='initial_duplicate'
)
def save_changes(n_clicks, rows):
    with engine.begin() as conn:
        conn.execute(paintings_table.delete())
        conn.execute(paintings_table.insert(), rows)
        df = pd.read_sql(paintings_table.select(), conn)
    return df.to_dict('records')

@app.callback(
    Output("download-csv", "data"),
    Input("save-csv-btn", "n_clicks"),
    State("edit-table", "data"),
    prevent_initial_call=True
)
def download_csv(n_clicks, data):
    if data:
        df = pd.DataFrame(data)
        return dcc.send_data_frame(df.to_csv, "paintings.csv", index=False)
    return dash.no_update

@app.callback(
    Output('edit-table', 'data', allow_duplicate=True),
    Output('upload-status', 'children'),
    Input('upload-csv', 'contents'),
    prevent_initial_call='initial_duplicate'
)
def upload_csv(contents):
    if contents:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        try:
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            with engine.begin() as conn:
                conn.execute(paintings_table.delete())
                conn.execute(paintings_table.insert(), df.to_dict(orient='records'))
            return df.to_dict('records'), "Файл успешно загружен."
        except Exception as e:
            return dash.no_update, f"Ошибка при загрузке файла: {e}"
    return dash.no_update, ""

if __name__ == '__main__':
    app.run(debug=True)
