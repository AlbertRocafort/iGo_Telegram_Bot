from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import igo
import time



# Declara una constant amb el access token que llegeix de token.txt
TOKEN = open('token.txt').read().strip()


# Nom de les imatges
POSITION_IMAGE = 'my_position.png'
PATH_IMAGE = 'shortest_path.png'


# Crea objectes per treballar amb Telegram
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher



# Funcions del bot

# Descarrega el graf si no ho esta
def start(update, context):

	# Inicialitzem el modul iGo
	igo.start_system()

	# Al inici utilitzarem sempre la ubicacio real
	context.user_data['use_real_position'] = True
	context.user_data['real_position'] = -1
	context.user_data['false_position'] = -1
	context.user_data['color_path'] = False
	context.user_data['last_congestion_refresh'] = None

	########################################################################################################################
	context.user_data['last_time_refresh'] = -1
	########################################################################################################################


	# Missatge que es mostrara
	message = "Hola! Sóc el bot iGo!"

	# Mostrem elm missatge
	context.bot.send_message(
		chat_id=update.effective_chat.id,
		text=message)



# Mostra les comandes que es poden executar
def help(update, context):

	# Missatge que es mostrara
	message = '''Aquí tens un llistat de les comandes que pots utilitzar:

		/start:		Inicialitza el bot.
		/help:		Mostra les comandes que es poden executar.
		/author:	Mostra l'autor d'aquest bot.
		/go desti:	Mostra una imatge amb el camí més ràpid desde l'ubicació actual fins el destí indicat
		/where:		Mostra una imatge amb la teva posició actual.
		/pos:		Falsejar la teva possicio
		/unpos:		Utilitzar la posició real
		/color:		Mostrar colors segons la congestio de la via en la comanda /go
		/uncolor:	Mostrar tota la ruta de la comanda /go del mateix color
	'''

	# Mostrem elm missatge
	context.bot.send_message(
		chat_id=update.effective_chat.id,
		text=message)



# Mostra l'autor del bot
def author(update, context):
	
	# Missatge que es mostrara
	message = "Bot creat per Albert Rocafort. 05/2021"

	# Mostrem elm missatge
	context.bot.send_message(
		chat_id=update.effective_chat.id,
		text=message)



# Mostra una imatge amb el cami mes rapid desde la ubicacio actual de l'usuari fins el desti indicat
# La ubicacio de origen tambe pot ser falsejada amb la comanda /pos
def go(update, context):

	# Agafem el desti que ens demanen del text del missatge i el passem a coordenades
	
	try:
		dest_lat, dest_lon = _get_coords_from_message(update, context, 2)

		# Ubicacio real com origen
		if context.user_data['use_real_position'] == True:

			# No tenim cap ubicacio guardada
			if context.user_data['real_position'] == -1: result = 0	
			
			# Agafem la ubicacio que tenim guardada
			else:
				color = context.user_data['color_path']
				org_lat, org_lon = context.user_data['real_position']

				build_igraph = _need_to_build_igraph(context)

				result = igo.shortest_path((org_lon, org_lat), (dest_lon, dest_lat), PATH_IMAGE, color, build_igraph)


		# Ubicacio falsejada com origen
		else:
			color = context.user_data['color_path']
			org_lat, org_lon = context.user_data['false_position']

			build_igraph = _need_to_build_igraph(context)

			result = igo.shortest_path((org_lon, org_lat), (dest_lon, dest_lat), PATH_IMAGE, color, build_igraph)


		# Es decideix que ha de mostrar el bot en funcio del resultat obtingut anteriorment
		if result == 1:		# S'ha trobat un cami correctament
			context.bot.send_photo(
			chat_id=update.effective_chat.id,
			photo=open(PATH_IMAGE, 'rb'))

		elif result == 0:	# No hi ha una ubicacio guardada
			context.bot.send_message(
				chat_id=update.effective_chat.id,
				text="Envia'm la teva localització o indica'n alguna amb la comanda /pos!")

		elif result == -1:	# No s'ha pogut trobar un cami
			context.bot.send_message(
				chat_id=update.effective_chat.id,
				text="No s'ha pogut trobar un cami entre l'origen i destí indicats")

	except:
		context.bot.send_message(
			chat_id=update.effective_chat.id,
			text="No s'ha pogut trobar el desti demanat")


