import argparse
import asyncio
import csv
import re
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import aiohttp

from API.products import create_shopify_product
from Products_classes.image_service import ImageService
from Products_classes.product import Product
from Products_classes.product_generation_service import ProductGenerationService
from Products_classes.tag_service import TagService


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _clean_decimal(value: str) -> Optional[str]:
    if not value:
        return None
    normalized = value.replace("\u00a0", " ").strip()
    if not normalized:
        return None
    normalized = normalized.replace(" ", "").replace(",", ".")
    try:
        return f"{float(normalized):.2f}"
    except ValueError:
        return None


def _clean_weight_in_grams(value: str) -> Optional[float]:
    if not value:
        return None
    cleaned = value.replace("\u00a0", " ").strip().replace(",", ".")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _clean_int(value: str) -> Optional[int]:
    if not value:
        return None
    cleaned = value.replace("\u00a0", " ").strip()
    if not cleaned:
        return None
    try:
        return int(float(cleaned.replace(",", ".")))
    except ValueError:
        return None


def _sanitize_identifier(value: str) -> str:
    if not value:
        return ""
    return value.strip().lstrip("#").strip()


def _sanitize_tag_value(value: str) -> str:
    if not value:
        return ""
    collapsed = re.sub(r"\s+", "_", value.strip())
    return re.sub(r"[^\w\-]", "_", collapsed)


def _slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


def _split_to_list(value: str) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(";") if item.strip()]


def _build_product_payload(row: Dict[str, str]) -> Tuple[Dict, str]:
    product_id = _sanitize_identifier(row.get("ID produit", ""))
    sku = row.get("Référence du produit", "").strip()
    vendor = row.get("Nom du fournisseur", "").strip()
    ean13 = row.get("EAN 13", "").strip()
    title = _normalize_whitespace(row.get("Nom du produit", ""))
    long_description = row.get("Description longue", "").strip()
    short_description = row.get("Description courte", "").strip()
    keywords = row.get("Mots clés", "")
    features = row.get("Caractéristiques", "")
    weight_value = _clean_weight_in_grams(row.get("Poids", ""))
    quantity = _clean_int(row.get("Quantité", "")) or _clean_int(row.get("Nombre de produits en stock", "")) or 0
    price_ttc = _clean_decimal(row.get("Prix du produit (TTC hors remise)", "")) or "0.00"
    purchase_price_ht = _clean_decimal(row.get("Prix d'achat HT du produit", ""))
    vat_rate = row.get("Taux de tva", "").strip()
    sous_categorie = row.get("Sous-catégorie principale", "").strip()
    categorie = row.get("Catégorie", "") or row.get("Catégorie principale parente", "")
    categorie_parente = row.get("Catégorie principale parente", "").strip()
    brand_name = row.get("Nom Marque", "").strip()
    page_title = row.get("Titre de la page", "").strip()
    meta_description = row.get("Méta description", "").strip()
    etat = row.get("Etat", "").strip().lower()

    status = "active" if etat == "affiché" else "draft"
    product_type = sous_categorie or categorie_parente or "Divers"

    product = Product(
        title=title,
        description=long_description,
        vendor=vendor or brand_name or "",
        product_type=product_type,
        status=status,
        sku=sku,
    )

    product.add_option("Title")

    variant = {
        "sku": sku,
        "option1": "Default Title",
        "price": price_ttc,
        "inventory_policy": "deny",
        "inventory_management": "shopify",
        "inventory_quantity": quantity,
        "requires_shipping": True,
        "fulfillment_service": "manual",
        "taxable": vat_rate != "0",
    }

    if ean13:
        variant["barcode"] = ean13
    if purchase_price_ht:
        variant["cost"] = purchase_price_ht
    if weight_value is not None:
        variant["weight"] = weight_value
        variant["weight_unit"] = "g"
        variant["grams"] = int(round(weight_value))

    product.add_variant(variant)

    if product_id:
        product.add_metafield("custom", "product_id", f"product_id : {product_id}", type="single_line_text_field")
    if short_description:
        product.add_metafield("custom", "short_description", short_description, type="multi_line_text_field")
    keyword_list = _split_to_list(keywords)
    if keyword_list:
        product.add_metafield("custom", "keywords", "\n".join(keyword_list), type="multi_line_text_field")
    if features:
        product.add_metafield("custom", "features", features.strip(), type="multi_line_text_field")
    if meta_description:
        product.add_metafield("custom", "meta_description", meta_description, type="multi_line_text_field")
    if purchase_price_ht:
        product.add_metafield("custom", "purchase_price_ht", purchase_price_ht, type="number_decimal")
    if page_title:
        product.add_metafield("seo", "title", page_title, type="single_line_text_field")

    tag_service = TagService()
    tag_service.add_tag(keyword_list)
    if product_id:
        tag_service.add_tag(f"product_id:{product_id}")
    if sous_categorie:
        tag_service.add_tag(f"Sous_Categorie_{_sanitize_tag_value(sous_categorie)}")
    if categorie:
        tag_service.add_tag(f"Categorie : {categorie}")
    if categorie_parente:
        tag_service.add_tag(f"Categorie_principale : {categorie_parente}")
    if vendor:
        tag_service.add_tag(f"Fournisseur : {vendor}")
    if brand_name:
        tag_service.add_tag(f"Marque : {brand_name}")

    image_service = ImageService()
    for photo_index in range(1, 6):
        url = row.get(f"Photo {photo_index}", "").strip()
        if url:
            image_service.add_image(url, sku)

    generation_service = ProductGenerationService(product, image_service, tag_service)
    payload = generation_service.get_formatted_product_data()
    product_payload = payload.get("product", {})
    if page_title:
        product_payload["metafields_global_title_tag"] = page_title
    if meta_description:
        product_payload["metafields_global_description_tag"] = meta_description
    product_payload["handle"] = _slugify(title) if title else ""

    return payload, title or sku or product_id


def _read_csv_rows(csv_path: Path) -> Iterable[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            yield row


async def import_products(csv_path: Path, token_index: int = 0, limit: Optional[int] = None) -> None:
    rows = _read_csv_rows(csv_path)
    prepared: List[Tuple[Dict, str]] = []
    for idx, row in enumerate(rows):
        if limit is not None and idx >= limit:
            break
        payload, label = _build_product_payload(row)
        prepared.append((payload, label))

    async with aiohttp.ClientSession() as session:
        for payload, label in prepared:
            print(f"Création du produit Shopify : {label}")
            response = await create_shopify_product(session, payload, token_index=token_index)
            if response:
                product_info = response.get("product", {})
                print(f"→ Produit créé : {product_info.get('id')} - {product_info.get('title')}")
            else:
                print(f"→ Échec de la création pour : {label}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Importe les produits dans Shopify à partir d'un fichier CSV.")
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=Path(__file__).parent / "files" / "Produits AVA.csv",
        type=Path,
        help="Chemin du fichier CSV à importer",
    )
    parser.add_argument("--token-index", type=int, default=0, help="Index du token Shopify à utiliser")
    parser.add_argument("--limit", type=int, default=None, help="Nombre maximum de produits à importer")

    args = parser.parse_args()
    asyncio.run(import_products(args.csv_path, token_index=args.token_index, limit=args.limit))


if __name__ == "__main__":
    main()
