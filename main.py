import os
import re
import time
import requests
from bs4 import BeautifulSoup
import logging
from colorama import Fore, Style, init

# Initialisation de colorama
init(autoreset=True)

# Configuration du logging
logging.basicConfig(level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Récupération de la clé API Corcel depuis les variables d'environnement
CORCEL_KEY = os.environ.get('CORCEL_KEY')
HEADERS = {
    "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "accept": "application/json",
    "content-type": "application/json",
    "Authorization": f"Bearer {CORCEL_KEY}"
}


def google_search(query, num_results=5):
    print(Fore.CYAN + "Recherche Google pour la requête...")
    url = f"https://www.google.com/search?q={query}&num={num_results}"
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')
    return [
        result.find('a')['href']
        for result in soup.find_all('div', class_='yuRUbf')
    ]


def extract_text(url):
    try:
        print(Fore.GREEN + f"Extraction du texte de l'URL : {url}")
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        text = ' '.join(soup.stripped_strings)
        return text
    except Exception as e:
        logging.error(
            f"Erreur lors de l'extraction du texte de {url}: {str(e)}")
        return ""


def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'(Cookie|cookie|Accepter|Refuser|Paramètres des cookies).*',
                  '', text)
    return text.strip()


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
            response = requests.post(url,
                                     json=payload,
                                     headers=HEADERS,
                                     timeout=60)
            response.raise_for_status()
            response_data = response.json()
            if isinstance(response_data, list) and response_data:
                first_item = response_data[0]
                if 'choices' in first_item and first_item['choices']:
                    choice = first_item['choices'][0]
                    if 'delta' in choice and 'content' in choice['delta']:
                        return choice['delta']['content']
            logging.warning(
                "La réponse de l'API ne contient pas le contenu attendu.")
            return str(response_data)
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                logging.warning(
                    f"Timeout, tentative {attempt + 1}/{retries}. Réessayer dans {delay} secondes..."
                )
                time.sleep(delay)
            else:
                logging.error(
                    "Erreur : La requête a expiré après plusieurs tentatives. Veuillez réessayer plus tard."
                )
                return "Erreur : La requête a expiré après plusieurs tentatives. Veuillez réessayer plus tard."
        except requests.exceptions.RequestException as e:
            if response.status_code == 524:
                logging.error(
                    "Erreur 524 : Le serveur d'origine a mis trop de temps à répondre."
                )
                if attempt < retries - 1:
                    logging.warning(
                        f"Tentative {attempt + 1}/{retries}. Réessayer dans {delay} secondes..."
                    )
                    time.sleep(delay)
                else:
                    logging.error(
                        "Erreur : Le serveur d'origine a mis trop de temps à répondre après plusieurs tentatives. Veuillez réessayer plus tard."
                    )
                    return "Erreur : Le serveur d'origine a mis trop de temps à répondre après plusieurs tentatives. Veuillez réessayer plus tard."
            else:
                logging.error(
                    f"Erreur lors de l'appel à l'API Corcel : {str(e)}")
                return f"Erreur lors de l'appel à l'API Corcel : {str(e)}"


def optimize_query_with_corcel(user_query):
    """
    Optimise une requête utilisateur en utilisant l'API Corcel.
    """
    # Préparation des messages pour l'API Corcel
    messages = [
        {
            "role": "system",
            "content": (
                "Vous êtes un expert en recherche Google. Utilisez des opérateurs de recherche avancés "
                "pour optimiser la requête suivante. L'output doit être tel qu'entré directement dans le moteur de recherche. "
                "Utilisez des opérateurs comme \"site:\", \"filetype:\", \"intitle:\", \"inurl:\", et des guillemets pour des phrases exactes."
            )
        },
        {
            "role": "user",
            "content": (
                f"Veuillez optimiser la requête suivante pour améliorer les résultats de recherche pertinents : {user_query}. "
                "Utilisez des opérateurs de recherche avancés pour affiner les résultats. "
                "L'output doit être prêt à être utilisé directement dans le moteur de recherche."
            )
        }
    ]

    print(Fore.BLUE + "Étape 1 : Préparation des messages pour l'API Corcel.")

    # Appel à l'API Corcel pour obtenir la requête optimisée
    optimized_query = call_corcel_api(messages)

    print(Fore.BLUE + "Étape 2 : Appel à l'API Corcel pour obtenir la requête optimisée.")

    # Vérification et nettoyage de la réponse
    if not optimized_query:
        print(Fore.RED + "Erreur : La réponse de l'API est vide.")
        return user_query

    print(Fore.BLUE + f"Étape 3 : Réponse de l'API reçue : {optimized_query}")

    # Extraction du contenu entre guillemets si présent
    match = re.search(r'\"(.*?)\"', optimized_query)
    if match:
        optimized_query = match.group(1).strip()
    else:
        optimized_query = optimized_query.strip()

    print(Fore.BLUE + f"Étape 4 : Extraction et nettoyage de la réponse : {optimized_query}")

    # Suppression des mots inutiles
    optimized_query = re.sub(
        r'\b(et|ou|le|la|les|un|une|des|de|du|dans|avec|pour|par|sur|sous|à|au|aux|en|chez|vers|contre|entre|sans|sous)\b',
        '', optimized_query)
    optimized_query = re.sub(r'\s+', ' ', optimized_query).strip()

    print(Fore.BLUE + f"Étape 5 : Suppression des mots inutiles : {optimized_query}")

    # Vérification si l'optimisation a réellement changé quelque chose
    if optimized_query.lower() == user_query.lower():
        print(Fore.YELLOW + "Aucune optimisation significative n'a été apportée à la requête.")
    else:
        print(Fore.YELLOW + f"Requête optimisée : {optimized_query}")

    return optimized_query


