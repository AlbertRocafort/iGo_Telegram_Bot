import networkx as nx # Llibreria per manipular grafs
import osmnx as ox # Llibreria d'on descarregarem el mapa
import collections # Llibreria per fer tuples
import csv # Llibreria per llegir informació en format CSV
import pickle # Llibreria per llegir/escriure dades de/en fitxers
import urllib # Llibreria per descarregar fitxers de la web
import haversine # Llibreria per calcular distancies entre coordenades
import staticmap as sm # Llibreria per pintar mapes
import os.path # Llibreria per comprovar si ja tenim el graf descarregat
import sklearn # Llibreria per la funcio nearest_nodes
import math
import time




# Constants
PLACE = 'Barcelona, Catalonia'
GRAPH_FILENAME = 'barcelona.graph'
IGRAPH_FILENAME = 'barcelona_i.graph'
SIZE = 800
HIGHWAYS_URL = 'https://opendata-ajuntament.barcelona.cat/data/dataset/1090983a-1c40-4609-8620-14ad49aae3ab/resource/1d6c814c-70ef-4147-aa16-a49ddb952f72/download/transit_relacio_trams.csv'
CONGESTIONS_URL = 'https://opendata-ajuntament.barcelona.cat/data/dataset/8319c2b1-4c21-4962-9acd-6db4c5ff1148/resource/2d456eb5-4ea6-4f68-9794-2f3f1a58a933/download'

GENERIC_SPEED = 30
GENERIC_CONGESTION = 3

GREEN_STREETS = [1, 2]
ORANGE_STREETS = [3, 4]
RED_STREEETS = [5]

# Definicio de tuples
Highway = collections.namedtuple('Highway', 'description coordinates') # Tram
Congestion = collections.namedtuple('Congestion', 'state next_state')




##############################
##### Funcions Públiques #####
##############################


# Inicialitza les dades del sistema
def start_system():

    # Descarreguem / Carreguem el graf
    if not _exists_graph(GRAPH_FILENAME):
        graph = _download_graph(PLACE)
        save_graph(graph)


# Mostra la posició real de l'usuari
def show_position(lon, lat, image_name):

    _plot_position(lon, lat, SIZE, image_name)


# Desde la posició real o falsejada es retorna una imatge amb el cami mes curt fins el desti
def shortest_path(org, dest, image_name, use_colors, build_igraph):


    if build_igraph:
        #Obtenir graf, highways i congestions, crea igraph i guardarlo
        graph = _get_graph(GRAPH_FILENAME)
        highways = _get_highways()
        congestions = _get_congestions()
        _build_igraph(graph, highways, congestions)
        _save_graph(graph, IGRAPH_FILENAME)

    else:
        graph = _get_graph(IGRAPH_FILENAME)

    # Busquem els nodes origen i desti
    org_node = ox.distance.nearest_nodes(graph, org[0], org[1])
    dest_node = ox.distance.nearest_nodes(graph, dest[0], dest[1])

    # Buscar cami més curt
    ipath = _get_shortest_ipath(graph, org_node, dest_node)

    if ipath == None: return -1

    # Guarda la imatge
    _plot_path(graph, ipath, SIZE, image_name, use_colors)
    return 1


# Tradueix una direccio de string a coordenades
def translate_direction(direction):

    return ox.geocoder.geocode(direction)


###################################################################
##### Funcions Privades per Obtencio de Dades de l'Ajuntament #####
###################################################################


# Descarrega archiu CSV de internet
def _download_csv(url):

    with urllib.request.urlopen(url) as response:
        lines = [l.decode('utf-8') for l in response.readlines()]
        reader = csv.reader(lines, delimiter=',', quotechar='"')
        next(reader)  # ignore first line with description
        
        return reader


# Retorna una llista amb tots els Highways
def _get_highways():
    
    # Llegim els Highways de la URL
    csv_reader = _download_csv(HIGHWAYS_URL)

    # Diccionari per emmagatzemar els highways
    highways = {}

    # Iterem per tot el reader
    for line in csv_reader:

        # Guardem la info al diccionari
        way_id, description, coordinates = line
        highways[int(way_id)] = Highway(description, list(map(float, coordinates.split(','))))


    return highways


# Retorna una llista amb tots els Congestions
def _get_congestions():
    
    csv_reader = _download_csv(CONGESTIONS_URL)

    congestions = {}

    # Iterem per tot el reader
    # (O(len(csv_reader)) < 550)
    for line in csv_reader:

        # Guardem la info al diccionari
        way_id, data_hour, state, next_state = str(line)[2:-2].split('#')
        congestions[int(way_id)] = Congestion(int(state), int(next_state))

    return congestions




####################################################
##### Funcions Privades per Gestiona els Grafs #####
####################################################


