import json
import asyncio
import requests

import aiohttp
import re
from utils import get_access_token, load_tokens, _rate_limiters, _tokens

SHOPIFY_DOMAIN = "broderiedumonde.com"
API_VERSION = "2025-01"

load_tokens()


async def get_all_products(token_index=0):
    print('getting all products')
    access_token, token_key = get_access_token(token_index)
    await _rate_limiters[token_key].acquire()

    url = f"https://{SHOPIFY_DOMAIN}/admin/api/{API_VERSION}/products.json?limit=250"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }
    products = []
    visited_urls = set()

    async with aiohttp.ClientSession() as session:
        while url:
            if url in visited_urls:
                print("Pagination arrêtée car URL déjà visitée :", url)
                break
            visited_urls.add(url)
            await _rate_limiters[token_key].acquire()
            try:
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()
                    products.extend(data.get("products", []))
                    link_header = response.headers.get("Link")
                    if link_header:
                        match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
                        url = match.group(1) if match else None
                    else:
                        url = None
            except Exception as e:
                print("Exception during get_all_products:", e)
                break
    return products


async def create_shopify_product(session, product_json, token_index=0):
    access_token, token_key = get_access_token(token_index)
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/{API_VERSION}/products.json"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    try:
        async with session.post(url, headers=headers, json=product_json, ssl=False) as response:
            http_status = response.status
            print(f"HTTP Status Code: {http_status}")

            if http_status == 201:
                return await response.json()
            else:
                error_text = await response.text()
                print(f"Erreur API Shopify pour le produit : {product_json}")
                print(f"Erreur renvoyée par Shopify : {error_text}")
                return None
    except aiohttp.ClientError as e:
        print(f"Erreur de requête : {e}")
        return None


async def update_shopify_product(session, product_id, product_json, token_index=0):
    access_token, token_key = get_access_token(token_index)
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/{API_VERSION}/products/{product_id}.json"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    try:
        async with session.put(url, headers=headers, json=product_json, ssl=False) as response:
            http_status = response.status
            print(f"HTTP Status Code: {http_status}")

            if http_status in [200, 201]:
                updated_product = await response.json()
                return updated_product
            else:
                error_text = await response.text()
                print(f"Erreur API Shopify lors de la mise à jour du produit ID {product_id} : {error_text}")
                return None
    except aiohttp.ClientError as e:
        print(f"Erreur de requête lors de la mise à jour du produit ID {product_id} : {e}")
        return None


async def add_linked_products_metafields(session, product_ids, token_index=0):
    """
    Pour chaque product_id de product_ids, crée un metafield 'custom.linked_products'
    en type list.product_reference, dont la valeur est la liste des autres products en GID.
    """
    access_token, token_key = get_access_token(token_index)
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }

    for pid in product_ids:
        # Affiche l'ID courant et le nombre de frères/sœurs
        print(f"Pour le produit ID {pid} : {len(product_ids) - 1} produits liés")
        # Dans une coroutine, on utilise asyncio.sleep et on l'attend
        await asyncio.sleep(1)

        # Génère la liste des GID pour tous les autres produits du groupe
        siblings = [
            f"gid://shopify/Product/{other_id}"
            for other_id in product_ids
            if other_id != pid
        ]
        print(product_ids)
        print(f"Siblings : {siblings}")
        siblings_json = json.dumps(siblings)
        print(f"Siblings json: {siblings_json}")

        url = f"https://{SHOPIFY_DOMAIN}/admin/api/{API_VERSION}/products/{pid}/metafields.json"
        payload = {
            "metafield": {
                "namespace": "custom",
                "key": "linked_products",
                "type": "list.product_reference",
                "value": siblings_json
            }
        }

        try:
            async with session.post(url, headers=headers, json=payload, ssl=False) as response:
                status = response.status
                print(f"[{pid}] HTTP Status Code: {status}")

                if status == 201:
                    data = await response.json()
                    mf = data.get("metafield", {})
                    print(f"[{pid}] Metafield créé: id={mf.get('id')}")
                else:
                    err = await response.text()
                    print(f"[{pid}] Erreur création metafield : {err}")

        except aiohttp.ClientError as e:
            print(f"[{pid}] Erreur de requête : {e}")


