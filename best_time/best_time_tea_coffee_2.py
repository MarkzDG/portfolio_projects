import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import time
import random
import json
import os
from datetime import datetime

def get_webdriver(headless=False, proxy=None):
    """Initialize Selenium WebDriver with options to avoid detection and captchas."""
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    
    # User-Agent aleatorio para simular diferentes dispositivos
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
    ]
    chrome_options.add_argument(f"user-agent={random.choice(user_agents)}")
    
    # Deshabilitar flags obvios de automatización
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Proxy opcional
    if proxy:
        chrome_options.add_argument(f"--proxy-server={proxy}")
    
    # Modo headless (opcional)
    if headless:
        chrome_options.add_argument("--headless=new")  # Nueva versión de headless, más indetectable
    
    # Desactivar WebRTC (puede exponer info)
    chrome_options.add_argument("--disable-webrtc")
    
    # Inicializar el WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # Eliminar la propiedad webdriver para evitar detección
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def google_search(query, num_results=20):
    """Perform a Google search using Selenium and return URLs with reduced patience."""
    driver = get_webdriver(headless=False)  # Sin headless para resolver captchas manualmente
    
    try:
        search_url = f"https://www.google.com/search?q={query}&num={num_results}"
        print(f"Fetching Google search: {search_url}")
        driver.get(search_url)
        
        # Esperar si aparece un CAPTCHA
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "captcha-form"))
            )
            print("Apareció un CAPTCHA. Resuélvelo manualmente y presiona Enter aquí cuando termines.")
            input("Esperando tu confirmación...")
        except TimeoutException:
            print("No CAPTCHA detected, proceeding with result extraction.")
        
        # Esperar que carguen los resultados (máximo 20 segundos)
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.yuRUbf a[href], div.g div a[href]"))
            )
        except Exception as e:
            print(f"Google page didn't load results in time: {e}")
            print("Attempting to extract any available links anyway...")
        
        # Pausa humana aleatoria
        time.sleep(random.uniform(1, 3))
        
        # Parsear la página
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Selectores para extraer enlaces
        selectors = [
            "div.yuRUbf a[href]",
            "div.g div a[href]",
            "a[href^='http']"
        ]
        
        links = []
        for selector in selectors:
            for result in soup.select(selector):
                link = result.get("href")
                if link and link.startswith("http") and "google" not in link.lower():
                    links.append(link)
        
        # Extraer URLs del formato '/url?q='
        if len(links) < 5:
            for a_tag in soup.find_all('a', href=True):
                link = a_tag['href']
                if link.startswith('/url?q='):
                    actual_url = link.split('/url?q=')[1].split('&')[0]
                    if actual_url.startswith('http') and 'google' not in actual_url.lower():
                        links.append(actual_url)
        
        # Eliminar duplicados
        links = list(dict.fromkeys(links))
        print(f"Found {len(links)} links from Google search")
        
        return links[:num_results]
    
    except Exception as e:
        print(f"Error in Google search: {e}")
        return []
    
    finally:
        driver.quit()

def scrape_full_text(url, driver):
    """Scrape text with a strict timeout of 15 seconds total."""
    print(f"Attempting to fetch: {url}")
    
    start_time = time.time()  # Start the timer
    max_time = 15  # Maximum allowed time in seconds
    
    try:
        # Set page load timeout to 10 seconds
        driver.set_page_load_timeout(10)
        
        # Intentar cargar la página
        try:
            driver.get(url)
            time.sleep(random.uniform(1, 2))  # Pausa humana
        except TimeoutException:
            print(f"Page load timed out for {url}")
            return "", url
        
        # Verificar tiempo total
        if time.time() - start_time > max_time:
            print(f"Total time exceeded {max_time} seconds for {url}. Moving to the next page.")
            return "", url
        
        # Esperar que cargue el body
        try:
            WebDriverWait(driver, max(1, max_time - (time.time() - start_time))).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            print(f"Timeout waiting for page content on {url}")
            return "", url
        
        # Verificar tiempo total
        if time.time() - start_time > max_time:
            print(f"Total time exceeded {max_time} seconds for {url}. Moving to the next page.")
            return "", url
        
        # Extraer contenido rápidamente
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Eliminar elementos no deseados
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        
        # Buscar contenido principal
        content_selectors = ["article", "main", ".content", "#content", ".post"]
        main_content = ""
        
        for selector in content_selectors:
            if time.time() - start_time > max_time:
                print(f"Total time exceeded {max_time} seconds for {url}. Moving to the next page.")
                return "", url
            
            elements = soup.select(selector)
            if elements:
                main_content = " ".join([elem.get_text(separator=" ") for elem in elements])
                break
        
        # Si no hay contenido principal, buscar párrafos
        if not main_content or len(main_content.split()) < 50:
            if time.time() - start_time > max_time:
                print(f"Total time exceeded {max_time} seconds for {url}. Moving to the next page.")
                return "", url
            
            paragraphs = soup.find_all('p')
            main_content = " ".join([p.get_text(separator=" ") for p in paragraphs])
        
        # Si sigue sin contenido suficiente, tomar todo el body
        if not main_content or len(main_content.split()) < 50:
            if time.time() - start_time > max_time:
                print(f"Total time exceeded {max_time} seconds for {url}. Moving to the next page.")
                return "", url
            
            body = soup.find('body')
            if body:
                main_content = body.get_text(separator=" ")
        
        # Verificar tiempo total
        if time.time() - start_time > max_time:
            print(f"Total time exceeded {max_time} seconds for {url}. Moving to the next page.")
            return "", url
        
        # Limpiar el texto
        main_content = re.sub(r'\s+', ' ', main_content).strip()
        
        if len(main_content) < 100:
            print(f"Insufficient content extracted from {url}")
            return "", url
            
        print(f"Extracted {len(main_content)} characters from {url}")
        return main_content, url
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return "", url