# Retorna si existeix un graf amb nom "filename"
def _exists_graph(filename):
    
    return os.path.exists(filename)


# Descarrega el graf del lloc indicat i el retorna
def _download_graph(place):

    # Descarreguem el multidigraf graf i el convertim en un digraf
    multigraph = ox.graph_from_place(place, network_type='drive', simplify=True)
    digraph = ox.utils_graph.get_digraph(multigraph, weight='length')


    # Es monta el igraph amb les arestes de graph que tenen 'length' i 'maxspeed'
    for node1 in digraph.nodes:

        # for each adjacent node and its information...
        for node2 in digraph.adj[node1]:

            # Agafem les dades que ens interesen de l'aresta
            speed = digraph[node1][node2].get('maxspeed', None)
            length = digraph[node1][node2].get('length', None)


            if type(speed) == list:
                speed = sum(list(map(float, speed))) / len(speed)

            # Vigilem amb les vies que no tenen la velocitat assignada
            if speed == None:
                digraph[node1][node2]['maxspeed'] = GENERIC_SPEED
                speed = GENERIC_SPEED


            time = float(length) / float(speed)
            digraph[node1][node2]['time'] = time
            digraph[node1][node2]['congestion'] = GENERIC_CONGESTION
            digraph[node1][node2]['itime'] = _calculate_itime(time, GENERIC_CONGESTION)
    
    return digraph


# Guarda el graph en el pickle
def _save_graph(graph, filename):
    with open(filename, 'wb') as file:
        pickle.dump(graph, file)


# Agafa el graf que ja tenim guardat al pickle
def _load_graph(filename):
    with open(filename, 'rb') as file:
        return pickle.load(file)


# Carrega / Descarrega el graf i el guarda en un PNG
def _get_graph(filename):

    if not _exists_graph(filename):
        graph = _download_graph(PLACE)
        _save_graph(graph, filename)
    else:
        graph = _load_graph(filename)

    return graph




#################################################
##### Funcions Privades per Generar Imatges #####
#################################################


# Genera una imatge amb un Marker en la posicio indicada
def _plot_position(lon, lat, size, image_name):

    # Creem el mapa
    m_bcn = sm.StaticMap(size, size)

    # Posem el marcador en la possicio indicada
    marker = sm.CircleMarker((lon, lat), 'red', 50)
    m_bcn.add_marker(marker)

    # Guardem la imatge
    image = m_bcn.render()
    image.save(image_name)


# Genera una imatge amb un path marcat
def _plot_path(graph, path, size, image_name, use_colors):

    # Creem el mapa
    m_bcn = sm.StaticMap(size, size)

    first = True

    #Per cada segment
    for node in path:

        # Afegim un marker en el punt inicial
        if first:
            lon = graph.nodes[node]['x']
            lat = graph.nodes[node]['y']
            start_marker = sm.CircleMarker((lon, lat), 'red', 12)
            m_bcn.add_marker(start_marker)

            first = False


        # Pintem cada aresta de la ruta
        else:

            lon0 = graph.nodes[ant]['x']
            lat0 = graph.nodes[ant]['y']
            lon1 = graph.nodes[node]['x']
            lat1 = graph.nodes[node]['y']

            if not use_colors: color = 'red'
            elif graph[ant][node]['congestion'] in GREEN_STREETS: color = 'green'
            elif graph[ant][node]['congestion'] in ORANGE_STREETS: color = 'orange'
            else: color = 'red'

            m_bcn.add_line(sm.Line(((float(lon0), float(lat0)), (float(lon1), float(lat1))), color, 4)) #Pintem la linia

        ant = node


    # Possem una bandereta en el punt final
    lon = graph.nodes[path[-1]]['x']
    lat = graph.nodes[path[-1]]['y']
    finish_marker = sm.CircleMarker((lon, lat), 'red', 12)
    m_bcn.add_marker(finish_marker)

    image = m_bcn.render()
    image.save(image_name)




###########################################################
##### Funcions Privades per Calcular el cami mes Curt #####
###########################################################


# Retorna la versió "inteligent" del graf de la ciutat.
def _build_igraph(graph, highways, congestions):

    # Per cada via de la que tenim info de la congestio
    for key in congestions:

        # Si tenim els segments de la via
        if key in highways.keys():

            # Coordenades dels segments
            lon_list = highways[key].coordinates[::2]   # Llista de longituds
            lat_list = highways[key].coordinates[1::2]  # Llista de latituds

            # Nodes mes propers als extrems dels segments
            nodes_list = ox.distance.nearest_nodes(graph, lon_list, lat_list)

            # Els separem en nodes d'origen i de desti:
            org_node_list = nodes_list[0:-1]
            dest_node_list = nodes_list[1:]

            # Propaguem la congestio del highway a tots els segments
            congestion = congestions[key].state
            _congestion_propagation(graph, org_node_list, dest_node_list, congestion)


