import basistheory
from basistheory.api import reactors_api
from basistheory.model.application import Application
from basistheory.model.create_reactor_request import CreateReactorRequest
from basistheory.model.update_reactor_request import UpdateReactorRequest
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
    def get_reactor_by_id(reactor_id: str):
        with basistheory.ApiClient(configuration=basistheory.Configuration(api_key=settings.BASIS_THEORY_MANGEMENT_API_KEY)) as api_client:
            reactors_client = reactors_api.ReactorsApi(api_client)

            reactor = reactors_client.get_by_id(reactor_id)
        return reactor

    @staticmethod
    def list_reactors():
        with basistheory.ApiClient(configuration=basistheory.Configuration(api_key=settings.BASIS_THEORY_MANGEMENT_API_KEY)) as api_client:
            reactors_client = reactors_api.ReactorsApi(api_client)

            reactors = reactors_client.get()
        return reactors

    @staticmethod
    def create_stripe_payment_method_reactor():
        reactors_client = reactors_api.ReactorsApi(api_client_management)

        reactor = reactors_client.create(
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
                    id=settings.BASIS_THEORY_APPLICATION_ID,
                ),
            )
        )
        return reactor

    @staticmethod
    def update_stripe_payment_method_reactor():
        """Update the Stripe Payment Method Reactor with the latest code.
        The current code contains a try/catch block around BasisTheory JS to catch and return the error details.
        """
        reactors_client = reactors_api.ReactorsApi(api_client_management)

        reactor = reactors_client.update(
            settings.BASIS_THEORY_CREATE_PAYMENT_METHOD_REACTOR_ID,
            update_reactor_request=UpdateReactorRequest(
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

    let bt_response;
    try {
        // Get the raw payment method from the token.
        bt_response = await req.bt.tokens.retrieve(token);
    } catch (err) {
        if (err.hasOwnProperty('details')) {
            return {body: err.details};
        }
        return {body: err}
        // throw new ReactorRuntimeError(err);
    }

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
                    id=settings.BASIS_THEORY_APPLICATION_ID,
                ),
            )
        )
        return reactor
