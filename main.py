import os
import re
import time
import requests
from bs4 import BeautifulSoup
import logging
from colorama import Fore, Style, init
import shutil

# Initialisation de colorama
init(autoreset=True)

# Configuration du logging
logging.basicConfig(level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Récupération de la clé API Corcel depuis les variables d'environnement
CORCEL_KEY = os.environ.get('CORCEL_KEY')
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/91.0.4472.124 Safari/537.36",
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
        logging.error(f"Erreur lors de l'extraction du texte de {url}: {str(e)}")
        return ""

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'(Cookie|cookie|Accepter|Refuser|Paramètres des cookies).*', '', text)
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
            response = requests.post(url, json=payload, headers=HEADERS, timeout=60)
            response.raise_for_status()
            response_data = response.json()
            if isinstance(response_data, list) and response_data:
                first_item = response_data[0]
                if 'choices' in first_item and first_item['choices']:
                    choice = first_item['choices'][0]
                    if 'delta' in choice and 'content' in choice['delta']:
                        return choice['delta']['content']
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
    """
    Optimise une requête utilisateur en utilisant l'API Corcel pour une recherche Google experte.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "Vous êtes un expert en recherche Google avancée. Votre tâche est d'optimiser la requête de l'utilisateur "
                "en utilisant des techniques de recherche avancées pour obtenir les résultats les plus pertinents et précis. "
                "Appliquez les techniques suivantes de manière judicieuse :\\n"
                "1. Opérateurs booléens (AND, OR, NOT)\\n"
                "2. Opérateurs de recherche avancés (site:, filetype:, intitle:, inurl:, intext:, AROUND(n))\\n"
                "3. Guillemets pour les phrases exactes\\n"
                "4. Tiret (-) pour exclure des termes\\n"
                "5. Astérisque (*) pour les jokers\\n"
                "6. Parenthèses pour grouper les termes\\n"
                "La requête optimisée doit être directement utilisable dans Google et refléter une expertise réelle en recherche."
            )
        },
        {
            "role": "user",
            "content": (
                f"Optimisez cette requête pour une recherche Google experte : {user_query}\\n"
                "Utilisez les techniques de recherche avancées mentionnées ci-dessus pour améliorer la précision et la pertinence des résultats.\\n"
                "Fournissez uniquement la requête optimisée, sans explications supplémentaires.\\n"
                "TA SEULE et unique réponse à ma demande est la requête optimisée qui doit être concise, précise et directement utilisable dans Google et ne pas comporter trop de filtres."
            )
        }
    ]

    print(Fore.BLUE + "Étape 1 : Préparation des messages pour l'API Corcel.")

    optimized_query = call_corcel_api(messages)

    print(Fore.BLUE + "Étape 2 : Appel à l'API Corcel pour obtenir la requête optimisée.")

    if not optimized_query:
        print(Fore.RED + "Erreur : La réponse de l'API est vide.")
        return user_query

    print(Fore.BLUE + f"Étape 3 : Réponse de l'API reçue : {optimized_query}")

    return optimized_query

def summarize_page_with_corcel(text, expertise):
    messages = [{
        "role": "system",
        "content": f"Vous êtes expert et avez écrit le message suivant pour vous présenter : {expertise}."
    }, {
        "role": "user",
        "content": f"Veuillez faire une synthèse concise, professionnelle, bien formatée en markdown, sur base des informations suivantes : {text}"
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
        "role": "system",
        "content": "Vous êtes un assistant spécialisé dans la déduction de l'expertise la plus pertinente pour une requête donnée."
    }, {
        "role": "user",
        "content": f"Veuillez deviner l'expertise la plus pertinente pour la requête suivante : {query}. Vous devenez cet expert. Répondez en vous présentant vous et votre expertise de manière professionnelle et concise."
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
        "role": "user",
        "content": f"""
        Veuillez créer une méga-synthèse basée sur les sous-synthèses suivantes : {combined_summaries}. Utilisez uniquement les informations les plus pertinentes en fonction de la recherche initiale. Mentionnez les sources suivantes : {sources_text}.

        ### Instructions pour la Méga-Synthèse

        1. **Rédaction de Qualité** : La méga-synthèse doit être bien rédigée, comme le ferait un expert en copywriting.
        2. **Formatage en Markdown** : Utilisez le format Markdown pour structurer le document.
        3. **Utilisation d'Emojis** : Agrémentez le texte d'emojis appropriés pour rendre la lecture agréable et moderne.
        4. **Sections Numérotées** : Structurez le contenu avec des sections numérotées.
        5. **Introduction et Conclusion** : Ajoutez une introduction et une conclusion.
        6. **Références** : Les sources doivent être référencées à la fin du document.
        7. **Cohérence** : Assurez-vous que le fil rouge soit cohérent tout au long du document.

        ### Structure du Document

        #### Introduction
        - Présentez brièvement le sujet de la méga-synthèse.
        - Expliquez l'importance du sujet et pourquoi il est pertinent.

        #### Corps du Document
        - Divisez le contenu en sections claires et numérotées.
        - Chaque section doit traiter un aspect spécifique du sujet.
        - Utilisez des sous-titres pour organiser le contenu de chaque section.
        - Intégrez des exemples concrets et des données chiffrées si possible.
        - Ajoutez des emojis pour rendre la lecture plus dynamique et engageante.

        #### Conclusion
        - Résumez les points clés abordés dans la méga-synthèse.
        - Proposez des perspectives ou des recommandations pour l'avenir.
        - Concluez avec une note positive ou une réflexion finale.

        #### Références
        - Listez toutes les sources mentionnées de manière claire et ordonnée.
        - Utilisez un format de citation cohérent.

        En tant qu'expert du domaine, n'hésitez pas à améliorer le contenu et à être aussi exhaustif que possible. Le document doit être détaillé, informatif et concret.
        """
    }]
    return call_corcel_api(messages)

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def main():
    # Suppression des anciennes synthèses
    syntheses_dir = "outputs/syntheses"
    if os.path.exists(syntheses_dir):
        shutil.rmtree(syntheses_dir)
        print(Fore.YELLOW + "Anciennes synthèses supprimées.")
    os.makedirs(syntheses_dir, exist_ok=True)

    user_query = input("Veuillez entrer votre requête de recherche : ")
    num_pages = int(input("Combien de pages souhaitez-vous consulter ? (par défaut 5) : ") or 5)

    optimized_query = optimize_query_with_corcel(user_query) if get_user_confirmation(
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
        with open(f"{syntheses_dir}/synthese_{index + 1}.md", "w", encoding="utf-8") as file:
            file.write(summary)

    mega_synthesis = create_mega_synthesis_with_corcel(summaries, expertise, sources)
    sanitized_query = sanitize_filename(user_query)
    os.makedirs("outputs/mega_syntheses", exist_ok=True)
    with open(f"outputs/mega_syntheses/mega_synthese_{sanitized_query}.md", "w", encoding="utf-8") as file:
        file.write(mega_synthesis)

    print(Fore.GREEN + "Synthèse complète créée avec succès.")

if __name__ == "__main__":
    main()