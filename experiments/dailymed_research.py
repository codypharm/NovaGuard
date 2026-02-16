
import requests
import json
import logging

# Use a known SPL Set ID (e.g., from OpenFDA or just random from DailyMed)
# Gabapentin (Neurontin): 3f1a9b2d-11d2-49bd-8051-9e5c6a7b8c9d ? No, this is made up.
# Let's search OpenFDA first to get an ID.

def get_set_id(drug_name):
    url = "https://api.fda.gov/drug/label.json"
    params = {"search": f'openfda.brand_name:"{drug_name}"', "limit": 1}
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        if "results" in data:
            spl = data["results"][0]["openfda"]["spl_set_id"][0]
            print(f"Found SPL Set ID for {drug_name}: {spl}")
            return spl
    except Exception as e:
        print(f"Failed to get SPL ID: {e}")
        return None

def verify_dailymed_json(spl_set_id):
    if not spl_set_id:
        return

    # Try standard DailyMed metadata endpoint
    base_url = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
    
    # 1. SPL Metadata
    url = f"{base_url}/spls/{spl_set_id}.json" # Should exist?
    print(f"\nChecking: {url}")
    resp = requests.get(url)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print("Response (Metadata exists!)")
        # print(json.dumps(resp.json(), indent=2)[:500])
    
    # 2. DailyMed REST API for specific sections?
    # Maybe check available endpoints?
    # https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{spl_set_id}/media.json ??
    
    # Let's try to find an endpoint that returns sections.
    # Usually it's NOT straightforward JSON by section.
    # But maybe there is a 'sections' endpoint?
    
    url_sections = f"{base_url}/spls/{spl_set_id}/sections.json" # Not documented but guess
    print(f"\nChecking: {url_sections}")
    resp = requests.get(url_sections)
    print(f"Status: {resp.status_code}")
    
    # 3. Try to get full SPL (XML) just to conform it exists
    url_xml = f"{base_url}/spls/{spl_set_id}.xml"
    print(f"\nChecking: {url_xml}")
    resp = requests.get(url_xml)
    print(f"Status 200?: {resp.status_code == 200}")

    # 4. Search for 'pharmacokinetics' 
    if resp.status_code == 200:
        print("XML contains 'Pharmacokinetics'?")
        print("Pharmacokinetics" in resp.text)
        print("12.3" in resp.text)

if __name__ == "__main__":
    spl_id = get_set_id("Gabapentin")
    verify_dailymed_json(spl_id)
