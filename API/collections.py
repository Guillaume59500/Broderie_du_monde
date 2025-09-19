import os
import json
import time
import asyncio
import aiohttp
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Importer la gestion des tokens depuis le module des clients
from utils import get_access_token, load_tokens, _rate_limiters, _tokens

# Configuration Shopify
SHOPIFY_DOMAIN = "broderiedumonde.com"  # Remplacez par votre domaine Shopify
API_VERSION = "2025-01"

# Charger les tokens (si ce n'est pas déjà fait)
load_tokens()

async def get_all_smart_collections(token_index=0):
    # Récupère le token et la clé associée
    access_token, token_key = get_access_token(token_index)
    # Appliquer le rate limiting
    await _rate_limiters[token_key].acquire()

    url = f"https://{SHOPIFY_DOMAIN}/admin/api/{API_VERSION}/smart_collections.json"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            return data.get("smart_collections", [])

async def create_smart_collection(collection_data, token_index=0):
    access_token, token_key = get_access_token(token_index)
    await _rate_limiters[token_key].acquire()

    url = f"https://{SHOPIFY_DOMAIN}/admin/api/{API_VERSION}/smart_collections.json"
    payload = {
        "smart_collection": {
            "title": collection_data["collectionTitle"],
            "rules": [
                {
                    "column": "tag",
                    "relation": "equals",
                    "condition": "Collection: "+ collection_data["collectionTitle"]
                }
            ]
            # Vous pouvez ajouter d'autres champs requis ou optionnels ici
        }
    }
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            return await response.json()


async def update_smart_collection(collection_id, collection_data, token_index=0):
    access_token, token_key = get_access_token(token_index)
    await _rate_limiters[token_key].acquire()

    url = f"https://{SHOPIFY_DOMAIN}/admin/api/{API_VERSION}/smart_collections/{collection_id}.json"
    payload = {
        "smart_collection": {
            "id": collection_id,
            "title": collection_data["collectionTitle"],
            "condition": "Collection: " + collection_data["collectionTitle"]
            # Ajoutez d'autres champs si nécessaire
        }
    }
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.put(url, json=payload, headers=headers) as response:
            return await response.json()