# Si l'usuari ha falsejat la seva ubicacio, la mostra
# Si l'usuari vol utilitzar la ubicacio real, demana que s'envii la ubicacio
def where(update, context):

	print(context.user_data['use_real_position'])


	if context.user_data['use_real_position'] == True:	# Hem de mostrar la ubicacio real

		if context.user_data['real_position'] == -1:	# No hi ha una ubicacio guardada
			context.bot.send_message(
			chat_id=update.effective_chat.id,
			text="Envia'm la teva localització o indica'n alguna amb la comanda /pos!")

		else:	# Agafem la ubicacio que tenim guardada
			lat, lon = context.user_data['real_position']
			igo.show_position(lon, lat, POSITION_IMAGE)
			context.bot.send_photo(
				chat_id=update.effective_chat.id,
				photo=open(POSITION_IMAGE, 'rb'))

	else:	# Hem de mostrar la ubicacio falsa
		lat, lon = context.user_data['false_position']
		igo.show_position(lon, lat, POSITION_IMAGE)

		context.bot.send_photo(
			chat_id=update.effective_chat.id,
			photo=open(POSITION_IMAGE, 'rb'))
		
	


# Mostra la ubicacio real de l'usuari quan aquest envia la seva ubicacio
def get_position(update, context):

	# Codi per guardar la ubicacio a temps real
	message = update.edited_message if update.edited_message else update.message

	# Guardem la posicio que se'ns ha enviat en user_data
	lat, lon = update.message.location.latitude, update.message.location.longitude
	context.user_data['real_position'] = (lat, lon)



# Falseja la posicio
def pos(update, context):

	# Obtenim les coordenades de la ubicacio indicada en el missatge
	try:
		lat, lon = _get_coords_from_message(update, context, 3)
	
		# Guardem la posicio en user_data
		context.user_data['use_real_position'] = False
		context.user_data['false_position'] = (lat, lon)

	except:
		context.bot.send_message(
			chat_id=update.effective_chat.id,
			text="No s'ha pogut trobar la posicio demanada")



# Es deixa de falsejar la posicio
def unpos(update, context):
	
    context.user_data['use_real_position'] = True



# Falseja la posicio
def color(update, context):

	# Activem l'us de colors alhora de mostrar la ruta
	context.user_data['color_path'] = True



# Falseja la posicio
def uncolor(update, context):

	# Activem l'us de colors alhora de mostrar la ruta
	context.user_data['color_path'] = False





def _get_coords_from_message(update, context, comand_size):

	# Format string
	if update.message.text[comand_size+2] < '0' or update.message.text[comand_size+2] > '9':
		direction = update.message.text[comand_size+2:]
		return igo.translate_direction(direction)

	# Format coordenades 
	else:
		lat = context.args[0]
		lon = context.args[1]
		return (float(lat), float(lon))


def _need_to_build_igraph(context):

	t1 = context.user_data['last_congestion_refresh']
	t2 = time.time()

	if t1 == None or t2 - t1 > 300:
		context.user_data['last_congestion_refresh'] = t2
		return True

	return False


# Indica que quan el bot rebi la comanda s'executi la funció
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('help', help))
dispatcher.add_handler(CommandHandler('author', author))
dispatcher.add_handler(CommandHandler('go', go))
dispatcher.add_handler(CommandHandler('where', where))
dispatcher.add_handler(MessageHandler(Filters.location, get_position))
dispatcher.add_handler(CommandHandler('pos', pos))
dispatcher.add_handler(CommandHandler('unpos', unpos))
dispatcher.add_handler(CommandHandler('color', color))
dispatcher.add_handler(CommandHandler('uncolor', uncolor))







# Engega el bot
updater.start_polling()