def extract_drink_times(text):
    """Extract mentions of coffee/tea times from raw text."""
    # Define drink types
    coffee_types = [
        r"coffee", r"espresso", r"cappuccino", r"latte", r"americano", 
        r"mocha", r"macchiato", r"café", r"java", r"brew", r"decaf"
    ]
    
    tea_types = [
        r"tea", r"green tea", r"black tea", r"herbal tea", r"chamomile", 
        r"oolong", r"white tea", r"matcha", r"chai", r"earl grey", r"pu-erh"
    ]
    
    # Time patterns (including "bedtime" as part of "night")
    time_patterns = [
        r"(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))",  # e.g. 8:00 AM, 8 PM
        r"(\d{1,2}\s+o'clock)",  # e.g. 8 o'clock
        r"(early|mid|late)\s+(morning|afternoon|evening)",  # e.g. early morning
        r"(before|after|during)\s+(breakfast|lunch|dinner|meal)",  # meal-related times
        r"(before|after)\s+(workout|exercise|gym|run)",  # activity-related times
        r"(before|at|after)\s+(sunrise|sunset|dawn|dusk)",  # natural times
        r"(morning|afternoon|evening|night|noon|midnight)"  # General time words
    ]
    
    # Lists to store findings
    drink_time_findings = []
    
    # Split into sentences for better context
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        
        # Check for drink types
        coffee_match = any(re.search(r'\b' + pattern + r'\b', sentence_lower) for pattern in coffee_types)
        tea_match = any(re.search(r'\b' + pattern + r'\b', sentence_lower) for pattern in tea_types)
        
        if not (coffee_match or tea_match):
            continue
            
        # Determine drink type
        drink_type = "coffee" if coffee_match else "tea"
        
        # Look for time information
        time_info = "Not specified"
        for pattern in time_patterns:
            match = re.search(pattern, sentence_lower, re.IGNORECASE)
            if match:
                time_info = match.group(0)
                break
                
        # Add to findings
        drink_time_findings.append({
            "drink": drink_type,
            "time": time_info,
            "source": ""  # Will be filled in later
        })
    
    print(f"Found {len(drink_time_findings)} relevant drink/time mentions")
    return drink_time_findings

