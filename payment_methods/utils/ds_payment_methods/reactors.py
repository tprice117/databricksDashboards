import basistheory
from basistheory.api import reactors_api
from basistheory.model.application import Application
from basistheory.model.create_reactor_request import CreateReactorRequest
from basistheory.model.react_request import ReactRequest
from django.conf import settings

from payment_methods.utils.ds_payment_methods.basistheory_config import (
    api_client_management,
    api_client_use_pci,
)


class Reactors:
    @staticmethod
    def invoke(reactor_id: str, args: dict, **kwargs):
        reactors_client = reactors_api.ReactorsApi(api_client_use_pci)

        return reactors_client.react(
            id=reactor_id,
            react_request=ReactRequest(
                args=args,
            ),
        )

    @staticmethod
    def create_stripe_payment_method_reactor():
        reactors_client = reactors_api.ReactorsApi(api_client_management)

        reactors_client.create(
            create_reactor_request=CreateReactorRequest(
                name="Create Stripe Payment Method (with Basis Theory Metadata)",
                code="""
module.exports = async function (req) {
    const stripe = require('stripe')(req.configuration.STRIPE_SECRET_KEY);
    const {
        AuthenticationError,
        BadRequestError,
        InvalidPaymentMethodError,
        RateLimitError,
        ReactorRuntimeError,
    } = require('@basis-theory/basis-theory-reactor-formulas-sdk-js');

    const {
        token,
        payment_method_id,
    } = req.args;

    // Get the raw payment method from the token.
    const bt_response = await req.bt.tokens.retrieve(token);

    const {
        number,
        expiration_month,
        expiration_year,
        cvc,
    } = bt_response.data;

    try {
        // Create a Stripe Payment Method with the token.
        const paymentMethod = await stripe.paymentMethods.create({
          type: 'card',
          card: {
            number,
            exp_month: expiration_month,
            exp_year: expiration_year,
            cvc,
          },
          metadata: {
              token,
              payment_method_id,
          },
        });

        return {
            raw: paymentMethod.id,
        };
    } catch (err) {
        switch (err.type) {
          case 'StripeCardError':
              throw new InvalidPaymentMethodError();
          case 'StripeRateLimitError':
              throw new RateLimitError();
          case 'StripeAuthenticationError':
              throw new AuthenticationError();
          case 'StripeInvalidRequestError':
              throw new BadRequestError();
          case 'StripeAPIError':
          case 'StripeConnectionError':
          default:
              throw new ReactorRuntimeError(err);
        }
    }
};

                """,
                configuration={
                    "STRIPE_SECRET_KEY": settings.STRIPE_SECRET_KEY,
                },
                application=Application(
                    id="63da13bb-3a2c-4bd5-b747-a5a4cc9f76e7",  # "a44b44d5-2cb8-4255-bbf6-dc5884bffdbf",
                ),
            )
        )