# Retorna el cami "inteligent" entre dos adresses
def _get_shortest_ipath(graph, org, dest):
    try:
        return ox.distance.shortest_path(graph, org, dest, weight = 'itime')
    except:
        return None


# Propaga la congestio d'un tram al graph d'OSMnx
def _congestion_propagation(graph, org_nodes, dest_nodes, congestion):

    # Busquem el cami mes curt entre node1 i node2
    # list_of_paths = ox.distance.shortest_path(graph, org_nodes, dest_nodes)

    list_of_paths = []
    for i in range(len(org_nodes)):

        try:
            path = ox.distance.shortest_path(graph, org_nodes[i], dest_nodes[i])
            list_of_paths.append(path)
        except:
            pass

    # Iterem per tots els paths generats
    for path in list_of_paths:

        #Iterem per cada node
        first = True
        for node2 in path:

            if first:
                first = False

            else:
                # Mirem que no haguem eliminat l'aresta en una iteracio anterior
                if node2 in graph.adj[node1]:

                    # itime en funcio de la congestio
                    graph[node1][node2]['congestion'] = congestion
                    itime = _calculate_itime(graph[node1][node2]['time'], congestion)
                    
                    # Mirem si hem d'esborrar l'aresta o no
                    if itime == -1: graph.remove_edge(node1, node2)
                    else: graph[node1][node2]['itime'] = itime

            node1 = node2


# Calcula el itime a partir de un temps i una congestio
def _calculate_itime(time, congestion):

    # Via tallada
    if congestion == 6:
        return -1

    # Via sense informacio
    if congestion == 0:
        congestion = GENERIC_CONGESTION

    return time * math.sqrt(congestion)




#########################################
##### Funcions Auxiliars de Testeig #####
#########################################


# Mostra el graf per pantalla
def _plot_graph(graph, image_name):

    ox.plot_graph(graph, show=False, save=True, filepath=image_name)


# Mostra els highways en un PNG
def _plot_highways(highways, image_name, size):

    # Creem el mapa
    m_bcn = sm.StaticMap(2000, 2000)

    #Per cada segment
    for key in highways:

        # Aixo es només per no haver d'escriure "highways[key].coordinates" tota l'estona
        coords = highways[key].coordinates

        # Per cada parell lon-lat de coordenades
        for i in range(2, len(coords), 2):
            # Pintem la linia del Highway
            m_bcn.add_line(sm.Line(((coords[i-2], coords[i-1]), (coords[i], coords[i+1])), 'red', 3))


    image = m_bcn.render()
    image.save(image_name)


# Mostra la congestio en un PNG
def _plot_congestions(highways, congestions, image_name, size):

    # Creem el mapa
    m_bcn = sm.StaticMap(size, size)

    #Per cada segment
    for key in highways:

        # Agafem la congestio de la via. Si no existeix retorna None
        congestion = congestions.get(key, None)

        # No ens sortim de la llista i hi ha info de la via i de la congestio
        if congestion is not None:

            if congestion.state == 0:
                color = 'black'
            elif congestion.state == 1:
                color = 'green'
            elif congestion.state == 2:
                color = 'green'
            elif congestion.state == 3:
                color = 'orange'
            elif congestion.state == 4:
                color = 'orange'
            elif congestion.state == 5:
                color = 'orange'
            else:
                color = 'red'


            coords = highways[key].coordinates
            for i in range(2, len(coords), 2):
                # Pintem la linia del Highway
                m_bcn.add_line(sm.Line(((coords[i-2], coords[i-1]), (coords[i], coords[i+1])), color, 3))

    image = m_bcn.render()
    image.save(image_name)


# Mostra un tram sencer en un PNG
# No te control d'errors
def _plot_one_highway(highways, tram, size):

    m_bcn = sm.StaticMap(size, size)

    # Canviem el nom per escriure-ho mes facil
    coords = highways[tram].coordinates

    # Per cada parell lon-lat de coordenades
    for i in range(2, len(coords), 2):
        # Pintem la linia del Highway
        m_bcn.add_line(sm.Line(((coords[i-2], coords[i-1]), (coords[i], coords[i+1])), 'red', 3))

    image = m_bcn.render()
    image.save('tram.png')


# Mostra el primer segment de un tram en PNG
# No te control d'errors
def _plot_first_segment(highways, tram, size):

    m_bcn = sm.StaticMap(size, size)
    m_bcn.add_line(sm.Line(((float(highways[tram].coordinates[0]), float(highways[tram].coordinates[1])), (float(highways[tram].coordinates[2]), float(highways[tram].coordinates[3]))), 'red', 3))

    image = m_bcn.render()
    image.save('segment.png')
