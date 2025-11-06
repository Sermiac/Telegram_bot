import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import re
from dotenv import load_dotenv
# --- Mantener el bot activo en Render ---
from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is alive and running!", 200

def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    def run():
        app.run(host='0.0.0.0', port=port)
    Thread(target=run).start()
# --- Fin del bloque ---

# needs a config.env with the data
load_dotenv("config.env")
bot_token = os.getenv("BOT_TOKEN")
sheet1_url = os.getenv("SHEET1_URL")
sheet2_url = os.getenv("SHEET2_URL")
group_id = os.getenv("GROUP_ID")

if load_dotenv("config.env") == False:
    exit()


TOKEN = bot_token

# === Configuración de Google Sheets ===
# Activa la API de Google Sheets en https://console.cloud.google.com/
# Crea una credencial de "Cuenta de servicio" y descarga el JSON
CREDENTIALS_FILE = "credenciales.json"
SPREADSHEET_NAME = "CorporationPricesReestructuration"  # Nombre de tu Google Sheets

# Inicializar conexión a Google Sheets
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
print("Cliente autenticado OK")

# Abrimos la primera hoja

try:
    hoja1 = client.open_by_url(sheet1_url).sheet1
    print("Hoja 1 abierta ok")
except Exception as e:
    print("Error detallado", e)

try:
    hoja2 = client.open_by_url(sheet2_url).get_worksheet(1)
    print("Hoja 2 abierta ok")
except Exception as e:
    print("Error detallado", e)

# Diccionario global para saber qué usuarios están en modo /precios
usuarios_modo_precios = {}
usuarios_modo_cuentas = {}
cantidad_temp = {}
producto_temp = {}  # Para guardar temporalmente el producto ingresado
PRODUCTOS = "Lista: Camisetas, Mugs normales, Mugs metaliza, Camisetas Doble, Camiseta doble N, Camiseta negra, Camiseta niño, Lamina metali Peq, Chapa mascota, Cédula, Mugs color, Caramañola Gran, Mug Opalizado, Agenda, Mameluco"
GRUPO_ID = int(group_id)




async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Desactivamos el modo precios si el usuario vuelve a /start
    usuarios_modo_precios.pop(user_id, None)
    usuarios_modo_cuentas.pop(user_id, None)
    await update.message.reply_text("👋 Hola, soy el bot que maneja las cuentas de GrafiCalamar")
    (print(update.message.chat_id))
    

# ----------------------------
# FUNCIONES DEL BOT
# ----------------------------

async def manejar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if usuarios_modo_cuentas.get(user_id):
        print(f"[DEBUG] Usuario {user_id} está en modo /cuentas")
        await procesar_cantidad(update, context)
    elif usuarios_modo_precios.get(user_id):
        print(f"[DEBUG] Usuario {user_id} está en modo /precios")
        await buscar_producto(update, context)
    else:
        print(f"[DEBUG] Usuario {user_id} no está en ningún modo")
        await update.message.reply_text("❌ Use /precios o /cuentas para cambiar de modo.")


async def precios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    usuarios_modo_precios[user_id] = True  # Activamos modo menú para este usuario
    usuarios_modo_cuentas.pop(user_id, None)

    await update.message.reply_text("Escriba el nombre del producto")
    await update.message.reply_text(PRODUCTOS)


async def buscar_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    query = update.message.text.strip().lower()

    # Obtiene todas las filas
    data = hoja1.get_all_values()

    # La fila 9 son los precios (según me dijiste)
    precios = data[8]   # fila 9 → índice 8
    productos = []

    # Buscar en columnas C hasta R (índices 2 hasta 17)
    for col in range(2, 18):
        for fila in range(1, 8):  # desde fila 2
            nombre = data[fila][col].strip().lower() if len(data[fila]) > col else ""
            if query in nombre and nombre != "":
                productos.append((data[fila][col], precios[col]))

    if productos:
        respuesta = "📦 Resultados encontrados:\n"
        for nombre, precio in productos:
            respuesta += f"- {nombre}: {precio}\n"
    else:
        respuesta = f"❌ El producto: {query} no se encontró en la base de datos, intentelo de nuevo"

    await update.message.reply_text(respuesta)


async def cuentas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    usuarios_modo_cuentas[user_id] = True  # Activamos modo cuentas
    usuarios_modo_cuentas[user_id] = "esperando_producto"  # Estado inicial
    await update.message.reply_text("Escriba el nombre del producto")


