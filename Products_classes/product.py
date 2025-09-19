class Product:
    def __init__(self, title, description, vendor, product_type, status="active", sku=None):
        self.title = title
        self.body_html = description
        self.vendor = vendor
        self.sku = sku
        self.product_type = product_type
        self.status = status
        self.options = []
        self.variants = []
        self.metafields = []

    def add_option(self, option_name):
        if not self.option_exists(option_name):
            self.options.append({"name": option_name})

    def add_variant(self, variant):
        if isinstance(variant, dict):
            variant.setdefault('metafields', [])
            option1 = variant.get('option1')
            option2 = variant.get('option2')
            for existing_variant in self.variants:
                if existing_variant.get('option1') == option1 and existing_variant.get('option2') == option2:
                    return
            self.variants.append(variant)
        else:
            raise ValueError("La variante doit être un dictionnaire")

    def add_metafield(self, namespace, key, value, type="string"):
        # Vérifie si le metafield existe déjà
        existing_metafield = next((mf for mf in self.metafields if mf['namespace'] == namespace and mf['key'] == key), None)
        if existing_metafield:
            existing_metafield['value'] = value  # Met à jour la valeur si le metafield existe déjà
            existing_metafield['type'] = type   # Optionnel: Met à jour le type si nécessaire
        else:
            self.metafields.append({
                "namespace": namespace,
                "key": key,
                "value": value,
                "type": type
            })

    def add_variant_metafield(self, variant_index, namespace, key, value, type="string"):
        if 0 <= variant_index < len(self.variants):
            variant = self.variants[variant_index]
            # Initialiser 'metafields' si elle n'existe pas déjà
            if 'metafields' not in variant:
                variant["metafields"] = []
            # Ajouter le metafield si nécessaire
            variant['metafields'].append({
                "namespace": namespace,
                "key": key,
                "value": value,
                "type": type
            })
        else:
            raise IndexError("L'indice de la variante est hors des limites")

    def to_data_array_without_images(self):
        return {
            "product": {
                "title": self.title,
                "body_html": self.body_html,
                "vendor": self.vendor,
                "status": self.status,
                "options": self.options,
                "variants": self.variants,
                "product_type": self.product_type,
                "metafields": self.metafields,
            }
        }

    def option_exists(self, option_name):
        return any(option["name"] == option_name for option in self.options)


