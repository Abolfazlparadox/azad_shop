def build_category_tree(queryset):
    """
    خروجی: [(category_obj, level), ...]
    سطح 0 برای دسته‌های بدون والد، هر سطح بعد +1 می‌شود.
    """
    tree = []
    # ابتدا دیکشنری parent_id → لیست فرزندان
    children_map = {}
    for cat in queryset:
        parent_id = cat.parent_id or 0
        children_map.setdefault(parent_id, []).append(cat)

    def traverse(parent_id, level):
        for cat in sorted(children_map.get(parent_id, []), key=lambda c: c.title):
            tree.append((cat, level))
            traverse(cat.id, level + 1)

    traverse(0, 0)
    return tree