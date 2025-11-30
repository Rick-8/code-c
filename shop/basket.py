from decimal import Decimal
from shop.models import Product

class Basket:
    def __init__(self, request):
        self.session = request.session
        self.basket = self.session.get("basket", {})

    def save(self):
        self.session["basket"] = self.basket
        self.session.modified = True

    def add(self, product_id, qty=1):
        product_id = str(product_id)
        self.basket[product_id] = self.basket.get(product_id, 0) + qty
        self.save()

    def remove(self, product_id):
        product_id = str(product_id)
        if product_id in self.basket:
            del self.basket[product_id]
            self.save()

    def update(self, product_id, qty):
        product_id = str(product_id)
        if qty <= 0:
            self.remove(product_id)
        else:
            self.basket[product_id] = qty
            self.save()

    def items(self):
        products = Product.objects.filter(id__in=self.basket.keys())
        for p in products:
            qty = self.basket[str(p.id)]
            yield {
                "product": p,
                "quantity": qty,
                "line_total": p.price * qty,
            }

    def total(self):
        return sum(item["line_total"] for item in self.items())

    def count(self):
        return sum(item["quantity"] for item in self.items())

    def clear(self):
        self.session["basket"] = {}
        self.session.modified = True
