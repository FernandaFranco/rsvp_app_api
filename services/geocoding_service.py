# backend/services/geocoding_service.py
"""Serviço de geocodificação de endereços usando Google Geocoding API."""
import os
import re
import requests


def geocode_address(address_full):
    """
    Geocodifica um endereço brasileiro usando Google Geocoding API.

    Formato de entrada esperado:
    "Rua Nome, Número, Bairro, Cidade - Estado, CEP XXXXX-XXX, Brasil"

    Retorna (latitude, longitude) se encontrado, ou (None, None) se não encontrado.
    """
    if not address_full:
        return None, None

    # Tentar Google Geocoding primeiro
    lat, lon = _geocode_with_google(address_full)

    if lat and lon:
        return lat, lon

    # Fallback para Nominatim se Google falhar
    print("⚠️  Google Geocoding falhou, tentando Nominatim...")
    return _geocode_with_nominatim(address_full)


def _geocode_with_google(address_full):
    """
    Geocodifica usando Google Geocoding API.
    """
    api_key = os.getenv("GOOGLE_GEOCODING_API_KEY")

    if not api_key or api_key == "SUA_CHAVE_AQUI":
        print("⚠️  Google API key não configurada, usando Nominatim")
        return None, None

    try:
        print(f"📍 Geocodificando com Google: {address_full[:60]}...")

        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": address_full,
            "region": "br",  # Prioriza resultados do Brasil
            "key": api_key
        }

        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK" and data.get("results"):
            result = data["results"][0]
            location = result["geometry"]["location"]
            lat = float(location["lat"])
            lon = float(location["lng"])

            if lat and lon and -90 <= lat <= 90 and -180 <= lon <= 180:
                formatted_address = result.get("formatted_address", "")
                print(f"   ✅ Google sucesso! Lat={lat}, Lon={lon}")
                print(f"   Endereço formatado: {formatted_address}")
                return lat, lon

        status = data.get("status", "UNKNOWN")
        print(f"   ❌ Google não encontrou: {status}")
        return None, None

    except requests.RequestException as e:
        print(f"❌ Erro na requisição Google: {e}")
        return None, None
    except (ValueError, KeyError) as e:
        print(f"❌ Erro ao processar resposta Google: {e}")
        return None, None


def _geocode_with_nominatim(address_full):
    """
    Geocodifica usando Nominatim (OpenStreetMap) como fallback.
    """
    try:
        # Simplificar endereço para Nominatim
        street_match = re.match(
            r'^(?:Rua|Av\.|Avenida|Travessa|Alameda|Praça)\s+([^,]+)',
            address_full,
            re.IGNORECASE
        )
        if street_match:
            street_name = street_match.group(1).strip()
        else:
            street_name = address_full.split(',')[0].strip()

        number_match = re.search(r',\s*(\d+)', address_full)
        number = number_match.group(1) if number_match else None

        city_state_match = re.search(r',\s*([^,]+)\s*-\s*([A-Z]{2})', address_full)
        if city_state_match:
            city = city_state_match.group(1).strip()
            state = city_state_match.group(2).strip()
        else:
            city = None
            state = None

        if not (street_name and city):
            print("❌ Não foi possível extrair rua ou cidade do endereço")
            return None, None

        # Montar endereço simplificado
        if number:
            if state:
                simplified_address = f"{street_name}, {number}, {city}, {state}, Brasil"
            else:
                simplified_address = f"{street_name}, {number}, {city}, Brasil"
        else:
            if state:
                simplified_address = f"{street_name}, {city}, {state}, Brasil"
            else:
                simplified_address = f"{street_name}, {city}, Brasil"

        print(f"📍 Geocodificando com Nominatim: {simplified_address}")

        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": simplified_address,
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
        }
        headers = {
            "User-Agent": "VenhaApp/1.0"
        }

        response = requests.get(url, params=params, headers=headers, timeout=3)
        response.raise_for_status()
        data = response.json()

        if data and len(data) > 0:
            result = data[0]
            lat = float(result.get("lat"))
            lon = float(result.get("lon"))

            if lat and lon and -90 <= lat <= 90 and -180 <= lon <= 180:
                print(f"   ✅ Nominatim sucesso! Lat={lat}, Lon={lon}")
                return lat, lon

        print("   ❌ Nominatim não encontrou coordenadas")
        return None, None

    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"❌ Erro ao geocodificar com Nominatim: {e}")
        return None, None