async def create_product_graphql(product_data, token_index=0):
    access_token, token_key = get_access_token(token_index)
    # Extrait le contenu si encapsulé sous "product"
    raw_input = product_data.get("product", product_data)
    # Transforme l'input pour correspondre à ProductInput attendu
    input_data = transform_product_input(raw_input)

    access_token, token_key = get_access_token(token_index)
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/{API_VERSION}/graphql.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }
    mutation = """
    mutation productCreate($input: ProductInput!) {
      productCreate(input: $input) {
        product {
          id
          title
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    payload = json.dumps({
        "query": mutation,
        "variables": {"input": input_data}
    })
    async with aiohttp.ClientSession() as session:
        await _rate_limiters[token_key].acquire()
        try:
            async with session.post(url, headers=headers, data=payload) as response:
                response_text = await response.text()
                if response.status >= 400:
                    print("HTTP Error during create_product_graphql:", response.status, response_text)
                    return {"error": response_text}
                result = await response.json()
                if "errors" in result:
                    print("GraphQL errors during create_product_graphql:", result["errors"])
                    return {"error": result["errors"]}
                return result.get("data", {}).get("productCreate", {})
        except Exception as e:
            print("Exception during create_product_graphql:", e)
            return None


async def get_all_variants(token_index=0):
    access_token, token_key = get_access_token(token_index)
    await _rate_limiters[token_key].acquire()

    url = f"https://{SHOPIFY_DOMAIN}/admin/api/{API_VERSION}/variants.json?limit=250"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }
    variants = []
    visited_urls = set()
    async with aiohttp.ClientSession() as session:
        while url:
            if url in visited_urls:
                print("Pagination arrêtée car URL déjà visitée :", url)
                break
            visited_urls.add(url)
            await _rate_limiters[token_key].acquire()
            try:
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()
                    variants.extend(data.get("variants", []))
                    link_header = response.headers.get("Link")
                    if link_header:
                        match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
                        url = match.group(1) if match else None
                    else:
                        url = None
            except Exception as e:
                print("Exception during get_all_variants:", e)
                break
    return variants


def transform_product_input(data):
    """
    Transforme le dictionnaire d'entrée pour qu'il corresponde à ProductInput attendu par Shopify GraphQL.

    Transformations effectuées :
      - 'body_html' → 'descriptionHtml'
      - 'product_type' → 'productType'
      - 'status' est remplacé par 'published' (true si 'active')
      - Suppression du champ 'variants' (non supporté dans cette mutation)
    """
    transformed = {}
    transformed["title"] = data.get("title")
    transformed["descriptionHtml"] = data.get("body_html")
    transformed["vendor"] = data.get("vendor")
    transformed["productType"] = data.get("product_type")
    transformed["variants"] = data.get("variants")

    # Gérer la publication : GraphQL ne prend pas 'status' directement,
    # on utilise un booléen "published"
    status = data.get("status", "").lower()
    transformed["published"] = True if status == "active" else False

    # Gérer les tags : Shopify attend une chaîne ou une liste de chaînes
    tags = data.get("tags")
    if isinstance(tags, str):
        # Par exemple, sépare par virgule
        transformed["tags"] = [tag.strip() for tag in tags.split(",") if tag.strip()]
    else:
        transformed["tags"] = tags

    # Conserver éventuellement les metafields s'ils sont déjà formatés correctement
    if "metafields" in data:
        transformed["metafields"] = data["metafields"]

    # Ne pas inclure les variantes ici
    return transformed


async def get_variant_metafields(variant_id, token_index=0):
    access_token, token_key = get_access_token(token_index)
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/{API_VERSION}/variants/{variant_id}/metafields.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }

    await _rate_limiters[token_key].acquire()

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("metafields", [])
        except Exception as e:
            print("Exception during get_variant_metafields:", e)
            return []


async def delete_shopify_product(session, product_id, token_index):
    access_token, token_key = get_access_token(token_index)
    print('Appel de delete_shopify_product')
    print(product_id)
    url = f"https://emde-b2b.myshopify.com/admin/api/2024-10/products/{product_id}.json"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    try:
        async with session.delete(url, headers=headers, ssl=False) as response:
            http_status = response.status
            print(f"HTTP Status Code: {http_status}")

            if http_status == 200:
                # En cas de succès, Shopify renvoie généralement une réponse vide ou un message de confirmation
                print(f"Produit avec l'ID {product_id} supprimé avec succès.")
                return True
            else:
                error_text = await response.text()
                print(f"Erreur API Shopify lors de la suppression du produit ID {product_id} : {error_text}")
                return False
    except aiohttp.ClientError as e:
        print(f"Erreur de requête lors de la suppression du produit ID {product_id} : {e}")
        return False


async def update_stock(inventory_item_id, stock, token_index):
    location_id = 100888019208
    access_token, token_key = get_access_token(token_index)

    stock_data = {
        "location_id": location_id,
        "inventory_item_id": inventory_item_id,
        "available": stock
    }
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/{API_VERSION}/inventory_levels/set.json"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=stock_data, headers=headers)
        return response.json()

    except Exception as e:
        print(e)
        return None
