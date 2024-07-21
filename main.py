import os
import re
import time
import requests
from bs4 import BeautifulSoup
import json
import logging

# Configuration du logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Récupération de la clé API Corcel depuis les variables d'environnement
CORCEL_KEY = os.environ['CORCEL_KEY']
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "accept": "application/json",
    "content-type": "application/json",
    "Authorization": f"Bearer {CORCEL_KEY}"
}

def google_search(query, num_results=5):
    logging.debug(f"Recherche Google pour la requête : {query}")
    url = f"https://www.google.com/search?q={query}&num={num_results}"
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')
    results = [result.find('a')['href'] for result in soup.find_all('div', class_='yuRUbf')]
    logging.debug(f"Résultats de recherche : {results}")
    return results

def extract_text(url, file_index):
    try:
        logging.debug(f"Extraction du texte de l'URL : {url}")
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        text = ' '.join(soup.stripped_strings)
        os.makedirs("extracted_texts", exist_ok=True)
        with open(f"extracted_texts/extracted_text_{file_index}.md", "w", encoding="utf-8") as file:
            file.write(text)
        logging.debug(f"Texte extrait et sauvegardé dans extracted_texts/extracted_text_{file_index}.md")
        return text
    except Exception as e:
        logging.error(f"Erreur lors de l'extraction du texte de {url}: {str(e)}")
        return ""

def clean_text(text):
    logging.debug("Nettoyage du texte")
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'(Cookie|cookie|Accepter|Refuser|Paramètres des cookies).*', '', text)
    cleaned_text = text.strip()
    logging.debug(f"Texte nettoyé : {cleaned_text}")
    return cleaned_text

def call_corcel_api(messages, retries=3, delay=10):
    url = "https://api.corcel.io/v1/text/cortext/chat"
    payload = {
        "model": "cortext-ultra",
        "stream": False,
        "top_p": 1,
        "temperature": 0.0001,
        "max_tokens": 4096,
        "messages": messages
    }
    for attempt in range(retries):
        try:
            logging.debug(f"Appel à l'API Corcel, tentative {attempt + 1}")
            response = requests.post(url, json=payload, headers=HEADERS, timeout=60)
            response.raise_for_status()
            response_data = response.json()
            logging.debug(f"Réponse de l'API Corcel : {json.dumps(response_data, indent=2)}")

            # Vérification de la structure de la réponse
            if isinstance(response_data, list) and len(response_data) > 0:
                first_item = response_data[0]
                if 'choices' in first_item and len(first_item['choices']) > 0:
                    choice = first_item['choices'][0]
                    if 'delta' in choice and 'content' in choice['delta']:
                        content = choice['delta']['content']
                        logging.debug(f"Contenu extrait : {content}")
                        return content

            logging.warning("La réponse de l'API ne contient pas le contenu attendu.")
            return str(response_data)

        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                logging.warning(f"Timeout, tentative {attempt + 1}/{retries}. Réessayer dans {delay} secondes...")
                time.sleep(delay)
            else:
                logging.error("Erreur : La requête a expiré après plusieurs tentatives. Veuillez réessayer plus tard.")
                return "Erreur : La requête a expiré après plusieurs tentatives. Veuillez réessayer plus tard."

        except requests.exceptions.RequestException as e:
            if response.status_code == 524:
                logging.error("Erreur 524 : Le serveur d'origine a mis trop de temps à répondre.")
                if attempt < retries - 1:
                    logging.warning(f"Tentative {attempt + 1}/{retries}. Réessayer dans {delay} secondes...")
                    time.sleep(delay)
                else:
                    logging.error("Erreur : Le serveur d'origine a mis trop de temps à répondre après plusieurs tentatives. Veuillez réessayer plus tard.")
                    return "Erreur : Le serveur d'origine a mis trop de temps à répondre après plusieurs tentatives. Veuillez réessayer plus tard."
            else:
                logging.error(f"Erreur lors de l'appel à l'API Corcel : {str(e)}")
                return f"Erreur lors de l'appel à l'API Corcel : {str(e)}"


def optimize_query_with_corcel(user_query):
    messages = [
        {"role": "system", "content": "Vous êtes un assistant spécialisé dans l'optimisation des requêtes de recherche pour obtenir des résultats pertinents."},
        {"role": "user", "content": f"Veuillez optimiser la requête suivante pour améliorer les résultats de recherche pertinents : {user_query}"}
    ]
    optimized_query = call_corcel_api(messages)
    match = re.search(r'\"(.*?)\"', optimized_query)
    optimized_query = match.group(1).strip() if match else optimized_query.strip()
    logging.debug(f"Requête optimisée : {optimized_query}")
    return optimized_query

def summarize_with_corcel(text, expertise):
    messages = [
        {"role": "system", "content": f"Vous êtes un assistant spécialisé dans la synthèse d'informations sur {expertise}."},
        {"role": "user", "content": f"Veuillez faire une synthèse concise et structurée des informations suivantes : {text}"}
    ]
    return call_corcel_api(messages)

def summarize_page_with_corcel(text, expertise):
    messages = [
        {"role": "system", "content": f"Vous êtes un assistant spécialisé dans la synthèse d'informations sur {expertise}."},
        {"role": "user", "content": f"Veuillez faire une synthèse concise en bullet points des informations suivantes : {text}"}
    ]
    return call_corcel_api(messages)

def get_user_confirmation():
    while True:
        confirmation = input("Souhaitez-vous optimiser votre requête de recherche ? (oui/non) : ").strip().lower()
        if confirmation in ['oui', 'non']:
            return confirmation == 'oui'
        print("Veuillez répondre par 'oui' ou 'non'.")

def guess_expertise_with_corcel(query):
    messages = [
        {"role": "system", "content": "Vous êtes un assistant spécialisé dans la déduction de l'expertise la plus pertinente pour une requête donnée."},
        {"role": "user", "content": f"Veuillez deviner l'expertise la plus pertinente pour la requête suivante : {query}"}
    ]
    expertise = call_corcel_api(messages).strip()
    logging.debug(f"Expertise devinée : {expertise}")
    return expertise

def main():
    user_query = input("Veuillez entrer votre requête de recherche : ")
    if get_user_confirmation():
        optimized_query = optimize_query_with_corcel(user_query)
        print(f"Requête optimisée : {optimized_query}")
    else:
        optimized_query = user_query

    expertise = guess_expertise_with_corcel(user_query)
    print(f"Expertise devinée : {expertise}")

    search_results = google_search(optimized_query)
    for index, url in enumerate(search_results):
        text = extract_text(url, index)
        cleaned_text = clean_text(text)
        summary = summarize_page_with_corcel(cleaned_text, expertise)
        with open(f"synthese{index + 1}.md", "w", encoding="utf-8") as file:
            file.write(summary)
        logging.debug(f"Synthèse sauvegardée dans synthese{index + 1}.md")

if __name__ == "__main__":
    main()