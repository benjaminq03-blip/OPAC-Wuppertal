from bs4 import BeautifulSoup
import requests
import streamlit as st
import re

st.set_page_config(
    page_title="Wuppertal OPAC Suche", page_icon="📚", layout="centered"
)

st.title("📚 Smarte Wuppertal OPAC-Suche")
st.write(
    "Direkt gekoppelt an den WebOPAC der Stadtbibliothek Wuppertal!"
)

query = st.text_input(
    "Buchtitel, Autor oder ISBN eingeben:", placeholder="z. B. Das Sams, Astrid Lindgren oder 978..."
)

def smart_typo_correction(text):
    text_lower = text.strip().lower()
    corrections = {
        "das sans": "Das Sams",
        "wanze muldon": "Die Wanze",
        "wanze muldun": "Die Wanze",
        "astrid lingren": "Astrid Lindgren",
        "michael ende": "Michael Ende",
    }
    if text_lower in corrections:
        corrected = corrections[text_lower]
        st.info(f"💡 Meintest du **'{corrected}'**? (Automatisch korrigiert)")
        return corrected
    return text

if st.button("Suchen"):
  if query:
    clean_query = re.sub(r'[^0-9X]', '', query.upper())
    is_isbn = len(clean_query) == 10 or len(clean_query) == 13
    
    if is_isbn:
        search_query = clean_query
        st.caption(f"🔍 ISBN-Suche erkannt für: {search_query}")
    else:
        search_query = smart_typo_correction(query)

    with st.spinner("Trickse das OPAC-System aus..."):
      session = requests.Session()
      
      headers = {
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
      }

      try:
        # Wir nutzen einen GET-Request mit den exakten Sisis-Parametern für die Schnellsuche
        search_url = "https://webopac.wuppertal.de/webOPACClient/search.do"
        params = {
            "methodToCall": "submit",
            "searchCategories[0]": "-1",  # -1 steht im Sisis-System oft für "Alle Felder"
            "searchString[0]": search_query,
            "submitSearch": "Suchen",
            "callingPage": "searchPreferences"
        }
        
        # Direkter Aufruf der Such-URL (Deep-Link Methode)
        response = session.get(search_url, params=params, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")

        # Wir suchen gezielt nach Zeilen, die Treffer enthalten
        rows = soup.find_all("tr")
        results = []

        for row in rows:
          # Viele Bibliotheks-Kataloge nutzen 'odd' oder 'even' Klassen für die Tabellenzeilen
          if "odd" in row.get("class", []) or "even" in row.get("class", []) or row.find("td"):
              cols = row.find_all("td")
              if cols:
                row_text = " | ".join([c.get_text(strip=True) for c in cols if c.get_text(strip=True)])
                if len(row_text) > 15 and "Suche" not in row_text and "Treffer" not in row_text:
                  results.append(row_text)

        if results:
          st.success(f"{len(results)} Einträge gefunden:")
          for idx, res in enumerate(results[:15], 1):
            lower_res = res.lower()
            
            if "entliehen" in lower_res or "ausgeliehen" in lower_res:
              status = "🔴 Entliehen"
            elif "verfügbar" in lower_res or "frei" in lower_res or "im regal" in lower_res:
              status = "🟢 Verfügbar"
            else:
              status = "⚪ Info / Standort"

            with st.container():
              st.markdown(f"**{idx}. [{status}]**\n\n{res}")
              st.divider()
        else:
          # Falls immer noch nichts gefunden wird, geben wir den HTML-Titel aus, um zu sehen, wo wir gelandet sind
          st.warning("Immer noch keine Treffer. Das System blockiert die Anfrage.")
          st.info(f"Wir sind auf folgender Seite gelandet: **{soup.title.string if soup.title else 'Unbekannt'}**")
          
      except Exception as e:
        st.error(f"Verbindungsfehler: {e}")
