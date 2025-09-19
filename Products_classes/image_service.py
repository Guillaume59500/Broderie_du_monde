class ImageService:
    def __init__(self):
        self.images = []

    def add_image(self, src, sku):
        self.images.append({"src": src, "sku": sku})

    def add_variant_id_to_photo(self, variant_id, sku):
        for image in self.images:
            if image["sku"] == sku:
                if "variant_ids" not in image:
                    image["variant_ids"] = []
                image["variant_ids"].append(variant_id)

    def to_data_array_only_images(self):
        return {
            "product": {
                "images": self.images,
            }
        }
