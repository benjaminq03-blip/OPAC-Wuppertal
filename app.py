import streamlit as st
import re
import os
import urllib.parse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

st.set_page_config(
    page_title="Wuppertal OPAC Suche", page_icon="📚", layout="centered"
)

# WICHTIG: Das installiert den unsichtbaren Browser in der Streamlit Cloud
@st.cache_resource
def install_browser():
    os.system("playwright install chromium")

install_browser()

st.title("📚 Smarte Wuppertal OPAC-Suche")
st.write("Jetzt mit echtem (unsichtbarem) Browser unter der Haube, der das System austrickst!")

query = st.text_input(
    "Buchtitel, Autor oder ISBN eingeben:", placeholder="z. B. Das Sams oder 978..."
)

def smart_typo_correction(text):
    text_lower = text.strip().lower()
    corrections = {
        "das sans": "Das Sams",
        "wanze muldon": "Die Wanze",
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
        search_query = clean_query if is_isbn else smart_typo_correction(query)

        with st.spinner("Starte unsichtbaren Browser und durchsuche OPAC... (Das kann beim ersten Mal kurz dauern)"):
            try:
                # Hier starten wir Playwright
                with sync_playwright() as p:
                    # headless=True bedeutet, der Browser läuft unsichtbar im Hintergrund
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                    page = context.new_page()

                    # 1. Startseite aufrufen, damit der Server uns Cookies gibt
                    page.goto("https://webopac.wuppertal.de/webOPACClient/start.do", wait_until="domcontentloaded")

                    # 2. Den Suchbegriff für die URL sicher codieren (aus Leerzeichen wird z.B. %20)
                    safe_query = urllib.parse.quote(search_query)
                    
                    # 3. Die exakte Sisis-Such-URL aufrufen
                    search_url = f"https://webopac.wuppertal.de/webOPACClient/search.do?methodToCall=submit&searchCategories%5B0%5D=-1&searchString%5B0%5D={safe_query}&submitSearch=Suchen"
                    page.goto(search_url, wait_until="domcontentloaded")
                    
                    # Wir geben dem alten Server 2 Sekunden Zeit, die Tabelle aufzubauen
                    page.wait_for_timeout(2000) 
                    
                    # Jetzt ziehen wir uns den fertigen HTML-Code der Seite
                    html = page.content()
                    browser.close()

                # Ab hier übernimmt wieder BeautifulSoup zum Filtern der Tabelle
                soup = BeautifulSoup(html, "html.parser")
                rows = soup.find_all("tr")
                results = []

                for row in rows:
                    if "odd" in row.get("class", []) or "even" in row.get("class", []) or row.find("td"):
                        cols = row.find_all("td")
                        if cols:
                            row_text = " | ".join([c.get_text(strip=True) for c in cols if c.get_text(strip=True)])
                            if len(row_text) > 15 and "Suche" not in row_text and "Treffer" not in row_text:
                                results.append(row_text)

                if results:
                    st.success(f"{len(results)} Einträge/Zweigstellen gefunden:")
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
                    st.warning("Keine Treffer gefunden. Das System blockiert nicht mehr, aber der Begriff ergab keine Treffer.")
                    
            except Exception as e:
                st.error(f"Fehler beim Ausführen des Browsers: {e}")
    else:
        st.warning("Bitte gib einen Suchbegriff ein.")
