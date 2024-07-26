import random
import string

from django.db import models

from api.models.main_product.main_product import MainProduct
from api.models.main_product.product_add_on_choice import ProductAddOnChoice
from common.models import BaseModel


class Product(BaseModel):
    product_code = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    main_product = models.ForeignKey(
        "api.MainProduct",
        models.CASCADE,
        related_name="products",
    )
    removal_price = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )

    def __str__(self):
        return f'{self.main_product.name} {"-" if self.formatted_add_on_choices != "" else ""} {self.formatted_add_on_choices}'

    @property
    def formatted_add_on_choices(self):
        product_add_on_choices = ProductAddOnChoice.objects.filter(product=self)

        formatted_add_on_choices = [
            f"{product_add_on_choice.add_on_choice.add_on.name}|{product_add_on_choice.add_on_choice.name}"
            for product_add_on_choice in product_add_on_choices
        ]

        return ", ".join(formatted_add_on_choices) if formatted_add_on_choices else ""

    @staticmethod
    def generate_product_code() -> str:
        """
        Generates a random 6 character code with the pattern letter-number-letter-number-letter-number.
        """
        char_sets = [string.ascii_uppercase, string.digits] * 3
        code = "".join(random.choice(char) for char in char_sets)

        # Check if code already exists or if the code contains "bad" characters (0, O, I, l, etc.).
        does_code_exist = Product.objects.filter(product_code=code).exists()
        if does_code_exist or any(char in code for char in ["0", "O", "1", "I", "L"]):
            return Product.generate_product_code()
        else:
            return code

    @staticmethod
    def exists_for_main_product(
        main_product: MainProduct,
        add_on_choices: list[ProductAddOnChoice],
    ):
        products = Product.objects.filter(main_product=main_product)

        for product in products:
            product_add_on_choices = ProductAddOnChoice.objects.filter(product=product)
            if len(product_add_on_choices) != len(add_on_choices):
                continue

            for add_on_choice in add_on_choices:
                if add_on_choice not in product_add_on_choices:
                    break
            else:
                return True

        return False

    @staticmethod
    def create_products_for_main_product(main_product: MainProduct):
        # There are 2 cases to consider:
        # 1. The MainProduct has no Products. In this case, we create
        # all Product combinations for the MainProduct based on the
        # MainProduct's AddOns.
        # 2. The MainProduct has existing Products (either they were
        # manually created or created by a previous version of this
        # function). In this case, we create any missing Products.
        # We do not delete any Products.

        # First, get a list of all combinations of AddOnChoices. For example,
        # if we have AddOns A, B, and C, and A has 2 choices, B has 3 choices,
        # and C has 2 choices, we should have 2 * 3 * 2 = 12 combinations.
        add_on_choices = [add_on.choices.all() for add_on in main_product.add_ons.all()]

        combinations = []
        for choice in add_on_choices:
            if not combinations:
                combinations = [[c] for c in choice]
            else:
                new_combinations = []
                for c in choice:
                    for combination in combinations:
                        new_combinations.append(combination + [c])
                combinations = new_combinations

        # Next, create Products for each combination of AddOnChoices.
        for combination in combinations:
            if Product.exists_for_main_product(main_product, combination):
                # Skip if the Product already exists.
                continue
            else:
                # Create the Product.
                product = Product.objects.create(
                    main_product=main_product,
                    product_code=Product.generate_product_code(),
                )

                # Create ProductAddOnChoices for this Product.
                for choice in combination:
                    ProductAddOnChoice.objects.create(
                        product=product,
                        add_on_choice=choice,
                    )
