class TagService:
    def __init__(self):
        self.tags = []

    def add_tag(self, tag):
        if isinstance(tag, str):
            # Si le tag est une chaîne contenant des virgules, le diviser en plusieurs tags
            split_tags = [t.strip() for t in tag.split(',')]
            for t in split_tags:
                if t and not self.tag_exists(t):
                    self.tags.append(t)
        elif isinstance(tag, list):
            for t in tag:
                self.add_tag(t)
        else:
            # Gérer d'autres types si nécessaire
            tag_str = str(tag).strip()
            if tag_str and not self.tag_exists(tag_str):
                self.tags.append(tag_str)

    def get_tags(self):
        return self.tags

    def get_tags_as_string(self):
        return ', '.join(self.tags)

    def tag_exists(self, tag):
        return tag in self.tags