async def procesar_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    estado = usuarios_modo_cuentas.get(user_id)

    if not estado:
        await update.message.reply_text("❌ Primero use /cuentas para iniciar.")
        return

    texto = update.message.text.strip()


    # ----------------------
    # Paso 1: producto
    # ----------------------
    if estado == "esperando_producto":
        global nombre
        query = texto.lower()
        data = hoja1.get_all_values()
        encontrado = False

        for col in range(2, 18):
            for fila in range(1, 8):
                nombre = data[fila][col].strip().lower() if len(data[fila]) > col else ""
                if query in nombre and nombre != "":
                    encontrado = True
                    celda_producto = f"{num_a_col(col)}{fila + 1}"  # columna + fila en formato A1
                    producto_temp[user_id] = (nombre, celda_producto)
                    
                    # Accedemos a las celdas +3 y +7
                    valor_fila_mas3 = data[fila+3][col] if len(data) > fila+3 and len(data[fila+3]) > col else ""
                    valor_fila_mas7 = data[fila+7][col] if len(data) > fila+7 and len(data[fila+7]) > col else ""

                    col_letra = num_a_col(col)
                    fila_num = fila + 1  # índice base 0 → fila en Sheets

                    # Link a hoja1: fila +3
                    formula1 = f"=Precios!{col_letra}{fila_num + 3}"
                    hoja2.update_acell("A3", formula1)

                    # Link a hoja1: fila +7
                    formula2 = f"=Precios!{col_letra}{fila_num + 7}"
                    hoja2.update_acell("B3", formula2)


                    break
            if encontrado:
                break

        if not encontrado:
            await update.message.reply_text(f"❌ No encontré el producto '{texto}'. Inténtelo de nuevo.")
            return

        usuarios_modo_cuentas[user_id] = "esperando_cantidad"
        nombre, celda_producto = producto_temp[user_id]
        await update.message.reply_text(
            f"✅ Producto encontrado: *{nombre}*\n Si no es. Porfavor, vuelva al menu o escriba /cuentas",
            parse_mode="Markdown"
        )

        await update.message.reply_text("¿Cuántos productos pidió el cliente?")
        return

    # ----------------------
    # Paso 2: cantidad
    # ----------------------
    if estado == "esperando_cantidad":
        if not texto.isdigit():
            await update.message.reply_text("❌ Por favor ingrese un número válido.")
            return

        cantidad = int(texto)
        cantidad_temp[user_id] = cantidad
        hoja2.update("C3", [[cantidad]])

        # Mostramos D2/D3 y E2/E3
        try:
            nombre_d2 = hoja2.acell("D2").value
            precio_d3 = hoja2.acell("D3").value
            nombre_e2 = hoja2.acell("E2").value
            precio_e3 = hoja2.acell("E3").value
            
            
        except Exception as e:
            await update.message.reply_text(f"Error al leer la hoja: {e}")
            return
            

        respuesta = (
            f"{nombre_d2} = {precio_d3}\n"
            f"{nombre_e2} = {precio_e3}\n"
        )
        await update.message.reply_text(respuesta)
    
    
        # Pasamos al estado de contraseña
        usuarios_modo_cuentas[user_id] = "esperando_contraseña"
        await update.message.reply_text("🔑 Ingrese la contraseña para guardar datos TOTALES")
        return

    # ----------------------
    # Paso 3: contraseña
    # ----------------------
    if estado == "esperando_contraseña":
        if texto != "1234":
            await update.message.reply_text("❌ Contraseña incorrecta. Intente de nuevo con /cuentas.")
            usuarios_modo_cuentas.pop(user_id, None)
            return
        #valores insumos y liquidez
        insumos_antes = hoja2.acell("H3").value
        liquidez_antes = hoja2.acell("H7").value
        
        # Copiamos valores
        valor_j3 = hoja2.acell("J3").value
        valor_j7 = hoja2.acell("J7").value
        valor_h3 = hoja2.acell("H3").value
        valor_h7 = hoja2.acell("H7").value
        
        #   J3 → L3 y J7 → L7
        hoja2.update("L3", [[valor_j3]])
        hoja2.update("L7", [[valor_j7]])
        
        #actualización de datos para copiado y calcular el total
        valor_l3 = hoja2.acell("L3").value
        valor_l7 = hoja2.acell("L7").value
        
        #para el total de las cuentas de Telegram
        insumos_despues = hoja2.acell("J3").value
        liquidez_despues = hoja2.acell("J7").value
        
        hoja2.update("H3", [[valor_l3]])
        hoja2.update("H7", [[valor_l7]])
        


        await update.message.reply_text("✅ Datos guardados correctamente"
            "\n"
            f"Insumos antes = {insumos_antes}\n"
            f"Liquidez antes = {liquidez_antes}\n"
            "\n"
            f"Insumos despues = {insumos_despues}\n"
            f"Liquidez despues = {liquidez_despues}")
            
            
        #datos
        total_productos = hoja2.acell("E3").value
        subtotal_productos = hoja2.acell("D3").value
            
        #convertir a solo numeros
        total_solo_numeros = re.sub(r"[^0-9.]", "", total_productos)
        subtotal_solo_numeros = re.sub(r"[^0-9.]", "", subtotal_productos)
            
        #cantidad de productos
        numero_de_productos = hoja2.acell("C3").value
            
        #operaciones matematicas
        total_resultado = float(total_solo_numeros) / float(numero_de_productos)
        la_liquidez = float(liquidez_despues) / 1000
        los_insumos = float(insumos_despues) / 1000
            
        await context.bot.send_message(
            chat_id=GRUPO_ID,
            text=f"Entradas:\n\n+{total_solo_numeros}\n  +{total_resultado:.0f}.000 x{numero_de_productos} {nombre}\n\n+{subtotal_solo_numeros} insumos\n\n{la_liquidez:.3f} ({los_insumos:.3f} de insumos)"
           )
        usuarios_modo_cuentas.pop(user_id, None)  # reiniciamos estado
        return

# Función para convertir número de columna a letra
def num_a_col(n):
    return chr(ord('A') + n)

# ----------------------------
# MAIN DEL BOT
# ----------------------------
def main():

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("cuentas", cuentas))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("precios", precios))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_texto))

    print("🤖 Bot corriendo...")
    app.run_polling(drop_pending_updates=True, poll_interval=10.0, timeout=120)

if __name__ == "__main__":
    keep_alive()
    main()