def main():
    # Create output directory
    output_dir = "coffee_tea_times"
    os.makedirs(output_dir, exist_ok=True)
    
    # Timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Broader queries for coffee and tea timing
    queries = [
        # Coffee-related queries
        '"coffee drinking" timing OR effects OR habits OR routine -site:pinterest.com -site:facebook.com -site:instagram.com',
        '"best time to drink coffee" OR "optimal coffee time" OR "coffee consumption" health',
        '"morning coffee" OR "afternoon coffee" OR "evening coffee" benefits OR effects',
        
        # Tea-related queries
        '"tea drinking" timing OR effects OR habits OR routine -site:pinterest.com -site:facebook.com -site:instagram.com',
        '"best time to drink tea" OR "optimal tea time" OR "tea consumption" health',
        '"morning tea" OR "afternoon tea" OR "evening tea" benefits OR effects'
    ]

    queries += [
    '"hot beverages" timing OR effects OR habits OR routine -site:pinterest.com -site:facebook.com -site:instagram.com',
    '"morning drink" OR "afternoon drink" OR "evening drink" benefits OR side effects',
    '"best time for a warm drink" OR "optimal moment to enjoy a hot drink" health OR energy'
    ]
    
    # Fallback URLs
    fallback_urls = [
        "https://www.healthline.com/nutrition/best-time-to-drink-coffee",
        "https://www.sleepfoundation.org/nutrition/caffeine-and-sleep",
        "https://www.medicalnewstoday.com/articles/best-time-to-drink-coffee",
        "https://www.webmd.com/diet/health-benefits-tea",
        "https://www.self.com/story/best-time-to-drink-coffee",
        "https://www.onhealth.com/content/1/health_benefits_of_drinking_tea",
        "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7019362/"
    ]
    
    all_urls = []
    
    # Execute each query
    for i, query in enumerate(queries):
        print(f"\n--- Query {i+1}/{len(queries)}: {query} ---")
        
        try:
            urls = google_search(query, num_results=10)
            all_urls.extend(urls)
            time.sleep(random.uniform(2, 5))  # Pausa entre búsquedas para evitar bloqueos
        except Exception as e:
            print(f"Error with query {i+1}: {e}")
    
    # Remove duplicates and limit results
    all_urls = list(dict.fromkeys(all_urls))
    print(f"Collected {len(all_urls)} unique URLs from all queries")
    
    # Use fallback if needed
    if len(all_urls) < 5:
        print("Insufficient results from search. Using fallback URLs.")
        all_urls.extend(fallback_urls)
        all_urls = list(dict.fromkeys(all_urls))
    
    print(f"Processing {len(all_urls)} URLs")
    
    # Initialize WebDriver
    driver = get_webdriver(headless=False)
    raw_texts = []  # Store raw text for later analysis
    findings = []
    
    # Process each URL
    for idx, url in enumerate(all_urls):
        print(f"\n[{idx+1}/{len(all_urls)}] Processing: {url}")
        
        try:
            full_text, source = scrape_full_text(url, driver)
            
            if not full_text:
                print(f"No content from {url}, skipping...")
                continue
                
            # Store raw text
            raw_texts.append({"text": full_text, "source": source})
            
            # Extract drink and time information
            drink_findings = extract_drink_times(full_text)
            
            # Add source information
            for finding in drink_findings:
                finding["source"] = source
                findings.append(finding)
            
            time.sleep(random.uniform(1, 3))  # Pausa humana entre páginas
        
        except Exception as e:
            print(f"Error processing {url}: {e}")
            continue
    
    # Clean up
    driver.quit()
    
    # Create DataFrame
    if findings:
        df = pd.DataFrame(findings)
        print(f"Extracted data: {len(df)} rows")
        
        # Save to Excel
        excel_file = os.path.join(output_dir, f"coffee_tea_times_{timestamp}.xlsx")
        df.to_excel(excel_file, index=False, engine="openpyxl")
        print(f"Data saved to {excel_file}")
        
        # Save raw data to JSON
        json_file = os.path.join(output_dir, f"coffee_tea_raw_{timestamp}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(raw_texts, f, ensure_ascii=False, indent=2)
        print(f"Raw data saved to {json_file}")
        
        # Generate summary
        generate_summary(findings, output_dir, timestamp)
    else:
        print("No findings extracted. Check search queries or fallback URLs.")

def generate_summary(findings, output_dir, timestamp):
    """Generate a summary of findings about coffee and tea consumption times."""
    if not findings:
        return
    
    # Separate coffee and tea findings
    coffee_findings = [f for f in findings if f["drink"] == "coffee"]
    tea_findings = [f for f in findings if f["drink"] == "tea"]
    
    # Count time mentions for coffee
    coffee_times = {}
    for f in coffee_findings:
        if f["time"] != "Not specified":
            # Group "bedtime" under "night"
            time_key = "night" if "bedtime" in f["time"].lower() else f["time"]
            coffee_times[time_key] = coffee_times.get(time_key, 0) + 1
    
    # Count time mentions for tea
    tea_times = {}
    for f in tea_findings:
        if f["time"] != "Not specified":
            # Group "bedtime" under "night"
            time_key = "night" if "bedtime" in f["time"].lower() else f["time"]
            tea_times[time_key] = tea_times.get(time_key, 0) + 1
    
    # Generate summary text
    summary = [
        "# Coffee and Tea Consumption Time Analysis",
        f"\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"\nTotal sources analyzed: {len(set([f['source'] for f in findings]))}",
        f"Total findings: {len(findings)} ({len(coffee_findings)} coffee, {len(tea_findings)} tea)",
        
        "\n## Most Mentioned Times for Coffee Consumption",
    ]
    
    # Add coffee time frequencies
    for time, count in sorted(coffee_times.items(), key=lambda x: x[1], reverse=True)[:10]:
        summary.append(f"- {time}: {count} mentions")
    
    summary.append("\n## Most Mentioned Times for Tea Consumption")
    
    # Add tea time frequencies
    for time, count in sorted(tea_times.items(), key=lambda x: x[1], reverse=True)[:10]:
        summary.append(f"- {time}: {count} mentions")
    
    # Save summary
    summary_file = os.path.join(output_dir, f"summary_{timestamp}.md")
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(summary))
    
    print(f"Summary saved to {summary_file}")

if __name__ == "__main__":
    main()