def summarize_with_corcel(text, expertise):
    messages = [{
        "role":
        "system",
        "content":
        f"Vous êtes un assistant spécialisé dans la synthèse d'informations sur {expertise}."
    }, {
        "role":
        "user",
        "content":
        f"Veuillez faire une synthèse concise et structurée des informations suivantes : {text}"
    }]
    return call_corcel_api(messages)


def summarize_page_with_corcel(text, expertise):
    messages = [{
        "role":
        "system",
        "content":
        f"Vous êtes un assistant spécialisé dans la synthèse d'informations sur {expertise}."
    }, {
        "role":
        "user",
        "content":
        f"Veuillez faire une synthèse concise, professionnelle, bien formatée en markdown, sur base des informations suivantes : {text}"
    }]
    return call_corcel_api(messages)


def get_user_confirmation(prompt):
    while True:
        confirmation = input(prompt).strip().lower()
        if confirmation in ['oui', 'non']:
            return confirmation == 'oui'
        print("Veuillez répondre par 'oui' ou 'non'.")


def guess_expertise_with_corcel(query):
    messages = [{
        "role":
        "system",
        "content":
        "Vous êtes un assistant spécialisé dans la déduction de l'expertise la plus pertinente pour une requête donnée."
    }, {
        "role":
        "user",
        "content":
        f"Veuillez deviner l'expertise la plus pertinente pour la requête suivante : {query}. Vous devenez cet expert. Répondez en vous présentant vous et votre expertise de manière professionnelle et concise."
    }]
    expertise = call_corcel_api(messages).strip()
    print(Fore.MAGENTA + f"Expertise devinée : {expertise}")
    return expertise


def create_mega_synthesis_with_corcel(summaries, expertise, sources):
    combined_summaries = "\n\n".join(summaries)
    sources_text = "\n".join(f"- {source}" for source in sources)
    messages = [{
        "role": "system",
        "content": f"Vous agissez tel que : {expertise}."
    }, {
        "role":
        "user",
        "content":
        f"Veuillez créer une méga-synthèse basée sur les sous-synthèses suivantes : {combined_summaries}. N'exploitez que les informations vraiment utile compte tenu de la recherche initiale. Mentionnez les sources suivantes : {sources_text}. La méga-synthèse doit être bien rédigée, tel un expert en copywriting, et formatée en markdown, avec l'un ou l'autre emoji pour rendre la lecture agréable et moderne. Ajoutez une introduction et une conclusion. Les sources doivent être référencées à la fin. Le fil rouge doit être cohérent. En tant qu'expert du domaine, n'hésitez pas à améliorer. Il faut que cela soit informatif et concret."
    }]
    return call_corcel_api(messages)


def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)


def main():
    user_query = input("Veuillez entrer votre requête de recherche : ")
    num_pages = int(
        input("Combien de pages souhaitez-vous consulter ? (par défaut 5) : ")
        or 5)
    optimized_query = optimize_query_with_corcel(
        user_query
    ) if get_user_confirmation(
        "Souhaitez-vous optimiser votre requête de recherche ? (oui/non) : "
    ) else user_query
    expertise = guess_expertise_with_corcel(user_query)
    search_results = google_search(optimized_query, num_results=num_pages)
    summaries, sources = [], []

    for index, url in enumerate(search_results[:num_pages]):
        text = extract_text(url)
        cleaned_text = clean_text(text)
        summary = summarize_page_with_corcel(cleaned_text, expertise)
        summaries.append(summary)
        sources.append(url)
        os.makedirs("outputs/syntheses", exist_ok=True)
        with open(f"outputs/syntheses/synthese_{index + 1}.md",
                  "w",
                  encoding="utf-8") as file:
            file.write(summary)

    mega_synthesis = create_mega_synthesis_with_corcel(summaries, expertise,
                                                       sources)
    sanitized_query = sanitize_filename(user_query)
    os.makedirs("outputs/mega_syntheses", exist_ok=True)
    with open(f"outputs/mega_syntheses/mega_synthese_{sanitized_query}.md",
              "w",
              encoding="utf-8") as file:
        file.write(mega_synthesis)

    print(
        Fore.BLUE +
        "La méga-synthèse a été créée avec succès. Vous pouvez la consulter dans le dossier 'outputs/mega_syntheses'."
    )


if __name__ == "__main__":
    main()
