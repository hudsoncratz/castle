import requests
import schedule
import re
import os
import random
from bs4 import BeautifulSoup
import telebot
import time
from datetime import datetime, timedelta
import pytz

# --- Configurações ---
url = "https://shop.ticket-center-hohenschwangau.de/Shop/PerformResUpdate2/de-DE/39901"
cookie_sessao = f"ASP.NET_SessionId=COLOQUE_SEU_COOKIE_AQUI{random.randrange(5,50000)}"
telegram_token = os.environ["API_TOKEN"]
chat_id = os.environ["CHAT_ID"]

# Fuso horário da Alemanha (CET/CEST)
timezone = pytz.timezone("Europe/Berlin")

headers = {
    "Content-Type": "application/json",
    "Origin": "https://shop.ticket-center-hohenschwangau.de",
    "Referer": "https://shop.ticket-center-hohenschwangau.de/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Cookie": cookie_sessao
}
# Iniciar uma sessão de requisições para manter os cookies
session = requests.Session()

# Realiza uma requisição GET para a página de onde o cookie será extraído
response = session.get(url)


def enviar_telegram(mensagem: str):
    bot = telebot.TeleBot(token=telegram_token)
    bot.send_message(chat_id=chat_id, text=mensagem)

def calcular_data_ammanha():
    # Obter a data de amanhã
    hoje = datetime.today()
    amanha = hoje + timedelta(days=1)
    return amanha.strftime('%d.%m.%Y')  # Retorna a data no formato "DD.MM.YYYY"

def calcular_data_hoje():
    # Obter a data de amanhã
    hoje = datetime.today()
    return hoje.strftime('%d.%m.%Y')  # Retorna a data no formato "DD.MM.YYYY"

def verificar_disponibilidade(data_selecionada: str):
    payload = {
        "dtStartDate": data_selecionada,
        "dtSelectedDate": data_selecionada,
        "nPoolNr": "30",
        "nTicketTypeNr": "44",
        "nDays": 0,
        "nPlaces": 4,
        "bReservation": "true",
        "PersonSelection": [
            {"nPersonTypeNr": "1", "nCount": "4"}
        ],
        "SelectedSubContigents": []
    }
    try:
        resp = requests.post(url, headers=headers, json=payload)
        # ✅ Obter a data e hora atual no fuso horário da Alemanha
        hora_execucao = datetime.now().astimezone(timezone).strftime('%d.%m.%Y %H:%M')
        str_hora_execucao = f"🚨 Executado em: {hora_execucao}"
        if resp.status_code != 200:
            enviar_telegram(f"⚠️ Erro HTTP {resp.status_code} na requisição! \n\n{str_hora_execucao}")
            return

        data = resp.json()
        html = data.get("szContent", "")

        # Parse do HTML
        soup = BeautifulSoup(html, "html.parser")

        # ✅ Extrair a data do campo <span id="dtInfo">
        data_selecionada = soup.select_one("#dtInfo")
        data_selecionada = data_selecionada.text.strip() if data_selecionada else "Data não encontrada"

        # ✅ Extrair horários e tipos de tour
        horarios = []
        for label in soup.select("label.txt.txt-sm"):
            hora_tag = label.select_one("span.time")
            descricao_tag = label.select_one("small")  # A descrição pode estar em <small> (para Audio Guide, etc.)
            idioma_tag = label.find("span", style="color:inherit;background-color:inherit")

            if hora_tag:
                horario = hora_tag.text.strip()
                descricao = descricao_tag.text.strip() if descricao_tag else ""
                idioma = idioma_tag.text.strip() if idioma_tag else ""

                # Se a descrição estiver vazia, usa o idioma, se o idioma também estiver vazio, usa "Não especificado"
                tipo_tour = descricao if descricao else (idioma if idioma else "Não especificado")

                horarios.append({
                    "hora": horario,
                    "tipo_tour": tipo_tour
                })

            # ✅ Monta mensagem formatada
        if horarios:
            horarios_str = "\n".join([f"🕒 {h['hora']} - {h['tipo_tour']}" for h in horarios])
            mensagem = f"📅 Data: {data_selecionada}\n✅ Horários disponíveis:\n{horarios_str} \n\n{str_hora_execucao}"
        else:
            mensagem = f"📅 Data: {data_selecionada}\n❌ Nenhum horário disponível no momento. \n\n{str_hora_execucao}"

        enviar_telegram(mensagem)


    except Exception as e:
        enviar_telegram(f"⚠️ Erro: {e}")

# --- Função que verifica o intervalo e define o tempo de espera ---
def agendar_verificacao(datas: list[str]) -> None:
    for data in datas:
        # Verifica o horário atual
        schedule.every().hour.at(":00").do(verificar_disponibilidade, data)
        # Rodar de 6h às 9h a cada 30 minutos
        for hora in range(1, 3):
            schedule.every().day.at(f"0{hora}:30").do(verificar_disponibilidade, data)

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
# --- Inicia o processo ---
    datas = [
        calcular_data_hoje(),
        calcular_data_ammanha(),
        '22.08.2025',
        '23.08.2025',
        '24.08.2025'
    ]
    for data in datas:
        verificar_disponibilidade(data)