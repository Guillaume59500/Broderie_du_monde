class ProductGenerationService:
    def __init__(self, product, image_service, tag_service):
        self.product = product
        self.image_service = image_service
        self.tag_service = tag_service

    def get_formatted_product_data(self):
        # Génère les données de produit sans les images
        data = self.product.to_data_array_without_images()

        # Ajoute les tags au produit
        data["product"]["tags"] = self.tag_service.get_tags()

        # Ajoute les images si elles existent
        images = self.image_service.to_data_array_only_images()["product"]["images"]
        if images:
            data["product"]["images"] = images

        # Supprime le champ 'options' s'il est vide ou non défini
        if "options" in data["product"]:
            cleaned_options = [opt for opt in data["product"]["options"] if data["product"]["options"] != ""]
            if not cleaned_options:
                del data["product"]["options"]  # Supprime si aucune option valide
            else:
                data["product"]["options"] = cleaned_options

        return data

    def get_images_data(self):
        return self.image_service.to_data_array_only_images()
